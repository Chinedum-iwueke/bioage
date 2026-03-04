from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bioage.constants_loader import load_constants
from bioage.explain import (
    build_explanation_bundle,
    generate_recommendations,
    simulate_counterfactuals,
)
from bioage.model import run_model
from bioage.scoring import score_request
from bioage.schema import normalize_request, AlcoholUse, CaffeineUse, DrugUse, SmokingStatus


def _base_payload() -> dict:
    return {
        "demographics": {"chronological_age_years": 44, "sex": "male"},
        "vitals": {"sbp_mmHg": 132, "dbp_mmHg": 86, "pwv_m_per_s": 9.6},
        "anthropometrics": {"height_cm": 176, "weight_kg": 88, "waist_cm": 108},
        "lifestyle": {
            "smoking_status": "current",
            "alcohol_use": "moderate",
            "drug_use": "occasional",
            "caffeine_use": "high",
        },
        "sleep": {
            "sleep_hours": 5.0,
            "sleep_quality": "fair",
            "sleep_consistency": "irregular",
        },
    }


def test_explanation_bundle_is_deterministic() -> None:
    constants = load_constants()
    req = normalize_request(_base_payload())
    result = run_model(req, constants)

    one = build_explanation_bundle(req, result, constants)
    two = build_explanation_bundle(req, result, constants)

    assert one == two
    assert json.dumps(one, sort_keys=True) == json.dumps(two, sort_keys=True)


def test_driver_ranking_waist_high_priority() -> None:
    constants = load_constants()
    payload = _base_payload()
    payload["anthropometrics"]["waist_cm"] = 125
    payload["anthropometrics"]["weight_kg"] = 79
    req = normalize_request(payload)
    result = run_model(req, constants)
    bundle = build_explanation_bundle(req, result, constants)

    systems = bundle["drivers"]["system_contributions"]
    metrics = bundle["drivers"]["metric_drivers"]

    assert systems[0]["system"] in {"metabolic", "cardio"}
    top_metric_names = [entry["metric"] for entry in metrics[:3]]
    assert "waist" in top_metric_names


def test_counterfactual_bp_improvement_reduces_risk_and_age_delta() -> None:
    constants = load_constants()
    payload = _base_payload()
    payload["vitals"]["sbp_mmHg"] = 165
    payload["vitals"]["dbp_mmHg"] = 102
    req = normalize_request(payload)

    cfs = simulate_counterfactuals(req, constants)["counterfactuals"]
    bp_cf = [item for item in cfs if "blood pressure" in item["name"].lower()][0]

    assert bp_cf["total_risk_change"] < 0
    assert bp_cf["age_delta_change"] < 0


def test_recommendation_mapping_has_all_lifestyle_keys() -> None:
    constants = load_constants()
    payload = _base_payload()

    for smoking in SmokingStatus:
        for alcohol in AlcoholUse:
            for drug in DrugUse:
                for caffeine in CaffeineUse:
                    payload["lifestyle"]["smoking_status"] = smoking.value
                    payload["lifestyle"]["alcohol_use"] = alcohol.value
                    payload["lifestyle"]["drug_use"] = drug.value
                    payload["lifestyle"]["caffeine_use"] = caffeine.value
                    req = normalize_request(payload)
                    scored = score_request(req, constants)
                    rec = generate_recommendations(req, scored["metric_scores"], constants)
                    assert rec["recommendations"]["smoking"]
                    assert rec["recommendations"]["alcohol"]
                    assert rec["recommendations"]["drug_use"]
                    assert rec["recommendations"]["caffeine_use"]
