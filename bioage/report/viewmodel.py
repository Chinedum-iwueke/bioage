"""View-model builder for deterministic report rendering."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bioage.scoring import label_bmi, label_bp, label_pwv
from bioage.schema import BioAgeRequest


def _titleize(label: str | None) -> str:
    if label is None:
        return "Not provided"
    return label.replace("_", " ").title()


def _tips_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(v) for v in raw]
    if isinstance(raw, str):
        value = raw.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            if not inner:
                return []
            return [part.strip().strip("\"'") for part in inner.split(",")]
        return [value]
    return []


def _range_to_min_max(expr: str, default_min: float = 0.0, prev_max: float = 0.0) -> tuple[float, float]:
    token = expr.strip()
    if token.startswith("<"):
        high = float(token[1:])
        return default_min if prev_max == 0 else prev_max, high
    if token.startswith(">="):
        low = float(token[2:])
        return low, low + 25.0
    if "-" in token:
        low, high = token.split("-", 1)
        return float(low), float(high)
    return prev_max, prev_max + 10.0


def build_bands(mapping: dict[str, Any], palette: list[str]) -> list[dict[str, Any]]:
    bands: list[dict[str, Any]] = []
    prev_max = 0.0
    for idx, (name, info) in enumerate(mapping.items()):
        range_expr = str(info.get("range", ""))
        min_v, max_v = _range_to_min_max(range_expr, default_min=0.0, prev_max=prev_max)
        if idx == len(mapping) - 1 and range_expr.startswith(">="):
            max_v = min_v + 40.0
        if max_v <= min_v:
            max_v = min_v + 1.0
        prev_max = max_v
        bands.append(
            {
                "label": _titleize(name),
                "min": round(min_v, 2),
                "max": round(max_v, 2),
                "color": palette[min(idx, len(palette) - 1)],
            }
        )
    return bands


def build_report_context(req: BioAgeRequest, result: dict, explanations: dict, constants: dict) -> dict[str, Any]:
    now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    meta = req.client_metadata or {}

    bp_label = label_bp(req.vitals.sbp_mmHg, req.vitals.dbp_mmHg, constants)
    bmi_label = label_bmi(float(req.anthropometrics.bmi), constants)
    pwv_label = label_pwv(req.vitals.pwv_m_per_s, constants)

    metric_drivers = explanations.get("drivers", {}).get("metric_drivers", [])
    top_drivers = [d for d in metric_drivers[:3]]

    recs = explanations.get("recommendations", {}).get("recommendations", {})
    lifestyle_notes: list[str] = []
    for key in ["bmi", "waist", "smoking", "sleep_duration", "sleep_quality", "sleep_consistency"]:
        lifestyle_notes.extend(_tips_list(recs.get(key, [])))

    context = {
        "generated_at": now_iso,
        "model_version": result.get("model_version", "unknown"),
        "disclaimer": explanations.get("disclaimer_short") or constants.get("copy", {}).get("disclaimer_short", ""),
        "client": {
            "prepared_for": meta.get("prepared_for") or meta.get("client_name") or meta.get("name") or "Client",
            "consultant_id": meta.get("consultant_id", "CONSULTANT-PLACEHOLDER"),
            "client_id": meta.get("client_id", "CLIENT-PLACEHOLDER"),
            "security_key": meta.get("security_key", "SECURITY-PLACEHOLDER"),
        },
        "headline": {
            "chronological_age": round(float(result["inputs"]["chronological_age_years"]), 1),
            "biological_age": round(float(result["biological_age_years"]), 1),
            "age_delta": round(float(result["age_delta_years"]), 1),
            "total_risk": round(float(result["total_risk"]), 1),
        },
        "vitals": {
            "pwv": None if req.vitals.pwv_m_per_s is None else round(float(req.vitals.pwv_m_per_s), 1),
            "pwv_label": _titleize(pwv_label),
            "bmi": round(float(req.anthropometrics.bmi), 1),
            "bmi_label": _titleize(bmi_label),
            "sbp": int(req.vitals.sbp_mmHg),
            "dbp": int(req.vitals.dbp_mmHg),
            "bp_label": _titleize(bp_label),
        },
        "subscores": {k: (None if v is None else round(float(v), 1)) for k, v in result.get("subscores", {}).items()},
        "top_drivers": top_drivers,
        "recommendations": recs,
        "priority_actions": explanations.get("recommendations", {}).get("priority_actions", []),
        "counterfactuals": explanations.get("counterfactuals", {}).get("counterfactuals", []),
        "estimated_years_recoverable": round(
            float(explanations.get("counterfactuals", {}).get("estimated_years_recoverable", 0.0)), 1
        ),
        "missing_metrics": result.get("missing_metrics", []),
        "warnings": result.get("warnings", []),
        "domain_summaries": explanations.get("domain_summaries", {}),
        "further_testing": [
            "Discuss persistent high blood pressure readings with a qualified clinician.",
            "Consider periodic lipid and glucose monitoring for cardiometabolic context.",
            "Track sleep quality and activity trends for 8-12 weeks before reassessment.",
        ],
        "lifestyle_notes": lifestyle_notes,
    }
    return context
