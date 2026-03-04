from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from bioage.constants_loader import load_constants
from bioage.pipeline import run_pipeline
from bioage.schema import SchemaValidationError

logger = logging.getLogger(__name__)

app = FastAPI(title="Biological Age Calculator")
templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

OUTPUT_ROOT = Path(os.getenv("BIOAGE_OUTPUT_DIR", "outputs/web"))
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(OUTPUT_ROOT)), name="media")

RUN_ID_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")


def _constants_path() -> Path | None:
    raw = os.getenv("BIOAGE_CONSTANTS_PATH")
    return Path(raw).expanduser().resolve() if raw else None


def _disclaimer_text() -> str:
    try:
        constants = load_constants(_constants_path())
        copy_cfg = constants.get("copy", {}) if isinstance(constants, dict) else {}
        return str(copy_cfg.get("disclaimer_short", "Educational guidance only. These results are not a diagnosis or treatment plan. Discuss personal decisions with a qualified healthcare professional."))
    except Exception:
        logger.exception("Failed to load constants for disclaimer")
        return "Educational guidance only. These results are not a diagnosis or treatment plan. Discuss personal decisions with a qualified healthcare professional."


def _safe_run_id(run_id: str) -> str:
    if not RUN_ID_PATTERN.fullmatch(run_id) or ".." in run_id or "/" in run_id or "\\" in run_id:
        raise HTTPException(status_code=400, detail="Invalid run identifier")
    return run_id


def _run_dir(run_id: str) -> Path:
    safe_id = _safe_run_id(run_id)
    path = (OUTPUT_ROOT / safe_id).resolve()
    root = OUTPUT_ROOT.resolve()
    if root not in path.parents:
        raise HTTPException(status_code=400, detail="Invalid run identifier")
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=404, detail="Run not found")
    return path


def _new_run_folder() -> tuple[str, Path]:
    stamp = datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")
    candidate = OUTPUT_ROOT / stamp
    suffix = 1
    while candidate.exists():
        candidate = OUTPUT_ROOT / f"{stamp}_{suffix}"
        suffix += 1
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate.name, candidate


@app.exception_handler(RequestValidationError)
def handle_request_validation_error(request: Request, exc: RequestValidationError) -> HTMLResponse:
    message = "Some required fields were missing or invalid. Please review lifestyle and sleep selections."
    return templates.TemplateResponse(
        request,
        "error.html",
        {"message": message, "disclaimer": _disclaimer_text()},
        status_code=400,
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {"disclaimer": _disclaimer_text()},
    )


@app.post("/calculate", response_class=HTMLResponse)
def calculate(
    request: Request,
    chronological_age_years: int = Form(...),
    sex: str = Form(...),
    sbp_mmHg: int = Form(...),
    dbp_mmHg: int = Form(...),
    pwv_m_per_s: str | None = Form(None),
    height_cm: str | None = Form(None),
    weight_kg: str | None = Form(None),
    bmi: str | None = Form(None),
    waist_cm: float = Form(...),
    smoking_status: str = Form(...),
    alcohol_use: str = Form(...),
    drug_use: str = Form(...),
    caffeine_use: str = Form(...),
    sleep_hours: float = Form(...),
    sleep_quality: str = Form(...),
    sleep_consistency: str = Form(...),
) -> HTMLResponse:
    def _opt_num(value: str | None, cast):
        if value is None:
            return None
        text = value.strip()
        return cast(text) if text else None

    try:
        raw_input = {
            "demographics": {
                "chronological_age_years": chronological_age_years,
                "sex": sex,
            },
            "vitals": {
                "sbp_mmHg": sbp_mmHg,
                "dbp_mmHg": dbp_mmHg,
                "pwv_m_per_s": _opt_num(pwv_m_per_s, float),
            },
            "anthropometrics": {
                "height_cm": _opt_num(height_cm, float),
                "weight_kg": _opt_num(weight_kg, float),
                "bmi": _opt_num(bmi, float),
                "waist_cm": waist_cm,
            },
            "lifestyle": {
                "smoking_status": smoking_status,
                "alcohol_use": alcohol_use,
                "drug_use": drug_use,
                "caffeine_use": caffeine_use,
            },
            "sleep": {
                "sleep_hours": sleep_hours,
                "sleep_quality": sleep_quality,
                "sleep_consistency": sleep_consistency,
            },
        }

        run_id, outdir = _new_run_folder()
        run_pipeline(
            raw_input=raw_input,
            outdir=outdir,
            constants_path=_constants_path(),
            assets_path=None,
            pdf=False,
            command_line=["web"],
        )

        result = json.loads((outdir / "result.json").read_text(encoding="utf-8"))
        explanations = json.loads((outdir / "explanations.json").read_text(encoding="utf-8"))
        normalized = json.loads((outdir / "inputs_normalized.json").read_text(encoding="utf-8"))

        drivers = explanations.get("drivers", {}).get("metric_drivers", [])[:3]
        actions = explanations.get("recommendations", {}).get("priority_actions", [])[:3]
        warnings = normalized.get("warnings", [])
        missing_metrics = ["PWV"] if normalized.get("vitals", {}).get("pwv_m_per_s") is None else []

        return templates.TemplateResponse(
            request,
            "result.html",
            {
                "run_id": run_id,
                "has_pdf": (outdir / "report.pdf").exists(),
                "disclaimer": _disclaimer_text(),
                "headline": {
                    "chronological_age": normalized.get("demographics", {}).get("chronological_age_years"),
                    "biological_age": result.get("biological_age_years"),
                    "age_delta": result.get("age_delta_years"),
                    "total_risk": result.get("total_risk"),
                },
                "drivers": drivers,
                "actions": actions,
                "warnings": warnings,
                "missing_metrics": missing_metrics,
            },
        )
    except SchemaValidationError as exc:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"message": str(exc), "disclaimer": _disclaimer_text()},
            status_code=400,
        )
    except ValueError:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"message": "Please enter valid numeric values.", "disclaimer": _disclaimer_text()},
            status_code=400,
        )
    except Exception:
        logger.exception("Unexpected error during calculation")
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "message": "We could not complete your request. Please review your inputs and try again.",
                "disclaimer": _disclaimer_text(),
            },
            status_code=500,
        )


@app.get("/runs/{run_id}/report", response_class=HTMLResponse)
def view_report(run_id: str) -> HTMLResponse:
    report_file = _run_dir(run_id) / "report.html"
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return HTMLResponse(report_file.read_text(encoding="utf-8"))


@app.get("/runs/{run_id}/download/report.html")
def download_report_html(run_id: str) -> FileResponse:
    report_file = _run_dir(run_id) / "report.html"
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(report_file, filename=f"{run_id}_report.html", media_type="text/html")


@app.get("/runs/{run_id}/download/report.pdf")
def download_report_pdf(run_id: str) -> FileResponse:
    pdf_file = _run_dir(run_id) / "report.pdf"
    if not pdf_file.exists():
        raise HTTPException(status_code=404, detail="PDF report is not available for this run")
    return FileResponse(pdf_file, filename=f"{run_id}_report.pdf", media_type="application/pdf")


@app.get("/runs/{run_id}/charts", response_class=HTMLResponse)
def view_charts(request: Request, run_id: str) -> HTMLResponse:
    charts_dir = _run_dir(run_id) / "charts"
    chart_files = sorted(p.name for p in charts_dir.glob("*.png")) if charts_dir.exists() else []
    return templates.TemplateResponse(
        request,
        "charts.html",
        {
            "run_id": run_id,
            "chart_files": chart_files,
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
