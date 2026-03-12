# Biological Age Calculator — Client One-Pager

## What it does (in plain English)
The Biological Age Calculator gives an **educational estimate** of how a person’s health profile compares with typical aging patterns.

It takes key inputs (blood pressure, arterial stiffness/PWV if available, BMI, waist, smoking/alcohol/drug/caffeine use, and sleep), converts them into risk scores, combines them with fixed weights, and translates the result into an age difference.

**Formula:**
**Biological Age = Chronological Age + Age Delta**

---

## What it is based on
This is a **research-informed wellness model**, not a diagnosis.

It reflects widely accepted patterns such as:
- higher blood pressure and arterial stiffness are linked with higher cardiovascular risk,
- central fat (waist) adds risk information beyond BMI alone,
- smoking carries a larger health penalty than lower-impact lifestyle factors,
- sleep and recovery matter, but are weighted less than core cardiometabolic markers.

---

## How scoring works (quick view)
1. **Each input gets a score** (higher score = higher modeled risk).
2. Scores are grouped into systems:
   - **Cardio:** BP + PWV
   - **Metabolic:** BMI + waist
   - **Lifestyle:** smoking/alcohol/drug/caffeine
   - **Recovery:** sleep duration/quality/consistency
3. System weights are applied:
   - Cardio **36%**
   - Metabolic **30%**
   - Lifestyle **24%**
   - Recovery **10%**
4. Weighted total risk is converted to years using:
   - **Age delta = (total risk - 50) × 0.25**
   - capped to **-8 to +15 years**

---

## Which inputs move the result most?
In the current implementation, biggest movers are generally:
- **Blood pressure** (especially when PWV is missing),
- **PWV** (when available),
- **BMI and waist** (metabolic pair),
- **Smoking** (largest lifestyle driver).

Smaller movers include alcohol, drug use, caffeine, and sleep (sleep still matters but has lower top-level weight).

---

## Approximate impact ranges (current model)
> These are model-based estimates from the current code/config and can vary by full profile.

- **Blood pressure:** ~0 to **+4.1 years** (if PWV missing) or ~0 to **+2.0 years** (if PWV present)
- **PWV:** ~0 to **+1.7 years**
- **BMI:** ~0 to **+1.5 years**
- **Waist circumference:** ~0 to **+1.3 years** (male), ~0 to **+1.4 years** (female)
- **Smoking:** never → current about **+1.0 years**
- **Alcohol:** up to about **+0.30 years**
- **Drug use:** up to about **+0.34 years**
- **Caffeine:** low → high about **+0.08 years**
- **Sleep (combined):** up to about **+0.65 years**

---

## Improvement scenarios (“years recoverable”)
The tool can run built-in what-if scenarios and re-score the profile if someone improves:
- blood pressure,
- waist circumference,
- smoking status,
- sleep pattern.

It then reports estimated change in risk and biological-age delta, plus a combined “estimated years recoverable” figure.

---

## Important limitations
- Educational estimate only — **not** a clinical diagnosis or treatment plan.
- Uses only the inputs provided; output quality depends on input quality.
- If measurements look unreliable (for example, likely unit issues), some recommendations are suppressed until values are confirmed.
- Current constants are calibrated such that many profiles remain below the model pivot, so outputs may trend younger than chronological age.

---

## Bottom line
This product is best used for **wellness coaching conversations**: it translates health/lifestyle patterns into a transparent, easy-to-understand biological-age estimate, and shows where improvement is most likely to change the result.
