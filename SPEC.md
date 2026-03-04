# SPEC.md — Single Source of Truth

## 1. Purpose

The Biological Age Calculator is defined as an **Educational Wellness Estimation Tool**.

It is explicitly **not** a medical device, does not provide diagnosis, and must not be represented as clinical decision support.

For this system, biological age is operationally defined as:

> **“A relative physiological risk age derived from cardiometabolic and lifestyle markers.”**

This specification is the contractual blueprint for model behavior, report generation, and deterministic output structure prior to research-aligned calibration.

---

## 2. System Architecture Overview

The model pipeline is:

**Inputs → Validation → Metric Scores → System Subscores → Weighted Risk Score → Age Delta → Biological Age → Report → Recommendations**

### 2.1 Pipeline intent

- **Inputs:** Collect user-provided demographic, physiological, and behavioral data.
- **Validation:** Enforce schema, units, and acceptable range checks.
- **Metric Scores:** Convert each validated input into a normalized risk metric on a common scale.
- **System Subscores:** Aggregate related metrics into system-level risk subscores.
- **Weighted Risk Score:** Combine subscores using configurable system weights.
- **Age Delta:** Transform total risk into age offset relative to chronological age.
- **Biological Age:** Compute final estimate as chronological age adjusted by age delta.
- **Report:** Render deterministic narrative + visual output in fixed section order.
- **Recommendations:** Generate deterministic guidance from rule mappings.

### 2.2 ASCII architecture diagram

```text
+--------+     +------------+     +--------------+     +----------------+
| Inputs | --> | Validation | --> | Metric Scores| --> | System Scores  |
+--------+     +------------+     +--------------+     +----------------+
                                                          |
                                                          v
                                                   +----------------+
                                                   | Weighted Total |
                                                   |   Risk Score   |
                                                   +----------------+
                                                          |
                                                          v
                                                   +----------------+
                                                   |   Age Delta    |
                                                   +----------------+
                                                          |
                                                          v
                                                   +----------------+
                                                   | Biological Age |
                                                   +----------------+
                                                      /           \
                                                     v             v
                                             +--------------+ +------------------+
                                             | Report Build | | Recommendations |
                                             +--------------+ +------------------+
```

---

## 3. Input Variables (No Numbers Yet)

All incoming values must be validated against schema-defined data types, units, and acceptable ranges using constants placeholders.

### 3.1 Demographics

- **chronological_age**
  - Type: integer or decimal (schema-constrained)
  - Unit: years
  - Acceptable range: `AGE_MIN` to `AGE_MAX` in `constants.yaml`
- **sex**
  - Type: enumerated string
  - Allowed values placeholder: `SEX_ALLOWED_VALUES`

### 3.2 Cardiovascular

- **sbp** (systolic blood pressure)
  - Type: decimal
  - Unit: mmHg
  - Acceptable range placeholder: `SBP_MIN` to `SBP_MAX`
- **dbp** (diastolic blood pressure)
  - Type: decimal
  - Unit: mmHg
  - Acceptable range placeholder: `DBP_MIN` to `DBP_MAX`
- **pwv** (pulse wave velocity, optional)
  - Type: decimal or null
  - Unit: m/s
  - Acceptable range placeholder: `PWV_MIN` to `PWV_MAX`

### 3.3 Metabolic

- **height**
  - Type: decimal
  - Unit: cm (or normalized to canonical SI before scoring)
  - Acceptable range placeholder: `HEIGHT_MIN` to `HEIGHT_MAX`
- **weight**
  - Type: decimal
  - Unit: kg
  - Acceptable range placeholder: `WEIGHT_MIN` to `WEIGHT_MAX`
- **bmi** (derived)
  - Derived from height and weight in canonical formula path
  - Formula implementation location to be defined in code-level docs
  - Validation placeholder for derived value: `BMI_MIN` to `BMI_MAX`
- **waist_circumference**
  - Type: decimal or null
  - Unit: cm
  - Acceptable range placeholder: `WAIST_MIN` to `WAIST_MAX`

### 3.4 Lifestyle

- **smoking_status**
  - Type: categorical enum
  - Allowed states placeholder: `SMOKING_CATEGORY_MAP`
