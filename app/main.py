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
from app.helptext import FIELD_HELP, FIELD_RANGES
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


def _default_form_values() -> dict[str, str]:
    return {
        "client_name": "",
        "chronological_age_years": "",
        "sex": "male",
        "sbp_mmHg": "",
        "dbp_mmHg": "",
        "pwv_m_per_s": "",
        "height_cm": "",
        "weight_kg": "",
        "bmi": "",
        "waist_cm": "",
        "smoking_status": "never",
        "alcohol_use": "none",
        "drug_use": "none",
        "caffeine_use": "none",
        "sleep_hours": "",
        "sleep_quality": "good",
        "sleep_consistency": "regular",
    }


def _render_help() -> dict[str, dict[str, str | list[str]]]:
    rendered: dict[str, dict[str, str | list[str]]] = {}
    for field, help_item in FIELD_HELP.items():
        item = dict(help_item)
        range_key = item.get("range_key")
        if isinstance(range_key, str) and range_key in FIELD_RANGES:
            low, high = FIELD_RANGES[range_key]
            item["range_text"] = f"{low:g}–{high:g}"
        else:
            item["range_text"] = "N/A (categorical input)"
        rendered[field] = item
    return rendered


def _form_context(values: dict[str, str] | None = None, field_errors: dict[str, str] | None = None) -> dict:
    base = _default_form_values()
    if values:
        for key, value in values.items():
            if key in base:
                base[key] = value
    return {
        "disclaimer": _disclaimer_text(),
        "helptext": _render_help(),
        "values": base,
        "field_errors": field_errors or {},
    }


def _field_error_with_range(message: str) -> tuple[str | None, str]:
    match = re.search(r"([a-z_]+\.[a-z_]+)", message)
    if not match:
        return None, message
    dotted = match.group(1)
    form_field = dotted.split(".")[-1]
    if dotted in FIELD_RANGES:
        low, high = FIELD_RANGES[dotted]
        return form_field, f"{message} (expected range {low:g}–{high:g})"
    return form_field, message


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
    message = "Please correct the highlighted fields"
    field_errors: dict[str, str] = {}
    for err in exc.errors():
        loc = err.get("loc", [])
        if not loc:
            continue
        field = str(loc[-1])
        dotted_map = {
            "chronological_age_years": "demographics.chronological_age_years",
            "sbp_mmHg": "vitals.sbp_mmHg",
            "dbp_mmHg": "vitals.dbp_mmHg",
            "pwv_m_per_s": "vitals.pwv_m_per_s",
            "height_cm": "anthropometrics.height_cm",
            "weight_kg": "anthropometrics.weight_kg",
            "bmi": "anthropometrics.bmi",
            "waist_cm": "anthropometrics.waist_cm",
            "sleep_hours": "sleep.sleep_hours",
        }
        dotted = dotted_map.get(field)
        if dotted and dotted in FIELD_RANGES:
            low, high = FIELD_RANGES[dotted]
            field_errors[field] = f"Required or invalid input (expected range {low:g}–{high:g})."
        else:
            field_errors[field] = "Required or invalid input."
    return templates.TemplateResponse(request, "error.html", {**_form_context(field_errors=field_errors), "message": message}, status_code=400)


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", _form_context())


@app.post("/calculate", response_class=HTMLResponse)
def calculate(
    request: Request,
    client_name: str = Form(...),
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
            "client_metadata": {"client_name": client_name, "prepared_for": client_name},
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
        field_name, err = _field_error_with_range(str(exc))
        field_errors = {field_name: err} if field_name else {"form": err}
        values = {
            "client_name": client_name,
            "chronological_age_years": str(chronological_age_years),
            "sex": sex,
            "sbp_mmHg": str(sbp_mmHg),
            "dbp_mmHg": str(dbp_mmHg),
            "pwv_m_per_s": pwv_m_per_s or "",
            "height_cm": height_cm or "",
            "weight_kg": weight_kg or "",
            "bmi": bmi or "",
            "waist_cm": str(waist_cm),
            "smoking_status": smoking_status,
            "alcohol_use": alcohol_use,
            "drug_use": drug_use,
            "caffeine_use": caffeine_use,
            "sleep_hours": str(sleep_hours),
            "sleep_quality": sleep_quality,
            "sleep_consistency": sleep_consistency,
        }
        return templates.TemplateResponse(
            request,
            "error.html",
            {**_form_context(values=values, field_errors=field_errors), "message": "Please correct the highlighted fields"},
            status_code=400,
        )
    except ValueError:
        return templates.TemplateResponse(
            request,
            "error.html",
            {**_form_context(), "message": "Please enter valid numeric values."},
            status_code=400,
        )
    except Exception:
        logger.exception("Unexpected error during calculation")
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                **_form_context(),
                "message": "We could not complete your request. Please review your inputs and try again.",
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
