"""Schema and normalization for biological-age questionnaire inputs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from bioage.guards import GuardFlag, add_flag, flags_to_json, merge_flags, unit_and_input_flags, warning_messages


class SchemaValidationError(ValueError):
    """Raised when an input payload fails schema validation."""


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"


class SmokingStatus(str, Enum):
    NEVER = "never"
    FORMER = "former"
    CURRENT = "current"


class AlcoholUse(str, Enum):
    NONE = "none"
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"


class DrugUse(str, Enum):
    NONE = "none"
    OCCASIONAL = "occasional"
    REGULAR = "regular"


class CaffeineUse(str, Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class SleepQuality(str, Enum):
    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"


class SleepConsistency(str, Enum):
    IRREGULAR = "irregular"
    SOMEWHAT_REGULAR = "somewhat_regular"
    REGULAR = "regular"


@dataclass
class DemographicsInput:
    chronological_age_years: int
    sex: Sex


@dataclass
class VitalsInput:
    sbp_mmHg: int
    dbp_mmHg: int
    pwv_m_per_s: float | None = None


@dataclass
class AnthropometricsInput:
    height_cm: float | None = None
    weight_kg: float | None = None
    bmi: float | None = None
    waist_cm: float = 0.0


@dataclass
class LifestyleInput:
    smoking_status: SmokingStatus
    alcohol_use: AlcoholUse
    drug_use: DrugUse
    caffeine_use: CaffeineUse


@dataclass
class SleepInput:
    sleep_hours: float
    sleep_quality: SleepQuality
    sleep_consistency: SleepConsistency


@dataclass
class BioAgeRequest:
    demographics: DemographicsInput
    vitals: VitalsInput
    anthropometrics: AnthropometricsInput
    lifestyle: LifestyleInput
    sleep: SleepInput
    client_metadata: dict[str, Any] | None = None
    measurement_metadata: dict[str, Any] | None = None
    submitted_at: str | None = None
    model_version: str | None = None
    warnings: list[str] = field(default_factory=list)
    guard_flags: list[GuardFlag] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["guard_flags"] = flags_to_json(self.guard_flags)
        return data


@dataclass
class ClientMetadata:
    prepared_for: str = "Demo Client"
    date: str = "1970-01-01"
    client_id: str = "CLIENT-DEMO"
    security_key: str = "SEC-DEMO"
    consultant_id: str = "CONSULTANT-DEMO"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DemoResult:
    disclaimer: str = (
        "Educational wellness estimation only. This report is not a diagnosis, "
        "medical advice, or treatment plan."
    )
    actual_age: int = 40
    biological_age: int = 42
    arterial_stiffness_label: str = "Placeholder"
    bmi_label: str = "Placeholder"
    systolic_label: str = "Placeholder"
    diastolic_label: str = "Placeholder"

    def to_dict(self) -> dict:
        return asdict(self)


def _require_dict(raw: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise SchemaValidationError(f"{field_name} must be an object")
    return raw


def _normalize_enum(value: Any, enum_type: type[Enum], field_name: str):
    if isinstance(value, str):
        normalized = value.strip().lower()
    else:
        normalized = value
    try:
        return enum_type(normalized)
    except Exception as exc:
        allowed = ", ".join(member.value for member in enum_type)
        raise SchemaValidationError(f"{field_name} must be one of: {allowed}") from exc


def _parse_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except Exception as exc:
        raise SchemaValidationError(f"{field_name} must be an integer") from exc


def _parse_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except Exception as exc:
        raise SchemaValidationError(f"{field_name} must be a number") from exc


def _check_range(value: float, field_name: str, low: float, high: float) -> None:
    if not low <= value <= high:
        raise SchemaValidationError(f"{field_name} must be between {low} and {high}")


def _computed_bmi(height_cm: float, weight_kg: float) -> float:
    h_m = height_cm / 100.0
    return weight_kg / (h_m * h_m)


def normalize_request(raw: dict[str, Any]) -> BioAgeRequest:
    payload = _require_dict(raw, "request")
    guard_flags: list[GuardFlag] = []

    demographics_raw = _require_dict(payload.get("demographics"), "demographics")
    vitals_raw = _require_dict(payload.get("vitals"), "vitals")
    anthropometrics_raw = _require_dict(payload.get("anthropometrics"), "anthropometrics")
    lifestyle_raw = _require_dict(payload.get("lifestyle"), "lifestyle")
    sleep_raw = _require_dict(payload.get("sleep"), "sleep")

    age = _parse_int(demographics_raw.get("chronological_age_years"), "demographics.chronological_age_years")
    _check_range(age, "demographics.chronological_age_years", 10, 120)
    sex = _normalize_enum(demographics_raw.get("sex"), Sex, "demographics.sex")
    demographics = DemographicsInput(chronological_age_years=age, sex=sex)

    sbp = _parse_int(vitals_raw.get("sbp_mmHg"), "vitals.sbp_mmHg")
    dbp = _parse_int(vitals_raw.get("dbp_mmHg"), "vitals.dbp_mmHg")
    _check_range(sbp, "vitals.sbp_mmHg", 70, 260)
    _check_range(dbp, "vitals.dbp_mmHg", 40, 160)
    pwv = vitals_raw.get("pwv_m_per_s")
    pwv_parsed = None
    if pwv is not None:
        pwv_parsed = _parse_float(pwv, "vitals.pwv_m_per_s")
        _check_range(pwv_parsed, "vitals.pwv_m_per_s", 3.0, 25.0)
    vitals = VitalsInput(sbp_mmHg=sbp, dbp_mmHg=dbp, pwv_m_per_s=pwv_parsed)

    height_raw = anthropometrics_raw.get("height_cm")
    weight_raw = anthropometrics_raw.get("weight_kg")
    bmi_raw = anthropometrics_raw.get("bmi")
    waist_raw = anthropometrics_raw.get("waist_cm")

    if waist_raw is None:
        raise SchemaValidationError("anthropometrics.waist_cm is required")
    waist = _parse_float(waist_raw, "anthropometrics.waist_cm")
    _check_range(waist, "anthropometrics.waist_cm", 20, 200)

    height = _parse_float(height_raw, "anthropometrics.height_cm") if height_raw is not None else None
    weight = _parse_float(weight_raw, "anthropometrics.weight_kg") if weight_raw is not None else None
    bmi = _parse_float(bmi_raw, "anthropometrics.bmi") if bmi_raw is not None else None

    if (height is None) != (weight is None):
        raise SchemaValidationError("anthropometrics.height_cm and anthropometrics.weight_kg must be provided together")
    if height is None and bmi is None:
        raise SchemaValidationError("Provide either anthropometrics.bmi or both height_cm and weight_kg")

    if height is not None:
        _check_range(height, "anthropometrics.height_cm", 90, 260)
    if weight is not None:
        _check_range(weight, "anthropometrics.weight_kg", 20, 250)
    if bmi is not None:
        _check_range(bmi, "anthropometrics.bmi", 12, 70)

    if height is not None and weight is not None:
        computed = round(_computed_bmi(height, weight), 2)
        if bmi is not None and abs(bmi - computed) > 2.0:
            add_flag(
                guard_flags,
                "BMI_MISMATCH_COMPUTED",
                "warning",
                "BMI mismatch; using BMI computed from height/weight.",
                "anthropometrics.bmi",
            )
        bmi = computed

    anthropometrics = AnthropometricsInput(height_cm=height, weight_kg=weight, bmi=bmi, waist_cm=waist)

    lifestyle = LifestyleInput(
        smoking_status=_normalize_enum(lifestyle_raw.get("smoking_status"), SmokingStatus, "lifestyle.smoking_status"),
        alcohol_use=_normalize_enum(lifestyle_raw.get("alcohol_use"), AlcoholUse, "lifestyle.alcohol_use"),
        drug_use=_normalize_enum(lifestyle_raw.get("drug_use"), DrugUse, "lifestyle.drug_use"),
        caffeine_use=_normalize_enum(lifestyle_raw.get("caffeine_use"), CaffeineUse, "lifestyle.caffeine_use"),
    )

    sleep_hours = _parse_float(sleep_raw.get("sleep_hours"), "sleep.sleep_hours")
    _check_range(sleep_hours, "sleep.sleep_hours", 0, 16)
    sleep = SleepInput(
        sleep_hours=sleep_hours,
        sleep_quality=_normalize_enum(sleep_raw.get("sleep_quality"), SleepQuality, "sleep.sleep_quality"),
        sleep_consistency=_normalize_enum(
            sleep_raw.get("sleep_consistency"), SleepConsistency, "sleep.sleep_consistency"
        ),
    )

    if pwv_parsed is None:
        add_flag(
            guard_flags,
            "MISSING_PWV",
            "info",
            "PWV missing; vascular stiffness signal unavailable.",
            "vitals.pwv_m_per_s",
        )
    if age <= 12 or age >= 100:
        add_flag(
            guard_flags,
            "AGE_BOUNDARY_CHECK",
            "info",
            "Age near boundary; confirm years entered correctly.",
            "demographics.chronological_age_years",
        )
    if bmi is not None and (bmi <= 14 or bmi >= 55):
        add_flag(
            guard_flags,
            "BMI_NEAR_LIMIT",
            "info",
            "BMI near limit; confirm height and weight values.",
            "anthropometrics.bmi",
        )

    guard_flags = merge_flags(
        guard_flags,
        unit_and_input_flags(
            age=age,
            waist_cm=waist,
            height_cm=height,
            weight_kg=weight,
            sbp_mmHg=sbp,
            dbp_mmHg=dbp,
            sleep_hours=sleep_hours,
            pwv_m_per_s=pwv_parsed,
        ),
    )

    submitted_at = payload.get("submitted_at") or datetime.now(timezone.utc).isoformat()
    if not isinstance(submitted_at, str):
        raise SchemaValidationError("submitted_at must be an ISO timestamp string")

    client_metadata = payload.get("client_metadata")
    if client_metadata is not None and not isinstance(client_metadata, dict):
        raise SchemaValidationError("client_metadata must be an object")
    measurement_metadata = payload.get("measurement_metadata")
    if measurement_metadata is not None and not isinstance(measurement_metadata, dict):
        raise SchemaValidationError("measurement_metadata must be an object")

    model_version = payload.get("model_version")
    if model_version is not None and not isinstance(model_version, str):
        raise SchemaValidationError("model_version must be a string")

    warnings = warning_messages(guard_flags)

    return BioAgeRequest(
        demographics=demographics,
        vitals=vitals,
        anthropometrics=anthropometrics,
        lifestyle=lifestyle,
        sleep=sleep,
        client_metadata=client_metadata,
        measurement_metadata=measurement_metadata,
        submitted_at=submitted_at,
        model_version=model_version,
        warnings=warnings,
        guard_flags=guard_flags,
    )
