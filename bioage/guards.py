"""Centralized guardrail flags and deterministic input heuristics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Severity = Literal["info", "warning", "error"]


@dataclass(frozen=True)
class GuardFlag:
    code: str
    severity: Severity
    message: str
    field: str | None = None


def add_flag(
    flags: list[GuardFlag],
    code: str,
    severity: Severity,
    message: str,
    field: str | None = None,
) -> None:
    flags.append(GuardFlag(code=code, severity=severity, message=message, field=field))


def merge_flags(*flag_lists: list[GuardFlag]) -> list[GuardFlag]:
    merged: list[GuardFlag] = []
    for flag_list in flag_lists:
        merged.extend(flag_list)
    return merged


def flags_to_json(flags: list[GuardFlag]) -> list[dict[str, str | None]]:
    return [asdict(flag) for flag in flags]


def flags_from_json(raw: list[dict[str, str | None]] | list[str] | None) -> list[GuardFlag]:
    if not raw:
        return []
    parsed: list[GuardFlag] = []
    for entry in raw:
        if isinstance(entry, str):
            parsed.append(GuardFlag(code="LEGACY_WARNING", severity="warning", message=entry, field=None))
            continue
        parsed.append(
            GuardFlag(
                code=str(entry.get("code") or "UNKNOWN"),
                severity=str(entry.get("severity") or "warning"),
                message=str(entry.get("message") or ""),
                field=str(entry["field"]) if entry.get("field") is not None else None,
            )
        )
    return parsed


def warning_messages(flags: list[GuardFlag]) -> list[str]:
    return [flag.message for flag in flags]


def unit_and_input_flags(
    *,
    age: int,
    waist_cm: float,
    height_cm: float | None,
    weight_kg: float | None,
    sbp_mmHg: int,
    dbp_mmHg: int,
    sleep_hours: float,
    pwv_m_per_s: float | None,
) -> list[GuardFlag]:
    flags: list[GuardFlag] = []

    if waist_cm < 55 and age >= 16:
        add_flag(
            flags,
            "UNIT_SUSPECT_WAIST_IN",
            "warning",
            "Waist seems low; confirm unit is cm (not inches).",
            "anthropometrics.waist_cm",
        )
    elif 55 <= waist_cm <= 70:
        add_flag(
            flags,
            "UNIT_VERIFY_WAIST_METHOD",
            "info",
            "Verify waist measurement method (at navel).",
            "anthropometrics.waist_cm",
        )
    elif waist_cm > 160:
        add_flag(
            flags,
            "UNIT_SUSPECT_WAIST_HIGH",
            "warning",
            "Waist seems high; confirm entry.",
            "anthropometrics.waist_cm",
        )

    if height_cm is not None:
        if 90 <= height_cm <= 130:
            add_flag(
                flags,
                "UNIT_SUSPECT_HEIGHT_CM",
                "warning",
                "Height seems low; confirm cm (not inches).",
                "anthropometrics.height_cm",
            )
        elif height_cm > 230:
            add_flag(
                flags,
                "HEIGHT_OUTLIER_HIGH",
                "error",
                "Height is outside expected range; please re-check entry.",
                "anthropometrics.height_cm",
            )

    if weight_kg is not None:
        if 20 <= weight_kg <= 35 and age >= 16:
            add_flag(
                flags,
                "UNIT_SUSPECT_WEIGHT_KG_LOW",
                "warning",
                "Weight seems low; confirm kg (not lb).",
                "anthropometrics.weight_kg",
            )
        elif weight_kg > 200:
            add_flag(
                flags,
                "UNIT_SUSPECT_WEIGHT_KG_HIGH",
                "warning",
                "Weight seems high; confirm entry.",
                "anthropometrics.weight_kg",
            )

    if sbp_mmHg < 80 or sbp_mmHg > 240:
        add_flag(flags, "BP_SBP_OUTLIER", "warning", "Systolic BP seems unusual; confirm mmHg value.", "vitals.sbp_mmHg")

    if dbp_mmHg < 45 or dbp_mmHg > 140:
        add_flag(
            flags,
            "BP_DBP_OUTLIER",
            "warning",
            "Diastolic BP seems unusual; confirm mmHg value.",
            "vitals.dbp_mmHg",
        )

    if sleep_hours < 3 or sleep_hours > 12:
        add_flag(flags, "SLEEP_HOURS_OUTLIER", "warning", "Sleep hours seem unusual; confirm average hours/night.", "sleep.sleep_hours")

    if pwv_m_per_s is not None and (pwv_m_per_s < 4.0 or pwv_m_per_s > 18.0):
        add_flag(flags, "PWV_OUTLIER", "warning", "PWV seems unusual; confirm m/s value.", "vitals.pwv_m_per_s")

    return flags
