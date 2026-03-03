from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from bioage.constants_loader import load_constants
from bioage.schema import normalize_request
from bioage.scoring import (
    score_bmi,
    score_bp,
    score_lifestyle,
    score_pwv,
    score_request,
    score_sleep,
    score_waist,
)


def _parse_range(expr: str) -> tuple[str, float, float | None]:
    raw = expr.strip()
    if raw.startswith(">="):
        return (">=", float(raw[2:]), None)
    if raw.startswith("<"):
        return ("<", float(raw[1:]), None)
    if "-" in raw:
        low, high = raw.split("-", 1)
        return ("range", float(low), float(high))
    return ("eq", float(raw), None)


def _value_inside(expr: str) -> float:
    if " or " in expr:
        return _value_inside(expr.split("or", 1)[0].strip())

    kind, a, b = _parse_range(expr)
    if kind == "<":
        return a - 0.1
    if kind == ">=":
        return a
    if kind == "range":
        assert b is not None
        return (a + b) / 2
    return a


def test_bp_boundaries_from_constants() -> None:
    c = load_constants()
    sys_bp = c["thresholds"]["blood_pressure"]["systolic"]
    dia_bp = c["thresholds"]["blood_pressure"]["diastolic"]

    elevated_start = _parse_range(sys_bp["elevated"]["range"])[1]
    stage1_start = _parse_range(sys_bp["stage_1_hypertension"]["range"])[1]
    stage2_start = _parse_range(sys_bp["stage_2_hypertension"]["range"])[1]
    crisis_start_s = _parse_range(sys_bp["hypertensive_crisis"]["range"])[1]
    stage1_d_start = _parse_range(dia_bp["stage_1_hypertension"]["range"])[1]
    stage2_d_start = _parse_range(dia_bp["stage_2_hypertension"]["range"])[1]
    crisis_start_d = _parse_range(dia_bp["hypertensive_crisis"]["range"])[1]

    normal_score = int(sys_bp["normal"]["score"])
    elevated_score = int(sys_bp["elevated"]["score"])
    stage1_score = int(sys_bp["stage_1_hypertension"]["score"])
    stage2_score = int(sys_bp["stage_2_hypertension"]["score"])
    crisis_score = int(sys_bp["hypertensive_crisis"]["score"])

    assert score_bp(int(elevated_start - 1), int(stage1_d_start - 1), c) == normal_score
    assert score_bp(int(elevated_start), int(stage1_d_start - 1), c) == elevated_score
    assert score_bp(int(stage1_start), int(stage1_d_start - 1), c) == stage1_score
    assert score_bp(int(stage2_start), int(stage1_d_start - 1), c) == stage2_score
    assert score_bp(int(crisis_start_s), int(stage1_d_start - 1), c) == crisis_score

    assert score_bp(int(elevated_start - 1), int(stage1_d_start), c) == stage1_score
    assert score_bp(int(elevated_start - 1), int(stage2_d_start), c) == stage2_score
    assert score_bp(int(elevated_start - 1), int(crisis_start_d), c) == crisis_score


@pytest.mark.parametrize("bucket_name", ["optimal", "mildly_elevated", "elevated", "high"])
def test_pwv_bins_and_none(bucket_name: str) -> None:
    c = load_constants()
    mapping = c["thresholds"]["pwv"]
    assert score_pwv(None, c) is None

    value = _value_inside(mapping[bucket_name]["range"])
    assert score_pwv(value, c) == int(mapping[bucket_name]["score"])


@pytest.mark.parametrize(
    "bucket_name",
    ["underweight", "normal", "overweight", "obesity_class_1", "obesity_class_2", "obesity_class_3"],
)
def test_bmi_bins(bucket_name: str) -> None:
    c = load_constants()
    mapping = c["thresholds"]["bmi"]
    value = _value_inside(mapping[bucket_name]["range"])
    assert score_bmi(value, c) == int(mapping[bucket_name]["score"])


@pytest.mark.parametrize("sex", ["male", "female"])
def test_waist_bins_by_sex(sex: str) -> None:
    c = load_constants()
    mapping = c["thresholds"]["waist_circumference"][sex]
    for bucket_name, bucket in mapping.items():
        value = _value_inside(bucket["range"])
        assert score_waist(sex, value, c) == int(bucket["score"]), bucket_name


def test_sleep_components_and_weighted_aggregate() -> None:
    c = load_constants()
    duration_mapping = c["thresholds"]["sleep_duration"]
    quality_mapping = c["thresholds"]["sleep_quality"]
    consistency_mapping = c["thresholds"]["sleep_consistency"]
    weights = c["weights"]["sleep_components"]

    duration_value = _value_inside(duration_mapping["short_or_long_mild"]["range"])
    quality_key = "fair"
    consistency_key = "somewhat_regular"

    expected = round(
        float(duration_mapping["short_or_long_mild"]["score"]) * float(weights["duration"])
        + float(quality_mapping[quality_key]["score"]) * float(weights["quality"])
        + float(consistency_mapping[consistency_key]["score"]) * float(weights["consistency"])
    )

    assert (
        score_sleep(duration_value, quality_key, consistency_key, c)
        == expected
    )


def test_lifestyle_components_and_weighted_aggregate() -> None:
    c = load_constants()
    smoking_key = "current"
    alcohol_key = "moderate"
    drug_key = "occasional"
    caffeine_key = "high"

    weights = c["weights"]["lifestyle_components"]
    expected = round(
        float(c["thresholds"]["smoking"][smoking_key]["score"]) * float(weights["smoking"])
        + float(c["thresholds"]["alcohol"][alcohol_key]["score"]) * float(weights["alcohol"])
        + float(c["thresholds"]["drug_use"][drug_key]["score"]) * float(weights["drug_use"])
        + float(c["thresholds"]["caffeine_use"][caffeine_key]["score"]) * float(weights["caffeine_use"])
    )

    assert score_lifestyle(smoking_key, alcohol_key, drug_key, caffeine_key, c) == expected


def test_score_request_sets_pwv_missing_note() -> None:
    c = load_constants()
    req = normalize_request(
        {
            "demographics": {"chronological_age_years": 40, "sex": "male"},
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

    scored = score_request(req, c)

    assert scored["metric_scores"]["pwv"] is None
    assert scored["notes"]["pwv_missing"] is True
