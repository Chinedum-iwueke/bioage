from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from app.main import app
from bioage.constants_loader import load_constants
from bioage.explain import build_explanation_bundle
from bioage.model import risk_to_age_delta, run_model
from bioage.pipeline import run_pipeline
from bioage.report.render import render_report_bundle
from bioage.schema import normalize_request
from bioage.scoring import score_request


client = TestClient(app)


def _base_payload() -> dict:
    return {
        "demographics": {"chronological_age_years": 39, "sex": "male"},
        "vitals": {"sbp_mmHg": 122, "dbp_mmHg": 79},
        "anthropometrics": {"height_cm": 178, "weight_kg": 80, "waist_cm": 91},
        "lifestyle": {
            "smoking_status": "never",
            "alcohol_use": "light",
            "drug_use": "none",
            "caffeine_use": "low",
        },
        "sleep": {"sleep_hours": 7.2, "sleep_quality": "good", "sleep_consistency": "regular"},
    }


def test_unit_warning_flags() -> None:
    p = _base_payload()
    p["anthropometrics"]["waist_cm"] = 30
    p["anthropometrics"]["height_cm"] = 110
    p["anthropometrics"]["weight_kg"] = 300

    req = normalize_request(p)
    codes = {f.code for f in req.guard_flags}

    assert "UNIT_SUSPECT_WAIST_IN" in codes
    assert "UNIT_SUSPECT_HEIGHT_CM" in codes
    assert "UNIT_SUSPECT_WEIGHT_KG_HIGH" in codes


def test_missing_pwv_propagates_and_report_marks_na(tmp_path: Path) -> None:
    constants = load_constants()
    req = normalize_request(_base_payload())

    scoring = score_request(req, constants)
    assert scoring["metric_scores"]["pwv"] is None

    result = run_model(req, constants)
    assert "pwv" in result["missing_metrics"]

    explanations = build_explanation_bundle(req, result, constants)
    bundle = render_report_bundle(tmp_path, req, result, explanations, constants)
    html = bundle["report_html"].read_text(encoding="utf-8")
    assert "Not provided" in html or "N/A" in html


def test_pipeline_is_deterministic_for_same_input(tmp_path: Path) -> None:
    payload = _base_payload()
    one = tmp_path / "one"
    two = tmp_path / "two"

    run_pipeline(payload, one, None, None, False, command_line=["pytest"])
    run_pipeline(payload, two, None, None, False, command_line=["pytest"])

    result_one = json.loads((one / "result.json").read_text(encoding="utf-8"))
    result_two = json.loads((two / "result.json").read_text(encoding="utf-8"))
    assert result_one == result_two

    exp_one = json.loads((one / "explanations.json").read_text(encoding="utf-8"))
    exp_two = json.loads((two / "explanations.json").read_text(encoding="utf-8"))
    assert exp_one["drivers"]["metric_drivers"] == exp_two["drivers"]["metric_drivers"]


def test_risk_and_age_caps_and_clamps() -> None:
    constants = load_constants()
    caps = constants["model"]["age_delta"]["caps"]

    high = risk_to_age_delta(10_000, constants)
    low = risk_to_age_delta(-10_000, constants)

    assert high["age_delta_years"] == pytest.approx(float(caps["max_years"]))
    assert low["age_delta_years"] == pytest.approx(float(caps["min_years"]))

    req = normalize_request(_base_payload())
    result = run_model(req, constants)
    assert 0.0 <= float(result["total_risk"]) <= 100.0
    assert result["biological_age_years"] >= 0


def test_web_path_traversal_is_blocked() -> None:
    response = client.get("/runs/..%2F..%2Fetc%2Fpasswd/report")
    assert response.status_code in {400, 404}

    response2 = client.get("/runs/bad/name/report")
    assert response2.status_code in {400, 404}


def test_web_missing_enum_is_friendly_error() -> None:
    payload = {
        "chronological_age_years": "39",
        "sex": "male",
        "sbp_mmHg": "122",
        "dbp_mmHg": "79",
        "pwv_m_per_s": "",
        "height_cm": "178",
        "weight_kg": "80",
        "bmi": "",
        "waist_cm": "91",
        "smoking_status": "never",
        "alcohol_use": "light",
        "drug_use": "none",
        "caffeine_use": "low",
        "sleep_hours": "7.2",
        "sleep_quality": "good",
    }
    response = client.post("/calculate", data=payload)
    assert response.status_code == 400
    assert "Please review" in response.text
