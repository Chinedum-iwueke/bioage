"""Deterministic composite model for biological-age estimation."""

from __future__ import annotations

from typing import Any

from bioage import __version__
from bioage.constants_loader import load_constants
from bioage.guards import flags_to_json
from bioage.schema import BioAgeRequest
from bioage.scoring import score_request


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _resolve_subscore_config(constants: dict[str, Any]) -> tuple[dict[str, Any], str]:
    model_cfg = constants.get("model", {})
    sub_cfg = model_cfg.get("subscores", {}) if isinstance(model_cfg, dict) else {}
    systems = sub_cfg.get("systems") if isinstance(sub_cfg, dict) else None
    aggregation_default = str(sub_cfg.get("aggregation_default", "mean")) if isinstance(sub_cfg, dict) else "mean"

    if isinstance(systems, dict) and systems:
        return systems, aggregation_default

    # Minimal compatibility fallback for older constants shapes.
    return {
        "cardio": {"components": ["bp", "pwv"], "aggregation": "mean"},
        "metabolic": {"components": ["bmi", "waist"], "aggregation": "mean"},
        "lifestyle": {"components": ["lifestyle"], "aggregation": "mean"},
        "recovery": {"components": ["sleep"], "aggregation": "mean"},
    }, aggregation_default


def compute_subscores(metric_scores: dict[str, Any], constants: dict[str, Any]) -> dict[str, Any]:
    systems_cfg, aggregation_default = _resolve_subscore_config(constants)

    subscores: dict[str, float | None] = {}
    missing_metrics: list[str] = []

    for system_name, system_cfg_raw in systems_cfg.items():
        system_cfg = system_cfg_raw if isinstance(system_cfg_raw, dict) else {}
        components_raw = system_cfg.get("components", [])
        if isinstance(components_raw, str):
            components = [part.strip() for part in components_raw.split(",") if part.strip()]
        else:
            components = list(components_raw)
        aggregation = str(system_cfg.get("aggregation", aggregation_default))

        present_values: list[float] = []
        for component in components:
            value = metric_scores.get(component)
            if value is None:
                if component not in missing_metrics:
                    missing_metrics.append(component)
                continue
            present_values.append(float(value))

        if aggregation != "mean":
            raise ValueError(f"Unsupported subscore aggregation: {aggregation}")

        subscores[str(system_name)] = _mean(present_values)

    return {"subscores": subscores, "missing_metrics": missing_metrics}


def _resolve_system_weights(constants: dict[str, Any]) -> dict[str, float]:
    model_cfg = constants.get("model", {})
    total_cfg = model_cfg.get("total_risk", {}) if isinstance(model_cfg, dict) else {}
    system_weights = total_cfg.get("system_weights") if isinstance(total_cfg, dict) else None
    if isinstance(system_weights, dict) and system_weights:
        return {k: float(v) for k, v in system_weights.items()}

    legacy = constants.get("weights", {}).get("systems", {})
    if not isinstance(legacy, dict) or not legacy:
        raise ValueError("No system weights found in constants")

    return {
        "cardio": float(legacy["cardiovascular"]),
        "metabolic": float(legacy["metabolic"]),
        "lifestyle": float(legacy["lifestyle"]),
        "recovery": float(legacy["recovery"]),
    }


def compute_total_risk(subscores: dict[str, float | None], missing_metrics: list[str], constants: dict[str, Any]) -> dict[str, Any]:
    del missing_metrics  # Missing metrics are already reflected in subscores availability.

    configured_weights = _resolve_system_weights(constants)
    available = {name: score for name, score in subscores.items() if score is not None and name in configured_weights}

    if not available:
        return {"total_risk": 0.0, "weights_used": {}}

    weight_sum = sum(configured_weights[name] for name in available)
    if weight_sum <= 0:
        raise ValueError("System weights must sum to a positive value")

    weights_used = {name: configured_weights[name] / weight_sum for name in available}
    total_risk = sum(float(available[name]) * weights_used[name] for name in available)
    total_risk = max(0.0, min(100.0, total_risk))

    return {"total_risk": total_risk, "weights_used": weights_used}


