"""Report rendering entrypoints."""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

from bioage.report.charts import plot_bioage_bar, plot_bp_gauges, plot_gauge
from bioage.report.viewmodel import build_bands, build_report_context
from bioage.schema import BioAgeRequest

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def _render_template(context: dict[str, Any]) -> str:
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=select_autoescape(["html"]))
    template = env.get_template("report.html")
    return template.render(**context)


def render_report_html(
    result: dict,
    explanations: dict,
    constants: dict,
    outdir: Path,
    assets_dir: Path | None = None,
) -> Path:
    del assets_dir
    req = result.get("_request")
    if not isinstance(req, BioAgeRequest):
        raise ValueError("result must include a BioAgeRequest at key '_request' for render_report_html")
    return _render_with_request(req, result, explanations, constants, outdir)


def _render_with_request(req: BioAgeRequest, result: dict, explanations: dict, constants: dict, outdir: Path) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    charts_dir = outdir / "charts"

    context = build_report_context(req, result, explanations, constants)

    palette = ["#8ad1a2", "#f4dd8c", "#f7b267", "#e76f51", "#cc3f3f"]
    pwv_bands = build_bands(constants["thresholds"]["pwv"], palette)
    bmi_bands = build_bands(constants["thresholds"]["bmi"], palette)
    sbp_bands = build_bands(constants["thresholds"]["blood_pressure"]["systolic"], palette)
    dbp_bands = build_bands(constants["thresholds"]["blood_pressure"]["diastolic"], palette)

    bio_chart = plot_bioage_bar(context["headline"]["chronological_age"], context["headline"]["biological_age"], charts_dir / "bio_age_bar.png")
    if req.vitals.pwv_m_per_s is None:
        stiffness_chart = plot_gauge(0.0, pwv_bands, charts_dir / "arterial_stiffness_gauge.png", "Arterial Stiffness", "m/s")
    else:
        stiffness_chart = plot_gauge(float(req.vitals.pwv_m_per_s), pwv_bands, charts_dir / "arterial_stiffness_gauge.png", "Arterial Stiffness", "m/s")
    bmi_chart = plot_gauge(float(req.anthropometrics.bmi), bmi_bands, charts_dir / "bmi_gauge.png", "Body Mass Index", "kg/m²")
    bp = plot_bp_gauges(req.vitals.sbp_mmHg, req.vitals.dbp_mmHg, sbp_bands, dbp_bands, charts_dir)

    context["charts"] = {
        "bio_age": str(bio_chart.relative_to(outdir)),
        "arterial_stiffness": str(stiffness_chart.relative_to(outdir)),
        "bmi": str(bmi_chart.relative_to(outdir)),
        "bp_sbp": str(bp["sbp"].relative_to(outdir)),
        "bp_dbp": str(bp["dbp"].relative_to(outdir)),
    }

    html = _render_template(context)
    report_path = outdir / "report.html"
    report_path.write_text(html, encoding="utf-8")
    shutil.copy2(TEMPLATES_DIR / "styles.css", outdir / "styles.css")
    return report_path


def _export_pdf_stub(html_path: Path, outdir: Path) -> Path:
    raise NotImplementedError(
        "PDF export is optional and currently disabled. Recommended path: install WeasyPrint and render report.html to report.pdf."
    )


def render_report_bundle(run_dir: Path, req: BioAgeRequest, result: dict, explanations: dict, constants: dict) -> dict:
    result_with_req = dict(result)
    result_with_req["_request"] = req
    html_path = _render_with_request(req, result_with_req, explanations, constants, run_dir)
    chart_paths = sorted((run_dir / "charts").glob("*.png"))
    bundle = {"report_html": html_path, "charts": chart_paths, "report_pdf": None}
    return bundle
