from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bioage.constants_loader import load_constants
from bioage.explain import build_explanation_bundle
from bioage.model import run_model
from bioage.report.render import render_report_bundle
from bioage.schema import normalize_request


def _payload() -> dict:
    return {
        "demographics": {"chronological_age_years": 41, "sex": "female"},
        "vitals": {"sbp_mmHg": 126, "dbp_mmHg": 84, "pwv_m_per_s": 8.1},
        "anthropometrics": {"height_cm": 165, "weight_kg": 67, "waist_cm": 86},
        "lifestyle": {
            "smoking_status": "never",
            "alcohol_use": "light",
            "drug_use": "none",
            "caffeine_use": "moderate",
        },
        "sleep": {"sleep_hours": 7.0, "sleep_quality": "good", "sleep_consistency": "regular"},
    }


def test_report_generation_has_required_sections(tmp_path: Path) -> None:
    constants = load_constants()
    req = normalize_request(_payload())
    result = run_model(req, constants)
    explanations = build_explanation_bundle(req, result, constants)

    bundle = render_report_bundle(tmp_path, req, result, explanations, constants)

    assert bundle["report_html"].exists()
    for name in [
        "bio_age_bar.png",
        "arterial_stiffness_gauge.png",
        "bmi_gauge.png",
        "bp_sbp_gauge.png",
        "bp_dbp_gauge.png",
    ]:
        assert (tmp_path / "charts" / name).exists()

    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    for marker in ["Biological Age Report", "Table of Contents", "Disclaimer", "Biological Age", "Blood Pressure"]:
        assert marker in html


def test_report_bundle_pdf_status_is_nonfatal(tmp_path: Path) -> None:
    constants = load_constants()
    req = normalize_request(_payload())
    result = run_model(req, constants)
    explanations = build_explanation_bundle(req, result, constants)

    bundle = render_report_bundle(tmp_path, req, result, explanations, constants, pdf=True)

    assert bundle["pdf_status"].startswith("generated") or bundle["pdf_status"].startswith("fallback_generated")
    assert bundle["report_pdf"] is not None
    assert bundle["report_pdf"].exists()
