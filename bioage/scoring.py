"""Deterministic config-driven scoring functions."""

from __future__ import annotations

from typing import Any

from bioage.constants_loader import load_constants
from bioage.schema import BioAgeRequest

_EPSILON = 1e-9


def _clamp_0_100(value: float) -> int:
    return int(round(max(0, min(100, value))))


def _score_from_mapping(mapping: dict[str, Any], key: str, label: str) -> float:
    if key not in mapping:
        allowed = ", ".join(sorted(mapping.keys()))
        raise ValueError(f"Unsupported {label}: {key}. Allowed values: {allowed}")
    entry = mapping[key]
    if not isinstance(entry, dict) or "score" not in entry:
        raise ValueError(f"Constants entry for {label}='{key}' must include a score")
    return float(entry["score"])


def _matches_clause(value: float, clause: str) -> bool:
    token = clause.strip()
    if token.startswith("<="):
        return value <= float(token[2:]) + _EPSILON
    if token.startswith(">="):
        return value + _EPSILON >= float(token[2:])
    if token.startswith("<"):
        return value < float(token[1:])
    if token.startswith(">"):
        return value > float(token[1:])
    if "-" in token:
        low_raw, high_raw = token.split("-", 1)
        low = float(low_raw)
        high = float(high_raw)
        return (value + _EPSILON) >= low and value <= high + _EPSILON
    return abs(value - float(token)) <= _EPSILON


def _score_from_ranged_mapping(value: float, mapping: dict[str, Any], label: str) -> int:
    for bucket_name, bucket in mapping.items():
        range_expr = bucket.get("range")
        if not isinstance(range_expr, str):
            raise ValueError(f"Constants entry '{label}.{bucket_name}' must include a string range")
        clauses = [part.strip() for part in range_expr.split("or")]
        if any(_matches_clause(value, clause) for clause in clauses):
            return _clamp_0_100(float(bucket["score"]))
    raise ValueError(f"No {label} range matched value: {value}")


def score_bp(sbp_mmHg: int, dbp_mmHg: int, constants: dict[str, Any]) -> int:
    """Score BP by explicit category precedence using config-driven thresholds.

    Logic: check highest-severity categories first; a category matches when either
    systolic or diastolic value falls in that category.
    """
    systolic = constants["thresholds"]["blood_pressure"]["systolic"]
    diastolic = constants["thresholds"]["blood_pressure"]["diastolic"]

    category_order = [
        "hypertensive_crisis",
        "stage_2_hypertension",
        "stage_1_hypertension",
        "elevated",
        "normal",
    ]

    for category in category_order:
        s_cat = systolic.get(category)
        d_cat = diastolic.get(category)
        matches_s = bool(s_cat and _matches_clause(float(sbp_mmHg), s_cat["range"]))
        matches_d = bool(d_cat and _matches_clause(float(dbp_mmHg), d_cat["range"]))
        if matches_s or matches_d:
            if s_cat and "score" in s_cat:
                return _clamp_0_100(float(s_cat["score"]))
            if d_cat and "score" in d_cat:
                return _clamp_0_100(float(d_cat["score"]))
            raise ValueError(f"Blood pressure category '{category}' lacks score")

    raise ValueError("No blood pressure category matched provided SBP/DBP")


def score_pwv(pwv_m_per_s: float | None, constants: dict[str, Any]) -> int | None:
    if pwv_m_per_s is None:
        return None
    return _score_from_ranged_mapping(float(pwv_m_per_s), constants["thresholds"]["pwv"], "thresholds.pwv")


def score_bmi(bmi: float, constants: dict[str, Any]) -> int:
    return _score_from_ranged_mapping(float(bmi), constants["thresholds"]["bmi"], "thresholds.bmi")


def score_waist(sex: str, waist_cm: float, constants: dict[str, Any]) -> int:
    sex_key = sex.lower().strip()
    waist_constants = constants["thresholds"]["waist_circumference"]
    if sex_key not in waist_constants:
        allowed = ", ".join(sorted(waist_constants.keys()))
        raise ValueError(f"Unsupported sex for waist scoring: {sex}. Allowed values: {allowed}")
    return _score_from_ranged_mapping(float(waist_cm), waist_constants[sex_key], f"thresholds.waist_circumference.{sex_key}")


def score_sleep(
    sleep_hours: float,
    sleep_quality: str,
    sleep_consistency: str,
    constants: dict[str, Any],
) -> int:
    duration_score = _score_from_ranged_mapping(
        float(sleep_hours), constants["thresholds"]["sleep_duration"], "thresholds.sleep_duration"
    )
    quality_score = _score_from_mapping(constants["thresholds"]["sleep_quality"], sleep_quality, "sleep_quality")
    consistency_score = _score_from_mapping(
        constants["thresholds"]["sleep_consistency"], sleep_consistency, "sleep_consistency"
    )

    weights = constants["weights"]["sleep_components"]
    total = (
        duration_score * float(weights["duration"])
        + quality_score * float(weights["quality"])
        + consistency_score * float(weights["consistency"])
    )
    return _clamp_0_100(total)


def score_lifestyle(
    smoking_status: str,
    alcohol_use: str,
    drug_use: str,
    caffeine_use: str,
    constants: dict[str, Any],
) -> int:
    smoking_score = _score_from_mapping(constants["thresholds"]["smoking"], smoking_status, "smoking_status")
    alcohol_score = _score_from_mapping(constants["thresholds"]["alcohol"], alcohol_use, "alcohol_use")
    drug_score = _score_from_mapping(constants["thresholds"]["drug_use"], drug_use, "drug_use")
    caffeine_score = _score_from_mapping(constants["thresholds"]["caffeine_use"], caffeine_use, "caffeine_use")

    weights = constants["weights"]["lifestyle_components"]
    total = (
        smoking_score * float(weights["smoking"])
        + alcohol_score * float(weights["alcohol"])
        + drug_score * float(weights["drug_use"])
        + caffeine_score * float(weights["caffeine_use"])
    )
    return _clamp_0_100(total)


def score_request(req: BioAgeRequest, constants: dict[str, Any] | None = None) -> dict[str, Any]:
    config = constants if constants is not None else load_constants()

    pwv_score = score_pwv(req.vitals.pwv_m_per_s, config)
    metric_scores = {
        "bp": score_bp(req.vitals.sbp_mmHg, req.vitals.dbp_mmHg, config),
        "pwv": pwv_score,
        "bmi": score_bmi(float(req.anthropometrics.bmi), config),
        "waist": score_waist(req.demographics.sex.value, req.anthropometrics.waist_cm, config),
        "sleep": score_sleep(
            req.sleep.sleep_hours,
            req.sleep.sleep_quality.value,
            req.sleep.sleep_consistency.value,
            config,
        ),
        "lifestyle": score_lifestyle(
            req.lifestyle.smoking_status.value,
            req.lifestyle.alcohol_use.value,
            req.lifestyle.drug_use.value,
            req.lifestyle.caffeine_use.value,
            config,
        ),
    }

    return {
        "metric_scores": metric_scores,
        "notes": {"pwv_missing": pwv_score is None},
    }
