# Scientific Basis and Modeling Rationale

## Scope and interpretation

This document explains the scientific rationale behind `bioage/constants.yaml` and the current scoring model. The implementation is **research-informed** and intended for educational wellness estimation. It is not clinically validated for diagnosis, prognosis, or treatment selection.

Terminology used here:
- **risk score**: configuration-driven point score for a metric or subsystem
- **educational estimate**: modeled biological age output for coaching-style interpretation
- **associated with**: indicates observed population-level relationships, not deterministic individual outcomes

## How constants are used

The model is deterministic and constants-driven. Threshold bins, score values, and weights are loaded from:
- `thresholds.*`
- `weights.*`
- `model.*`
- `copy.*`
- `recommendations.*`

These values encode prior assumptions about directionality and relative influence.

---

## 1) `thresholds.blood_pressure` (SBP/DBP)

Blood pressure categories follow widely used clinical framing (normal, elevated, stage-based hypertension, crisis-level ranges). Higher categories are associated with higher cardiovascular risk and higher all-cause risk in many cohorts.

Rationale for scores:
- monotonic increase from normal to severe ranges
- larger penalties in higher bins to reflect non-linear risk escalation at extreme pressure values
- separate SBP and DBP binning retained because both carry signal across age groups

## 2) `thresholds.pwv`

Pulse wave velocity (PWV) is used as an arterial stiffness proxy. Higher stiffness is associated with vascular aging and adverse cardiovascular outcomes.

Rationale for scores:
- PWV is optional in this system to preserve usability when not measured
- provided PWV values are binned into increasing risk bands
- absence of PWV is handled as missing data, not as a default low-risk assumption

## 3) `thresholds.bmi` and `thresholds.waist_circumference`

BMI and waist circumference are both included to capture general and central adiposity.

Rationale:
- BMI supports broad body-mass categorization
- waist circumference adds abdominal adiposity context often associated with cardiometabolic risk beyond BMI alone
- sex-specific waist bands (`male`, `female`) reflect established differences in body-fat distribution risk interpretation

## 4) `thresholds.sleep_duration`, `thresholds.sleep_quality`, `thresholds.sleep_consistency`

Sleep risk is modeled as a recovery domain.

Rationale:
- sleep duration uses a U-shaped structure with lowest risk around typical mid-range duration
- very short and very long sleep carry higher penalties
- quality and consistency are included because fragmented or irregular sleep is associated with adverse cardiometabolic and behavioral patterns

## 5) `thresholds.smoking`, `thresholds.alcohol`, `thresholds.drug_use`, `thresholds.caffeine_use`

Lifestyle exposure bins convert category selections into risk points.

Rationale:
- current smoking receives high penalty due to strong and consistent adverse association signals
- alcohol and recreational drug-use bins are modeled as increasing risk gradients
- caffeine is treated as a smaller-effect modifier within lifestyle context

---

## 6) `weights.*` system and component weighting

### System weights (`weights.systems` and mirrored `model.total_risk.system_weights`)

Current weighting prioritizes:
1. cardiovascular
2. metabolic
3. lifestyle
4. recovery

Rationale:
- cardiovascular and metabolic markers are core cardiometabolic risk anchors
- lifestyle captures important modifiable behaviors
- recovery (sleep) is meaningful but weighted lower relative to dominant physiological domains

### Within-system components

Component weights reflect relative importance assumptions while preserving domain structure (for example, SBP/DBP/smoking contributions in cardiovascular and BMI/waist in metabolic).

These are design choices for an educational estimator and should be revisited if validated outcome-linked calibration data become available.

---

## 7) `model.age_delta` and caps

Composite risk is mapped to age delta using a linear rule:
- pivot risk and pivot delta set the reference point
- slope controls sensitivity in years per risk point
- caps (`min_years`, `max_years`) bound extreme outputs

Rationale for caps:
- prevents implausible age shifts for outlier combinations
- improves interpretability for coaching contexts
- limits over-extrapolation beyond confidence expected from a non-clinically calibrated model

---

## 8) Recommendations and counterfactuals

`recommendations.*` and `counterfactual_targets.*` drive deterministic explanation outputs:
- label-based recommendation tips
- scenario simulations (BP, waist, smoking, sleep) that show modeled changes in risk and age delta

These outputs are explanatory and educational. They are not prescriptions.

---

## 9) Validation status and responsible use

Current model status:
- deterministic and reproducible
- research-informed configuration
- not clinically validated for diagnostic or prognostic use

Appropriate use:
- wellness education
- trend-oriented coaching discussions
- hypothesis generation for lifestyle planning

Not appropriate use:
- diagnosis
- medication decisions
- emergency triage
- lifespan prediction claims
