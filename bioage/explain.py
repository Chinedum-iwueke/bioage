"""Deterministic explanation utilities for model outputs."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from bioage.constants_loader import load_constants
from bioage.guards import GuardFlag
from bioage.model import run_model
from bioage.schema import BioAgeRequest, SmokingStatus
from bioage.scoring import metric_labels

_SYSTEM_COMPONENTS: dict[str, list[str]] = {
    "cardio": ["bp", "pwv"],
    "metabolic": ["bmi", "waist"],
    "lifestyle": ["lifestyle"],
    "recovery": ["sleep"],
}


def _stable_rank(items: list[dict[str, Any]], key: str = "contribution") -> list[dict[str, Any]]:
    return sorted(items, key=lambda row: (-float(row[key]), str(row.get("metric") or row.get("system") or "")))


def compute_contributions(result: dict[str, Any], constants: dict[str, Any]) -> dict[str, Any]:
    del constants
    subscores = result.get("subscores", {})
    weights_used = result.get("weights_used", {})
    metric_scores = result.get("metric_scores", {})

    system_contributions: list[dict[str, Any]] = []
    metric_drivers: list[dict[str, Any]] = []

    for system_name, weight in weights_used.items():
        subscore = subscores.get(system_name)
        if subscore is None:
            continue
        system_contribution = float(subscore) * float(weight)
        system_contributions.append({"system": system_name, "contribution": round(system_contribution, 4)})

        components = _SYSTEM_COMPONENTS.get(system_name, [])
        present_components: list[tuple[str, float]] = []
        for metric in components:
            metric_score = metric_scores.get(metric)
            if metric_score is None:
                continue
            present_components.append((metric, float(metric_score)))

        component_sum = sum(score for _, score in present_components)
        if component_sum <= 0:
            continue
        for metric, score in present_components:
            share = score / component_sum
            metric_drivers.append(
                {
                    "metric": metric,
                    "system": system_name,
                    "contribution": round(system_contribution * share, 4),
                }
            )

    return {
        "system_contributions": _stable_rank(system_contributions),
        "metric_drivers": _stable_rank(metric_drivers),
    }


def _recommendation_for(mapping: dict[str, Any], label: str) -> list[str]:
    entry = mapping.get(label)
    if not isinstance(entry, dict):
        return []
    tips = entry.get("tips", [])
    return [str(t) for t in tips]


_UNTRUSTED_CODES_BY_METRIC: dict[str, set[str]] = {
    "waist": {"UNIT_SUSPECT_WAIST_IN", "UNIT_SUSPECT_WAIST_HIGH"},
    "bp": {"BP_SBP_OUTLIER", "BP_DBP_OUTLIER"},
    "sleep_duration": {"SLEEP_HOURS_OUTLIER"},
}


def _trust_map(req: BioAgeRequest) -> tuple[dict[str, bool], list[dict[str, str]]]:
    trusted = {"waist": True, "bp": True, "sleep_duration": True}
    suppressed: list[dict[str, str]] = []
    flags_by_code = {flag.code: flag for flag in req.guard_flags if isinstance(flag, GuardFlag)}

    for metric, codes in _UNTRUSTED_CODES_BY_METRIC.items():
        for code in sorted(codes):
            if code in flags_by_code:
                trusted[metric] = False
                suppressed.append({"metric": metric, "reason": code.lower()})
                break

    return trusted, suppressed


def generate_recommendations(req: BioAgeRequest, metric_scores: dict[str, Any], constants: dict[str, Any]) -> dict[str, Any]:
    del metric_scores
    labels = metric_labels(req, constants)
    rec_cfg = constants.get("recommendations", {})
    trusted, suppressed = _trust_map(req)

    recommendations: dict[str, list[str]] = {
        "bp": _recommendation_for(rec_cfg.get("bp", {}), str(labels["bp"])),
        "waist": _recommendation_for(rec_cfg.get("waist", {}), str(labels["waist"])),
        "bmi": _recommendation_for(rec_cfg.get("bmi", {}), str(labels["bmi"])),
        "smoking": _recommendation_for(rec_cfg.get("smoking", {}), str(labels["smoking"])),
        "alcohol": _recommendation_for(rec_cfg.get("alcohol", {}), str(labels["alcohol"])),
        "drug_use": _recommendation_for(rec_cfg.get("drug_use", {}), str(labels["drug_use"])),
        "caffeine_use": _recommendation_for(rec_cfg.get("caffeine_use", {}), str(labels["caffeine_use"])),
        "sleep_duration": _recommendation_for(rec_cfg.get("sleep_duration", {}), str(labels["sleep_duration"])),
        "sleep_quality": _recommendation_for(rec_cfg.get("sleep_quality", {}), str(labels["sleep_quality"])),
        "sleep_consistency": _recommendation_for(
            rec_cfg.get("sleep_consistency", {}), str(labels["sleep_consistency"])
        ),
    }

    if not trusted["waist"]:
        recommendations["waist"] = ["Confirm waist measurement in cm before interpreting this metric."]
    if not trusted["bp"]:
        recommendations["bp"] = ["Confirm blood pressure values in mmHg before interpreting this metric."]

    actions: list[tuple[str, float]] = []
    if str(labels["smoking"]) == "current":
        actions.append(("Quit smoking", 1000.0))
    if trusted["waist"]:
        actions.append(("Reduce waist circumference", float(req.anthropometrics.waist_cm)))
    else:
        actions.append(("Confirm waist measurement in cm before interpreting this metric", 1.0))
    if trusted["bp"]:
        actions.append(("Improve blood pressure control", float(req.vitals.sbp_mmHg + req.vitals.dbp_mmHg)))
    priority_actions = [name for name, _ in sorted(actions, key=lambda x: (-x[1], x[0]))][:3]

    return {
        "recommendations": recommendations,
        "priority_actions": priority_actions,
        "trusted_for_recommendation": trusted,
        "suppressed_recommendations": suppressed,
    }


def _rescore(req: BioAgeRequest, constants: dict[str, Any]) -> dict[str, Any]:
    return run_model(req, constants)


def simulate_counterfactuals(req: BioAgeRequest, constants: dict[str, Any]) -> dict[str, Any]:
    current = _rescore(req, constants)
    current_age_delta = float(current["age_delta_years"])
    current_risk = float(current["total_risk"])

    cf_cfg = constants.get("counterfactual_targets", {})
    labels_cfg = constants.get("copy", {}).get("counterfactual_labels", {})

    counterfactuals: list[dict[str, Any]] = []

    bp_cfg = cf_cfg.get("bp", {})
    bp_req = replace(
        req,
        vitals=replace(
            req.vitals,
            sbp_mmHg=int(bp_cfg.get("representative_sbp", req.vitals.sbp_mmHg)),
            dbp_mmHg=int(bp_cfg.get("representative_dbp", req.vitals.dbp_mmHg)),
        ),
    )
    if bp_req.vitals.sbp_mmHg != req.vitals.sbp_mmHg or bp_req.vitals.dbp_mmHg != req.vitals.dbp_mmHg:
        bp_out = _rescore(bp_req, constants)
        counterfactuals.append(
            {
                "name": str(labels_cfg.get("bp", "If blood pressure moved into the normal range")),
                "age_delta_change": round(float(bp_out["age_delta_years"]) - current_age_delta, 4),
                "total_risk_change": round(float(bp_out["total_risk"]) - current_risk, 4),
            }
        )

    waist_cfg = cf_cfg.get("waist", {})
    representative_cm = waist_cfg.get("representative_cm_by_sex", {}).get(req.demographics.sex.value)
    if representative_cm is not None:
        waist_req = replace(req, anthropometrics=replace(req.anthropometrics, waist_cm=float(representative_cm)))
        if float(waist_req.anthropometrics.waist_cm) != float(req.anthropometrics.waist_cm):
            waist_out = _rescore(waist_req, constants)
            counterfactuals.append(
                {
                    "name": str(labels_cfg.get("waist", "If waist circumference moved to a healthier range")),
                    "age_delta_change": round(float(waist_out["age_delta_years"]) - current_age_delta, 4),
                    "total_risk_change": round(float(waist_out["total_risk"]) - current_risk, 4),
                }
            )

    transitions = cf_cfg.get("smoking", {}).get("transitions", {})
    current_smoking = req.lifestyle.smoking_status.value
    target_smoking = transitions.get(current_smoking)
    if isinstance(target_smoking, str):
        smoking_req = replace(
            req,
            lifestyle=replace(req.lifestyle, smoking_status=SmokingStatus(target_smoking)),
        )
        smoke_out = _rescore(smoking_req, constants)
        counterfactuals.append(
            {
                "name": str(labels_cfg.get("smoking", "If smoking status improved")),
                "age_delta_change": round(float(smoke_out["age_delta_years"]) - current_age_delta, 4),
                "total_risk_change": round(float(smoke_out["total_risk"]) - current_risk, 4),
            }
        )

    sleep_cfg = cf_cfg.get("sleep", {})
    sleep_req = replace(
        req,
        sleep=replace(
            req.sleep,
            sleep_hours=float(sleep_cfg.get("representative_hours", req.sleep.sleep_hours)),
            sleep_quality=str(sleep_cfg.get("target_quality", req.sleep.sleep_quality.value)),
            sleep_consistency=str(sleep_cfg.get("target_consistency", req.sleep.sleep_consistency.value)),
        ),
    )
    # sleep enums are str-enums; cast by constructor for safety
    sleep_req = replace(
        sleep_req,
        sleep=replace(
            sleep_req.sleep,
            sleep_quality=type(req.sleep.sleep_quality)(sleep_req.sleep.sleep_quality),
            sleep_consistency=type(req.sleep.sleep_consistency)(sleep_req.sleep.sleep_consistency),
        ),
    )
    if (
        sleep_req.sleep.sleep_hours != req.sleep.sleep_hours
        or sleep_req.sleep.sleep_quality != req.sleep.sleep_quality
        or sleep_req.sleep.sleep_consistency != req.sleep.sleep_consistency
    ):
        sleep_out = _rescore(sleep_req, constants)
        counterfactuals.append(
            {
                "name": str(labels_cfg.get("sleep", "If sleep duration and consistency moved into an optimal range")),
                "age_delta_change": round(float(sleep_out["age_delta_years"]) - current_age_delta, 4),
                "total_risk_change": round(float(sleep_out["total_risk"]) - current_risk, 4),
            }
        )

    counterfactuals = sorted(counterfactuals, key=lambda item: (item["age_delta_change"], item["name"]))
    estimated_years_recoverable = round(sum(-min(0.0, float(item["age_delta_change"])) for item in counterfactuals), 4)

    return {
        "counterfactuals": counterfactuals,
        "estimated_years_recoverable": estimated_years_recoverable,
    }


def build_explanation_bundle(req: BioAgeRequest, result: dict[str, Any], constants: dict[str, Any] | None = None) -> dict[str, Any]:
    config = constants if constants is not None else load_constants()
    return {
        "disclaimer_short": str(config.get("copy", {}).get("disclaimer_short", "Educational guidance only.")),
        "domain_summaries": dict(config.get("copy", {}).get("domain_summaries", {})),
        "drivers": compute_contributions(result, config),
        "recommendations": generate_recommendations(req, result.get("metric_scores", {}), config),
        "counterfactuals": simulate_counterfactuals(req, config),
    }
