from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from bioage.constants_loader import load_constants
from app.helptext import FIELD_HELP, FIELD_RANGES
from app.validation import parse_validation_error
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


def _form_context(
    values: dict[str, str] | None = None,
    field_errors: dict[str, str] | None = None,
    error_summary: str | None = None,
) -> dict:
    base = _default_form_values()
    if values:
        for key, value in values.items():
            if key in base:
                base[key] = value
    return {
        "disclaimer": _disclaimer_text(),
        "helptext": _render_help(),
        "form_values": base,
        "form_errors": field_errors or {},
        "error_summary": error_summary,
    }


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


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", _form_context())


@app.post("/calculate", response_class=HTMLResponse)
async def calculate(request: Request) -> HTMLResponse:
    def _opt_num(value: str | None, cast):
        if value is None:
            return None
        text = value.strip()
        return cast(text) if text else None

    form_data = await request.form()
    values = _default_form_values()
    values.update({key: str(form_data.get(key, "")) for key in values})

    try:
        raw_input = {
            "client_metadata": {"client_name": values["client_name"], "prepared_for": values["client_name"]},
            "demographics": {
                "chronological_age_years": _opt_num(values["chronological_age_years"], int),
                "sex": values["sex"],
            },
            "vitals": {
                "sbp_mmHg": _opt_num(values["sbp_mmHg"], int),
                "dbp_mmHg": _opt_num(values["dbp_mmHg"], int),
                "pwv_m_per_s": _opt_num(values["pwv_m_per_s"], float),
            },
            "anthropometrics": {
                "height_cm": _opt_num(values["height_cm"], float),
                "weight_kg": _opt_num(values["weight_kg"], float),
                "bmi": _opt_num(values["bmi"], float),
                "waist_cm": _opt_num(values["waist_cm"], float),
            },
            "lifestyle": {
                "smoking_status": values["smoking_status"],
                "alcohol_use": values["alcohol_use"],
                "drug_use": values["drug_use"],
                "caffeine_use": values["caffeine_use"],
            },
            "sleep": {
                "sleep_hours": _opt_num(values["sleep_hours"], float),
                "sleep_quality": values["sleep_quality"],
                "sleep_consistency": values["sleep_consistency"],
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
    except (SchemaValidationError, ValueError) as exc:
        field_errors, summary = parse_validation_error(exc)
        return templates.TemplateResponse(
            request,
            "index.html",
            _form_context(values=values, field_errors=field_errors, error_summary=summary),
            status_code=200,
        )
    except Exception:
        logger.exception("Unexpected error during calculation")
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                **_form_context(values=values),
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