- **alcohol_use_frequency**
  - Type: categorical enum
  - Allowed states placeholder: `ALCOHOL_FREQUENCY_MAP`
- **drug_use_frequency**
  - Type: categorical enum
  - Allowed states placeholder: `DRUG_FREQUENCY_MAP`
- **caffeine_use**
  - Type: categorical enum or bounded ordinal
  - Allowed states placeholder: `CAFFEINE_USE_MAP`

### 3.5 Sleep

- **sleep_duration_avg**
  - Type: decimal
  - Unit: hours per night
  - Acceptable range placeholder: `SLEEP_DURATION_MIN` to `SLEEP_DURATION_MAX`
- **sleep_quality_self_rating**
  - Type: ordinal categorical
  - Scale placeholder: `SLEEP_QUALITY_SCALE`
- **sleep_consistency**
  - Type: categorical or bounded ordinal
  - Scale placeholder: `SLEEP_CONSISTENCY_SCALE`

---

## 4. Scoring Framework (Structure Only)

Each metric is transformed into a normalized risk score on a **0–100** scale:

- `0` = optimal observed risk state in model definition
- `100` = highest model-defined risk state

No final thresholds are specified in this document.

### 4.1 Required scoring constant placeholders

Examples of required placeholders (non-exhaustive):

- `BP_STAGE_NORMAL_SCORE = <to be defined in constants.yaml>`
- `BP_STAGE_ELEVATED_SCORE = <to be defined in constants.yaml>`
- `SBP_THRESHOLD_BANDS = <to be defined in constants.yaml>`
- `DBP_THRESHOLD_BANDS = <to be defined in constants.yaml>`
- `PWV_THRESHOLD_BANDS = <to be defined in constants.yaml>`
- `BMI_THRESHOLD_BANDS = <to be defined in constants.yaml>`
- `WAIST_THRESHOLD_BANDS = <to be defined in constants.yaml>`
- `SMOKING_RISK_MAP = <to be defined in constants.yaml>`
- `ALCOHOL_RISK_MAP = <to be defined in constants.yaml>`
- `DRUG_RISK_MAP = <to be defined in constants.yaml>`
- `CAFFEINE_RISK_MAP = <to be defined in constants.yaml>`
- `SLEEP_DURATION_RISK_MAP = <to be defined in constants.yaml>`
- `SLEEP_QUALITY_RISK_MAP = <to be defined in constants.yaml>`
- `SLEEP_CONSISTENCY_RISK_MAP = <to be defined in constants.yaml>`

### 4.2 Deferred to Task 1.5

Task 1.5 will define and freeze:

- Threshold bands
- Relative magnitudes of risk levels
- System-level weights
- Age delta conversion rules

---

## 5. System Subscores

System subscores are grouped as follows.

### 5.1 Cardiovascular system

Components:
- Blood pressure composite (SBP/DBP-derived BP score)
- PWV score (optional; excluded if missing)

### 5.2 Metabolic system

Components:
- BMI score
- Waist circumference score

### 5.3 Lifestyle system

Components:
- Smoking score
- Alcohol score
- Drug score
- Caffeine score

### 5.4 Recovery system

Components:
- Sleep composite score (derived from duration, quality, consistency)

### 5.5 Formula structure

Base structure per system:

```text
SystemScore = average(component_scores)
```

Missing component handling:
- Missing components are excluded from denominator.
- If a component is unavailable, system score is computed from present components only.
- If a full system has no usable components, system is marked unavailable and excluded from total-risk aggregation.
- Remaining system weights are renormalized proportionally.

---

## 6. Composite Risk Score

Composite score structure:

```text
TotalRiskScore =
  (Cardio * CARDIO_WEIGHT) +
  (Metabolic * METABOLIC_WEIGHT) +
  (Lifestyle * LIFESTYLE_WEIGHT) +
  (Recovery * RECOVERY_WEIGHT)
```

All weight constants are placeholders and will be defined in Task 1.5 in `constants.yaml`.

Weight renormalization must occur when one or more systems are unavailable.

---

## 7. Age Delta Mapping

Age delta is defined as a deterministic transformation from total risk:

```text
AgeDelta = f(TotalRiskScore)
```

Required structure:
- Linear mapping placeholder (e.g., slope/intercept representation)
- Minimum age-delta cap placeholder
- Maximum age-delta cap placeholder

