"""Helpers to load and validate scoring constants."""

from __future__ import annotations

from pathlib import Path
from typing import Any

DEFAULT_CONSTANTS_PATH = Path(__file__).with_name("constants.yaml")
_REQUIRED_PATHS: tuple[tuple[str, ...], ...] = (
    ("thresholds", "blood_pressure", "systolic"),
    ("thresholds", "blood_pressure", "diastolic"),
    ("thresholds", "pwv"),
    ("thresholds", "bmi"),
    ("thresholds", "waist_circumference", "male"),
    ("thresholds", "waist_circumference", "female"),
    ("thresholds", "sleep_duration"),
    ("thresholds", "sleep_quality"),
    ("thresholds", "sleep_consistency"),
    ("thresholds", "smoking"),
    ("thresholds", "alcohol"),
    ("thresholds", "drug_use"),
    ("thresholds", "caffeine_use"),
    ("weights", "sleep_components"),
    ("weights", "lifestyle_components"),
    ("model", "subscores", "systems", "cardio", "components"),
    ("model", "subscores", "systems", "metabolic", "components"),
    ("model", "subscores", "systems", "lifestyle", "components"),
    ("model", "subscores", "systems", "recovery", "components"),
    ("model", "total_risk", "system_weights"),
    ("model", "age_delta", "linear", "pivot_risk"),
    ("model", "age_delta", "linear", "pivot_delta_years"),
    ("model", "age_delta", "linear", "slope_years_per_risk_point"),
    ("model", "age_delta", "caps", "min_years"),
    ("model", "age_delta", "caps", "max_years"),
)

_CACHE: dict[Path, dict[str, Any]] = {}


class ConstantsValidationError(ValueError):
    """Raised when constants are missing required structure."""


def _parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if value in {"true", "false"}:
        return value == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _load_yaml_mapping_only(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if raw_line.strip().startswith("- "):
            raise ConstantsValidationError(
                f"Unsupported YAML list syntax on line {line_number}; expected mapping-only constants"
            )

        line = raw_line.strip()
        if ":" not in line:
            raise ConstantsValidationError(f"Invalid YAML line {line_number}: {raw_line}")

        key, value_part = line.split(":", 1)
        key = key.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise ConstantsValidationError(f"Invalid indentation on line {line_number}")

        current = stack[-1][1]
        if value_part.strip() == "":
            new_node: dict[str, Any] = {}
            current[key] = new_node
            stack.append((indent, new_node))
        else:
            current[key] = _parse_scalar(value_part)

    return root


def _walk_path(constants: dict[str, Any], path: tuple[str, ...]) -> Any:
    cursor: Any = constants
    for key in path:
        if not isinstance(cursor, dict) or key not in cursor:
            joined = ".".join(path)
            raise ConstantsValidationError(f"Missing required constants key: {joined}")
        cursor = cursor[key]
    return cursor


def _validate_constants(constants: dict[str, Any]) -> None:
    for path in _REQUIRED_PATHS:
        _walk_path(constants, path)


def load_constants(path: str | Path = DEFAULT_CONSTANTS_PATH) -> dict[str, Any]:
    """Load constants yaml once per path and return a validated dictionary."""
    resolved = Path(path).expanduser().resolve()
    if resolved in _CACHE:
        return _CACHE[resolved]

    if not resolved.exists():
        raise FileNotFoundError(f"Constants file not found: {resolved}")

    raw = _load_yaml_mapping_only(resolved.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConstantsValidationError("Constants YAML root must be a mapping/object")

    _validate_constants(raw)
    _CACHE[resolved] = raw
    return raw