def _resolve_age_delta_config(constants: dict[str, Any]) -> tuple[float, float, float, float, float]:
    model_cfg = constants.get("model", {})
    age_cfg = model_cfg.get("age_delta", {}) if isinstance(model_cfg, dict) else {}

    linear_cfg = age_cfg.get("linear", {}) if isinstance(age_cfg, dict) else {}
    caps_cfg = age_cfg.get("caps", {}) if isinstance(age_cfg, dict) else {}

    if linear_cfg and caps_cfg:
        return (
            float(linear_cfg["pivot_risk"]),
            float(linear_cfg["pivot_delta_years"]),
            float(linear_cfg["slope_years_per_risk_point"]),
            float(caps_cfg["min_years"]),
            float(caps_cfg["max_years"]),
        )

    legacy = constants.get("age_delta", {})
    if not isinstance(legacy, dict):
        raise ValueError("Missing age_delta config")

    # Legacy path requires explicit pivot in constants if model.age_delta is not used.
    if "pivot_risk" not in legacy or "pivot_delta_years" not in legacy:
        raise ValueError("Legacy age_delta config requires pivot_risk and pivot_delta_years")
    pivot_risk = float(legacy["pivot_risk"])
    pivot_delta = float(legacy["pivot_delta_years"])
    slope = float(legacy["slope_years_per_risk_point"])
    return (pivot_risk, pivot_delta, slope, float(legacy["min_years"]), float(legacy["max_years"]))


def risk_to_age_delta(total_risk: float, constants: dict[str, Any]) -> dict[str, Any]:
    pivot_risk, pivot_delta_years, slope, min_years, max_years = _resolve_age_delta_config(constants)

    age_delta_uncapped = pivot_delta_years + ((float(total_risk) - pivot_risk) * slope)
    age_delta_years = max(min_years, min(max_years, age_delta_uncapped))
    return {
        "age_delta_years": age_delta_years,
        "age_delta_uncapped": age_delta_uncapped,
        "age_delta_capped": age_delta_years != age_delta_uncapped,
        "age_delta_caps": {"min": min_years, "max": max_years},
    }


def compute_biological_age(chronological_age_years: int, age_delta_years: float) -> float:
    return max(0.0, float(chronological_age_years) + float(age_delta_years))


def run_model(req: BioAgeRequest, constants: dict[str, Any] | None = None) -> dict[str, Any]:
    config = constants if constants is not None else load_constants()
    scored = score_request(req, config)
    metric_scores = scored["metric_scores"]

    subscore_result = compute_subscores(metric_scores, config)
    subscores = subscore_result["subscores"]
    missing_metrics = subscore_result["missing_metrics"]

    total_result = compute_total_risk(subscores, missing_metrics, config)
    delta_result = risk_to_age_delta(total_result["total_risk"], config)
    biological_age = compute_biological_age(req.demographics.chronological_age_years, delta_result["age_delta_years"])

    model_version = (
        req.model_version
        or str(config.get("model", {}).get("version") if isinstance(config.get("model", {}), dict) else "")
        or str(config.get("version", __version__))
    )

    return {
        "model_version": model_version,
        "inputs": {
            "chronological_age_years": req.demographics.chronological_age_years,
            "sex": req.demographics.sex.value,
        },
        "metric_scores": metric_scores,
        "subscores": subscores,
        "total_risk": total_result["total_risk"],
        "weights_used": total_result["weights_used"],
        "age_delta_years": delta_result["age_delta_years"],
        "age_delta_uncapped": delta_result["age_delta_uncapped"],
        "age_delta_capped": delta_result["age_delta_capped"],
        "age_delta_caps": delta_result["age_delta_caps"],
        "biological_age_years": biological_age,
        "missing_metrics": missing_metrics,
        "warnings": list(req.warnings),
        "guard_flags": flags_to_json(req.guard_flags),
    }
