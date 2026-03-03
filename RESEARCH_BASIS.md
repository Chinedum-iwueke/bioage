# Research Basis for Biological Age Risk Thresholds and Weightings

This document explains the research-informed rationale for values in `bioage/constants.yaml`.

## Design principles

1. **Public, non-proprietary evidence only**: thresholds and relative contributions are based on widely used clinical cut points and large cohort/meta-analytic patterns.
2. **Relative, not absolute, calibration**: scores represent proportional risk contributions (hazard burden) rather than direct probabilities.
3. **Monotonic risk scaling**: categories with stronger observed hazard ratios receive proportionally higher scores.
4. **Domain weighting by attributable impact**: domains with larger and more consistent all-cause/CVD risk associations receive higher system weights.

---

## 1) Blood pressure thresholds and scores

**Configuration:** `thresholds.blood_pressure`.

### Research rationale
- Cutoffs follow widely accepted guideline categories (normal, elevated, stage 1, stage 2, crisis) from ACC/AHA-aligned practice frameworks.
- Epidemiology consistently shows a graded rise in cardiovascular and all-cause mortality above ~120/80 mmHg, with materially higher risk once in stage 2 ranges.
- Therefore, score increments are small from normal → elevated, moderate at stage 1, and steep for stage 2/crisis.

### Score mapping logic
- SBP: `0 → 8 → 18 → 32 → 45`
- DBP: `0 → 16 → 30 → 45`

This ratio reflects that moving from elevated to stage 2 is not a linear worsening; mortality/CVD risk rises more steeply at higher BP strata.

---

## 2) BMI thresholds and scores

**Configuration:** `thresholds.bmi`.

### Research rationale
- Standard BMI categories (underweight, normal, overweight, obesity classes I–III) are globally used in risk stratification.
- Large pooled analyses show increased mortality at both low BMI (underweight/frailty disease burden) and high BMI, with progressively higher risk in higher obesity classes.
- Obesity is linked to major global mortality burden and reduced life expectancy at higher BMI ranges.

### Score mapping logic
- Underweight: `10` (non-zero due to elevated mortality risk in low BMI populations).
- Normal: `0`.
- Overweight: `10`.
- Obesity classes I/II/III: `20 / 30 / 40`.

Near-linear increments across obesity classes reflect stepwise hazard worsening.

---

## 3) Waist circumference thresholds and scores

**Configuration:** `thresholds.waist_circumference`.

### Research rationale
- Abdominal adiposity predicts cardiometabolic and mortality risk beyond BMI in many cohorts.
- Sex-specific risk gradients are established; example cohort findings show markedly higher mortality at high waist ranges (e.g., men >110 cm around ~1.5× vs <90 cm; women >95 cm around ~1.8× vs low-risk reference).
- This supports both sex-specific cutoffs and stronger upper-bin penalties, especially in women for equivalent high-risk categories where relative risk has often been reported as larger.

### Score mapping logic
- Men: `0 / 12 / 22 / 34`
- Women: `0 / 12 / 24 / 38`

Upper-bin spacing is larger than lower-bin spacing to match observed hazard acceleration at extreme central obesity.

---

## 4) Smoking thresholds and scores

**Configuration:** `thresholds.smoking`.

### Research rationale
- Smoking is among the strongest modifiable drivers of all-cause mortality and cardiovascular risk.
- Smoking is also associated with accelerated biological aging markers relative to never-smokers.
- Former smokers have persistent but reduced residual risk versus current smokers.

### Score mapping logic
- Never: `0`
- Former (>=12 months abstinent): `10`
- Occasional: `22`
- Daily: `38`

The daily-smoking value is intentionally high and exceeds moderate obesity or mild BP elevation bins, reflecting stronger and broad mortality impact.

---

## 5) Sleep duration thresholds and scores

**Configuration:** `thresholds.sleep_duration`.

### Research rationale
- Cohort literature supports a U-shaped association between sleep duration and mortality, with lowest risk around ~7–8 h/night.
- Short and very long sleep are both associated with elevated risk, increasing at extremes.

### Score mapping logic
- Optimal (7–8 h): `0`
- Mild deviation (6 or 9 h): `8`
- Moderate deviation (5 or 10 h): `16`
- Extreme deviation (<5 or >10 h): `26`

This preserves U-shape and assigns moderate (not dominant) influence relative to smoking/hypertension.

---

## 6) Physical activity and alcohol thresholds/scores

**Configuration:** `thresholds.physical_activity`, `thresholds.alcohol`.

### Research rationale
- Meeting guideline-level activity (>=150 min/week moderate-intensity equivalent) is associated with lower mortality than inactivity.
- Sedentary behavior and low activity increase all-cause risk in dose-response fashion.
- Heavy alcohol intake increases multiple-cause mortality risk; low-risk intake carries lower relative hazard.

### Score mapping logic
- Physical activity: `0 / 10 / 20 / 30` from guideline-meeting to none.
- Alcohol: `0 / 10 / 20` from low-risk to heavy.

Activity receives broader spread because dose-response and attributable burden are typically stronger than modest alcohol category differences in general-population tools.

---

## 7) System-level weights

**Configuration:** `weights.systems`.

- Cardiovascular: `0.36`
- Metabolic: `0.30`
- Lifestyle: `0.24`
- Recovery: `0.10`

### Research rationale
- **Cardiovascular (highest)**: BP and smoking have strong, reproducible associations with CVD and all-cause mortality.
- **Metabolic (second)**: adiposity (especially central obesity) substantially contributes to cardiometabolic and mortality burden.
- **Lifestyle (third)**: smoking/activity/alcohol are critical modifiable exposures; smoking is additionally represented as a major contributor within this domain.
- **Recovery (fourth)**: sleep contributes meaningful risk but with weaker/more confounded effect sizes than core BP/smoking exposures.

Weights are normalized to 1.00 and set to keep stronger evidence domains proportionately larger.

---

## 8) Within-system component weights

**Configuration:** `weights.*_components`.

### Cardiovascular components
- SBP `0.52`, DBP `0.33`, Smoking `0.15`
- Rationale: SBP is generally the stronger predictor across adult populations; DBP remains important; smoking also contributes to vascular risk.

### Metabolic components
- BMI `0.45`, Waist `0.55`
- Rationale: central adiposity often adds predictive value above BMI alone, so waist is weighted slightly higher.

### Lifestyle components
- Smoking `0.50`, Physical activity `0.30`, Alcohol `0.20`
- Rationale: smoking typically has the strongest hazard magnitude among these three; inactivity next; alcohol category effects are variable by pattern/context.

### Recovery
- Sleep duration `1.0`

---

## 9) Risk-to-age-delta mapping

**Configuration:** `age_delta`.

- `slope_years_per_risk_point: 0.25`
- `min_years: -8`
- `max_years: 15`

### Research rationale
- Biological age outputs should be interpretable and bounded.
- A quarter-year per aggregate risk point yields visible separation between low-, intermediate-, and high-risk profiles without generating implausible extremes in routine use.
- Caps prevent over-extrapolation beyond evidence density for very high composite scores.

---

## Notes on use and future calibration

- This configuration is **research-aligned prior structure**, not a final fitted model.
- If outcome-linked local data become available, re-calibrate point scales and slope with survival modeling while preserving directionality and clinical cut points.
- Re-validation should include discrimination (e.g., C-statistic), calibration plots, subgroup fairness checks, and sensitivity analyses.
