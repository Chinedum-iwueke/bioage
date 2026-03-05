from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.helptext import FIELD_HELP, FIELD_RANGES


def _loc_to_path(loc: tuple[Any, ...] | list[Any]) -> str:
    items = [str(part) for part in loc if part not in {"body", "query", "path"}]
    return ".".join(items)


def _append_range_hint(field_path: str, message: str) -> str:
    range_values = FIELD_RANGES.get(field_path)
    if not range_values:
        return message

    field_name = field_path.split(".")[-1]
    unit = str(FIELD_HELP.get(field_name, {}).get("unit", "")).strip()
    low, high = range_values
    suffix = f" {unit}" if unit and unit != "category" else ""
    return f"{message.rstrip('.')} (accepted range {low:g}–{high:g}{suffix})."


def parse_validation_error(exc: Exception) -> tuple[dict[str, str], str]:
    summary = "Please correct the highlighted fields"
    errors: dict[str, str] = {}

    if isinstance(exc, ValidationError):
        for err in exc.errors():
            field_path = _loc_to_path(err.get("loc", ()))
            if not field_path:
                continue
            message = str(err.get("msg", "Invalid input"))
            errors[field_path] = _append_range_hint(field_path, message)
        return errors, summary

    raw_message = str(exc).strip() or "Invalid input"
    known_field = None
    for field_path in FIELD_RANGES:
        if field_path in raw_message:
            known_field = field_path
            break

    if known_field:
        errors[known_field] = _append_range_hint(known_field, raw_message)
    else:
        errors["form"] = raw_message
    return errors, summary
