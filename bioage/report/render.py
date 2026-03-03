"""Render placeholder report HTML from templates."""

from __future__ import annotations

from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def _fallback_render(context: dict) -> str:
    template_text = (TEMPLATES_DIR / "report.html").read_text(encoding="utf-8")
    return (
        template_text.replace("{{ client.prepared_for }}", context["client"]["prepared_for"])
        .replace("{{ client.date }}", context["client"]["date"])
        .replace("{{ client.client_id }}", context["client"]["client_id"])
        .replace("{{ client.security_key }}", context["client"]["security_key"])
        .replace("{{ client.consultant_id }}", context["client"]["consultant_id"])
        .replace("{{ charts.bio_age }}", context["charts"]["bio_age"])
        .replace("{{ charts.arterial_stiffness }}", context["charts"]["arterial_stiffness"])
        .replace("{{ charts.bmi }}", context["charts"]["bmi"])
        .replace("{{ charts.bp_sbp }}", context["charts"]["bp_sbp"])
        .replace("{{ charts.bp_dbp }}", context["charts"]["bp_dbp"])
        .replace('{% include "toc.html" %}', (TEMPLATES_DIR / "toc.html").read_text(encoding="utf-8"))
    )


def render_report(context: dict, output_html: Path) -> Path:
    output_html.parent.mkdir(parents=True, exist_ok=True)
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            autoescape=select_autoescape(["html"]),
        )
        template = env.get_template("report.html")
        html = template.render(**context)
    except ModuleNotFoundError:
        html = _fallback_render(context)

    output_html.write_text(html, encoding="utf-8")
    return output_html