Required statement:

> **“Age delta caps prevent unrealistic biological age swings.”**

All mapping constants are deferred to Task 1.5.

---

## 8. Biological Age Calculation

Final calculation structure:

```text
BiologicalAge = ChronologicalAge + AgeDelta
```

Output must preserve deterministic rounding/formatting behavior as defined in implementation standards.

---

## 9. Drivers & Recommendations Logic

### 9.1 Driver detection

The model must identify:
- Top contributing system
- Top contributing metric within that system

Contribution logic must be deterministic and reproducible.

### 9.2 Recommendation generation

Recommendations are generated from a deterministic rule table:

- `RECOMMENDATION_RULE_TABLE = <to be defined later>`
- Mapping keys: risk drivers and severity tier placeholders
- Mapping outputs: educational recommendation text blocks

### 9.3 Counterfactual roadmap note

Counterfactual simulation (example: “if BP normalized”) is explicitly out of scope for this stage and will be implemented in later tasks.

---

## 10. Reporting Structure (Aligned With Guide PDF)

Report output must mirror the guide ordering and presentation style represented by `assets/sample_report_guide.pdf` and the current report templates.

### 10.1 Required section order

1. Cover Page
   - Client metadata
   - Prepared for
   - Date
   - Consultant ID
2. Table of Contents
3. Introduction + Disclaimer
4. Biological Age Summary
5. Arterial Stiffness Section
6. BMI Section
7. Blood Pressure Section
8. Appendices
   - Arterial Stiffness Explained
   - Blood Pressure Explained
   - Lifestyle Notes
   - Further Testing

### 10.2 Disclaimer requirement

**All reports must include visible disclaimer on Introduction page and footer.**

### 10.3 Presentation consistency

- Section headings must be stable and deterministic.
- Narrative style must remain educational and non-diagnostic.
- Charts/visuals may evolve, but section order and disclaimer placement are fixed.

---

## 11. Missing Data Rules

The model must not crash on partial inputs. Missing data must be handled deterministically and surfaced in report warnings.

### 11.1 Missing PWV

- Cardiovascular score falls back to BP-only subscore.
- PWV-specific narrative replaced with “not provided” explanatory text.
- Warning flag emitted.

### 11.2 Missing waist circumference

- Metabolic score falls back to BMI-only subscore.
- Waist-related recommendation logic disabled.
- Warning flag emitted.

### 11.3 Missing sleep details

- If one sleep component missing, compute recovery score from available sleep components.
- If all sleep components missing, recovery system marked unavailable and excluded with weight renormalization.
- Warning flag emitted.

### 11.4 Partial lifestyle responses

- Available lifestyle components still scored.
- Missing lifestyle components excluded from lifestyle average.
- If all lifestyle components missing, lifestyle system marked unavailable and excluded with weight renormalization.
- Warning flag emitted.

### 11.5 Warning propagation

- Each missing-data event must produce structured warning codes in output payload.
- Report must render a human-readable “Data completeness notes” block.

---

## 12. Determinism & Versioning

- All thresholds, risk maps, and weights are stored in `constants.yaml`.
- Output must include a required model version string, e.g., `MODEL_VERSION`.
- Given identical inputs and identical constants version, outputs must be identical.
- Any constant changes require model version increment according to project release policy.

---

## 13. Future Institutional Upgrade Notes

This architecture is intentionally extensible for later institutional-grade evolution:

- Transition from rule-based scoring to data-driven regression or hybrid models
- Calibration against real cohort data
- Confidence interval generation
- Population shift/drift monitoring
- Device standardization and protocol controls for PWV acquisition

These upgrades must remain backward-compatible with report contract and deterministic baseline mode.

---

## Open Design Decisions Requiring Confirmation

The following implementation-level decisions remain intentionally open and should be confirmed during Task 1.5 or subsequent governance review:

- Canonical input unit policy for height and potential dual-unit intake normalization.
- Exact categorical vocabularies for lifestyle and sleep enum states.
- Final rule precedence when both system-level and metric-level recommendations are triggered.
- Output rounding precision policy for system scores, total risk score, age delta, and biological age.
- Warning code namespace and schema shape for downstream API/report interoperability.
