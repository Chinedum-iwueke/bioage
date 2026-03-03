from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from bioage.schema import SchemaValidationError, normalize_request


def _base_request() -> dict:
    return {
        "demographics": {"chronological_age_years": 42, "sex": "female"},
        "vitals": {"sbp_mmHg": 120, "dbp_mmHg": 78},
        "anthropometrics": {"height_cm": 170, "weight_kg": 68, "waist_cm": 80},
        "lifestyle": {
            "smoking_status": "never",
            "alcohol_use": "light",
            "drug_use": "none",
            "caffeine_use": "low",
        },
        "sleep": {
            "sleep_hours": 7.0,
            "sleep_quality": "good",
            "sleep_consistency": "regular",
        },
    }


def test_valid_minimal_request_computes_bmi() -> None:
    payload = _base_request()
    normalized = normalize_request(payload)

    assert normalized.vitals.pwv_m_per_s is None
    assert normalized.anthropometrics.bmi == pytest.approx(23.53, abs=0.01)
    assert any("PWV missing" in warning for warning in normalized.warnings)


def test_bmi_only_without_height_weight_passes() -> None:
    payload = _base_request()
    payload["anthropometrics"] = {"bmi": 26.2, "waist_cm": 92}

    normalized = normalize_request(payload)

    assert normalized.anthropometrics.bmi == pytest.approx(26.2)
    assert normalized.anthropometrics.height_cm is None
    assert normalized.anthropometrics.weight_kg is None


def test_bmi_mismatch_generates_warning_and_prefers_computed() -> None:
    payload = _base_request()
    payload["anthropometrics"]["bmi"] = 30.0

    normalized = normalize_request(payload)

    assert normalized.anthropometrics.bmi == pytest.approx(23.53, abs=0.01)
    assert any("BMI mismatch" in warning for warning in normalized.warnings)


def test_waist_likely_inches_generates_warning() -> None:
    payload = _base_request()
    payload["anthropometrics"]["waist_cm"] = 50

    normalized = normalize_request(payload)

    assert any("Waist seems low" in warning for warning in normalized.warnings)


def test_invalid_sbp_out_of_range_raises_validation_error() -> None:
    payload = _base_request()
    payload["vitals"]["sbp_mmHg"] = 300

    with pytest.raises(SchemaValidationError) as exc_info:
        normalize_request(payload)

    assert "sbp_mmHg" in str(exc_info.value)


def test_enum_values_normalize_case() -> None:
    payload = _base_request()
    payload["lifestyle"]["smoking_status"] = "CURRENT"

    normalized = normalize_request(payload)

    assert normalized.lifestyle.smoking_status.value == "current"
