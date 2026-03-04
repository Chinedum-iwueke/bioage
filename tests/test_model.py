from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bioage.constants_loader import load_constants
from bioage.model import (
    compute_biological_age,
    compute_subscores,
    compute_total_risk,
    risk_to_age_delta,
    run_model,
)
from bioage.scoring import score_request
from bioage.schema import normalize_request


def _known_request_missing_pwv():
    return normalize_request(
        {
            "demographics": {"chronological_age_years": 38, "sex": "male"},
            "vitals": {"sbp_mmHg": 128, "dbp_mmHg": 82},
            "anthropometrics": {"height_cm": 176, "weight_kg": 78, "waist_cm": 92},
            "lifestyle": {
                "smoking_status": "never",
                "alcohol_use": "light",
                "drug_use": "none",
                "caffeine_use": "moderate",
            },
            "sleep": {
                "sleep_hours": 7.5,
                "sleep_quality": "good",
                "sleep_consistency": "regular",
            },
        }
    )


def test_known_example_pipeline_with_missing_pwv() -> None:
    constants = load_constants()
    req = _known_request_missing_pwv()

    scored = score_request(req, constants)
    sub = compute_subscores(scored["metric_scores"], constants)
    total = compute_total_risk(sub["subscores"], sub["missing_metrics"], constants)
    delta = risk_to_age_delta(total["total_risk"], constants)
    bio_age = compute_biological_age(req.demographics.chronological_age_years, delta["age_delta_years"])

    assert sub["subscores"]["cardio"] == pytest.approx(float(scored["metric_scores"]["bp"]))
    assert sub["subscores"]["metabolic"] == pytest.approx(
        (float(scored["metric_scores"]["bmi"]) + float(scored["metric_scores"]["waist"])) / 2
    )
    assert sub["subscores"]["lifestyle"] == pytest.approx(float(scored["metric_scores"]["lifestyle"]))
    assert sub["subscores"]["recovery"] == pytest.approx(float(scored["metric_scores"]["sleep"]))
    assert "pwv" in sub["missing_metrics"]

    assert math.isclose(sum(total["weights_used"].values()), 1.0)
    assert 0.0 <= total["total_risk"] <= 100.0
    assert delta["age_delta_caps"]["min"] <= delta["age_delta_years"] <= delta["age_delta_caps"]["max"]
    assert bio_age == pytest.approx(req.demographics.chronological_age_years + delta["age_delta_years"])


def test_run_model_shape_and_consistency() -> None:
    constants = load_constants()
    req = _known_request_missing_pwv()

    result = run_model(req, constants)

    assert result["inputs"]["chronological_age_years"] == 38
    assert result["metric_scores"]["pwv"] is None
    assert "pwv" in result["missing_metrics"]
    assert result["biological_age_years"] == pytest.approx(result["inputs"]["chronological_age_years"] + result["age_delta_years"])


@pytest.mark.parametrize("risk", [0.0, 100.0])
def test_extreme_risk_maps_to_capped_range(risk: float) -> None:
    constants = load_constants()
    out = risk_to_age_delta(risk, constants)

    linear = constants["model"]["age_delta"]["linear"]
    caps = constants["model"]["age_delta"]["caps"]
    uncapped = float(linear["pivot_delta_years"]) + (risk - float(linear["pivot_risk"])) * float(
        linear["slope_years_per_risk_point"]
    )
    expected = max(float(caps["min_years"]), min(float(caps["max_years"]), uncapped))

    assert out["age_delta_uncapped"] == pytest.approx(uncapped)
    assert out["age_delta_years"] == pytest.approx(expected)
    assert out["age_delta_capped"] is (expected != uncapped)
