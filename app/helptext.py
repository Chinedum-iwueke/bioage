from __future__ import annotations

from bioage.schema import FIELD_LIMITS

FIELD_RANGES: dict[str, tuple[float, float]] = FIELD_LIMITS

FIELD_HELP: dict[str, dict[str, str | list[str]]] = {
    "client_name": {
        "label": "Client Name",
        "description": "Name shown on the generated report cover page.",
        "unit": "text",
        "examples": ["Jane Doe"],
    },
    "chronological_age_years": {
        "label": "Chronological Age",
        "description": "Current age in completed years.",
        "unit": "years",
        "range_key": "demographics.chronological_age_years",
        "examples": ["39", "52"],
    },
    "sex": {
        "label": "Sex",
        "description": "Biological sex used by the risk model.",
        "unit": "category",
        "examples": ["male", "female"],
    },
    "sbp_mmHg": {
        "label": "Systolic BP",
        "description": "Top blood pressure number measured at rest.",
        "unit": "mmHg",
        "range_key": "vitals.sbp_mmHg",
        "examples": ["118", "132"],
    },
    "dbp_mmHg": {
        "label": "Diastolic BP",
        "description": "Bottom blood pressure number measured at rest.",
        "unit": "mmHg",
        "range_key": "vitals.dbp_mmHg",
        "examples": ["76", "84"],
    },
    "pwv_m_per_s": {
        "label": "Pulse Wave Velocity",
        "description": "Arterial stiffness proxy from pulse wave speed (optional).",
        "unit": "m/s",
        "range_key": "vitals.pwv_m_per_s",
        "examples": ["7.1", "9.3"],
    },
    "height_cm": {
        "label": "Height",
        "description": "Body height (provide with weight if BMI omitted).",
        "unit": "cm",
        "range_key": "anthropometrics.height_cm",
        "examples": ["172", "181"],
    },
    "weight_kg": {
        "label": "Weight",
        "description": "Body weight (provide with height if BMI omitted).",
        "unit": "kg",
        "range_key": "anthropometrics.weight_kg",
        "examples": ["68", "84"],
    },
    "bmi": {
        "label": "BMI",
        "description": "Body mass index (optional when height+weight are provided).",
        "unit": "kg/m²",
        "range_key": "anthropometrics.bmi",
        "examples": ["22.4", "27.1"],
    },
    "waist_cm": {
        "label": "Waist Circumference",
        "description": "Waist measurement at the navel level.",
        "unit": "cm",
        "range_key": "anthropometrics.waist_cm",
        "examples": ["84", "96"],
    },
    "smoking_status": {
        "label": "Smoking",
        "description": "Current tobacco smoking category.",
        "unit": "category",
        "examples": ["never", "former"],
    },
    "alcohol_use": {
        "label": "Alcohol",
        "description": "Typical alcohol intake category.",
        "unit": "category",
        "examples": ["none", "moderate"],
    },
    "drug_use": {
        "label": "Drug Use",
        "description": "Non-prescribed recreational drug use frequency.",
        "unit": "category",
        "examples": ["none", "occasional"],
    },
    "caffeine_use": {
        "label": "Caffeine",
        "description": "Typical caffeine intake category.",
        "unit": "category",
        "examples": ["low", "moderate"],
    },
    "sleep_hours": {
        "label": "Sleep Hours",
        "description": "Average nightly sleep duration.",
        "unit": "hours/night",
        "range_key": "sleep.sleep_hours",
        "examples": ["6.8", "7.5"],
    },
    "sleep_quality": {
        "label": "Sleep Quality",
        "description": "Subjective quality of sleep most nights.",
        "unit": "category",
        "examples": ["fair", "good"],
    },
    "sleep_consistency": {
        "label": "Sleep Consistency",
        "description": "How regular your sleep/wake timing is.",
        "unit": "category",
        "examples": ["somewhat_regular", "regular"],
    },
}
