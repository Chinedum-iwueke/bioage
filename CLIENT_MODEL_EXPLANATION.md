# How the Biological Age Calculator Works (Client-Friendly Guide)

## 1) What this product does

This product estimates **biological age** from a short set of health and lifestyle inputs.

In simple terms, it does five things:
1. Reads your inputs (blood pressure, body measurements, smoking, sleep, etc.).
2. Compares each input to research-informed risk categories in the model settings.
3. Converts those categories into scores and combines them into one weighted risk score.
4. Converts that weighted risk score into an **age difference** (called age delta).
5. Adds that age delta to your actual age.

So the core equation is:

**Biological Age = Actual Age + Age Delta**

Example:
- If you are 45 and age delta is **-4**, biological age is **41**.
- If you are 45 and age delta is **+3**, biological age would be **48**.

(With the current constants in this repo, age delta is currently configured so outputs are generally younger than chronological age; more on that in limitations.)

---

## 2) What it is based on

The calculator is **research-informed** and designed as an **educational wellness estimate**, not a diagnosis.

The ideas behind it are straightforward:
- Higher blood pressure is widely linked to higher cardiovascular risk.
- Higher arterial stiffness (PWV) is linked to vascular aging.
- Body composition matters; waist size captures abdominal fat risk that BMI alone can miss.
- Smoking has a stronger modeled penalty than lower-impact habits like caffeine.
- Sleep duration, quality, and consistency matter for recovery, but are weighted less than core cardiometabolic signals.

So, the tool translates these known risk patterns into a practical coaching-style estimate.

---

## 3) How the scoring works in simple terms

### Step A: each input gets a metric score
Every metric is turned into a point score (higher = worse risk pattern).

Examples from current settings:
- BP category score ranges from **0 to 45**.
- PWV score ranges from **0 to 38** (if provided).
- BMI score ranges from **0 to 40**.
- Waist score ranges up to **34 (male)** or **38 (female)**.

### Step B: combined metric scores
Two composite metric scores are built from weighted components:
- **Lifestyle score** = smoking (45%) + alcohol (25%) + drug use (20%) + caffeine (10%).
- **Sleep score** = duration (50%) + quality (30%) + consistency (20%).

### Step C: system subscores
The model groups metrics into four systems:
- **Cardio** = mean of BP and PWV (if PWV is missing, BP alone is used).
- **Metabolic** = mean of BMI and waist.
- **Lifestyle** = lifestyle score.
- **Recovery** = sleep score.

### Step D: total risk weighting
System scores are weighted into total risk:
- Cardio: **36%**
- Metabolic: **30%**
- Lifestyle: **24%**
- Recovery: **10%**

### Step E: risk becomes years
The model maps risk to years with a linear rule:

**Age delta = (total risk - 50) x 0.25**, then capped to **-8 to +15 years**.

Finally:

**Biological age = chronological age + age delta**.

---

## 4) How each input affects the final age

Below are practical, code-derived impact ranges for each major input. These are approximate and depend on the full profile.

> Useful shortcut: each 1-point change in total risk changes age delta by **0.25 years**.

### Blood pressure
- **What it checks:** BP category (normal, elevated, stage 1/2, crisis).
- **Why it matters:** proxy for cardiovascular strain.
- **Practical effect in this model:**
  - BP score range is 0 to 45.
  - If PWV is missing (BP fully drives cardio): up to about **0 to 4.1 years**.
  - If PWV is present (BP is half of cardio): up to about **0 to 2.0 years**.
  - Typical jump, normal -> stage 1 (0 -> 18): about **+1.6 years** (no PWV) or **+0.8 years** (with PWV).

### Arterial stiffness (PWV)
- **What it checks:** PWV category from optimal to high.
- **Why it matters:** reflects arterial stiffness / vascular aging.
- **Practical effect in this model:**
  - PWV only affects output when provided.
  - PWV score range 0 to 38.
  - Because PWV is half of cardio when present, full range is about **0 to 1.7 years**.

### BMI
- **What it checks:** BMI category from normal to obesity classes.
- **Why it matters:** broad body-mass risk signal.
- **Practical effect in this model:**
  - BMI score range 0 to 40.
  - BMI is half of metabolic system, and metabolic is 30% of total.
  - Full range is about **0 to 1.5 years**.

### Waist circumference
- **What it checks:** sex-specific waist risk categories.
- **Why it matters:** central/abdominal fat risk signal.
- **Practical effect in this model:**
  - Male score range 0 to 34 (~**0 to 1.3 years**).
  - Female score range 0 to 38 (~**0 to 1.4 years**).
  - Same pathway strength as BMI (half of metabolic), but female upper category is slightly higher.

### Smoking
- **What it checks:** never / former / current.
- **Why it matters:** strong lifestyle risk factor.
- **Practical effect in this model:**
  - Smoking is 45% of lifestyle score.
  - Lifestyle is 24% of total risk.
  - Never -> current (0 -> 38 score) is about **+1.0 years**.
  - Former -> current (10 -> 38) is about **+0.76 years**.

### Alcohol
- **What it checks:** none / light / moderate / heavy.
- **Why it matters:** behavior risk gradient.
- **Practical effect in this model:**
  - Alcohol is 25% of lifestyle score.
  - Full none -> heavy span contributes about **0 to 0.30 years**.

### Drug use
- **What it checks:** none / occasional / regular.
- **Why it matters:** modeled lifestyle risk exposure.
- **Practical effect in this model:**
  - Drug use is 20% of lifestyle score.
  - Full none -> regular span contributes about **0 to 0.34 years**.

### Caffeine
- **What it checks:** none / low / moderate / high.
- **Why it matters:** lower-impact lifestyle modifier.
- **Practical effect in this model:**
  - Caffeine is 10% of lifestyle score.
  - Low -> high contributes about **+0.08 years**.
  - This is intentionally much smaller than smoking.

### Sleep (duration, quality, consistency)
- **What it checks:**
  - duration category,
  - quality level,
  - consistency pattern.
- **Why it matters:** recovery and daily restoration.
- **Practical effect in this model:**
  - Sleep score feeds recovery (10% system weight).
  - Combined worst-to-best sleep profile is about **0 to 0.65 years**.
  - Rough component maxima:
    - duration: ~**0.33 years**,
    - quality: ~**0.21 years**,
    - consistency: ~**0.12 years**.

---

## 5) Why some inputs matter more than others

Some factors have bigger effects because of two layers of weighting:
1. **Where they sit** (which system: cardio/metabolic/lifestyle/recovery), and
2. **How heavily they are weighted** within that system.

In plain terms:
- BP often matters more than sleep because cardio has a much larger system weight (36% vs 10%).
- Smoking matters more than caffeine because smoking gets a much larger share inside lifestyle (45% vs 10%).
- Waist and BMI are similar in strength because they share metabolic system influence.

So “importance” is mathematical, not subjective: it comes directly from the model constants.

---

## 6) Example walk-through (using current implementation)

### Example A: generally healthy profile
**Inputs (age 42, female):**
- BP 118/76, PWV 6.8
- BMI 23.5, waist 78 cm
- Never smoker, light alcohol, no drug use, low caffeine
- Sleep 7.4h, good quality, regular

**How model scores it:**
- Metric scores are very low overall (mostly 0, with very small lifestyle/sleep points).
- Cardio and metabolic are near zero; lifestyle and recovery are small.

**Result:**
- Total risk is very low (~0.44).
- Age delta hits the lower cap of **-8 years**.
- Biological age for age 42 becomes **~34**.

### Example B: elevated risk profile
**Inputs (age 42, male):**
- BP 146/94, PWV 11.2
- BMI 32.0, waist 108 cm
- Current smoker, heavy alcohol, occasional drug use, high caffeine
- Sleep 5h, poor quality, irregular

**How model scores it:**
- Higher BP and PWV raise cardio.
- BMI + waist raise metabolic.
- Smoking-heavy lifestyle pattern raises lifestyle.
- Poor sleep raises recovery score.

**Result:**
- Total risk ~27.24.
- Age delta ~**-5.69 years**.
- Biological age for age 42 becomes **~36.3**.

Note: even this elevated profile stays below the model’s risk pivot (50), so output remains younger than chronological age under current constants.

---

## 7) What happens when a person improves

The tool includes built-in “what-if” simulations (counterfactuals).

It can automatically simulate:
- BP moved to a normal representative value,
- waist moved to healthier sex-specific target,
- smoking improved one step (current->former, former->never),
- sleep moved to a target pattern (7.5h, good, regular).

For each scenario, it reruns the same model and reports:
- change in total risk,
- change in age delta,
- and a summed **estimated years recoverable** figure.

So improvement scenarios are not guesses—they are deterministic reruns of the same scoring logic with improved inputs.

---

## 8) Important limitations

- This is a **research-informed educational estimate**, not a clinical diagnosis.
- It is **not** a full medical assessment and should not guide medication or emergency decisions.
- It only uses the inputs currently included in the questionnaire.
- Output quality depends on input quality (for example, correct units).
- If measurements look suspicious (like likely unit errors), related recommendations can be suppressed and replaced with “confirm measurement” guidance.
- With the current constants, the model’s risk scale does not typically cross the pivot used for positive age deltas; this means outputs currently trend younger than chronological age. This is a calibration behavior, not a medical claim.

---

## 9) Appendix: simplified parameter impact table

| Parameter | What the tool checks | Why it matters | Relative strength | Approximate effect on biological age* |
|---|---|---|---|---|
| Blood pressure | BP category from SBP/DBP | Cardiovascular strain signal | High | ~0 to +4.1 years (if PWV missing) or ~0 to +2.0 years (if PWV present) |
| PWV (arterial stiffness) | PWV category | Vascular aging / stiffness proxy | Moderate-High | ~0 to +1.7 years |
| BMI | BMI category | General body-mass risk pattern | Moderate | ~0 to +1.5 years |
| Waist circumference | Sex-specific waist category | Central adiposity risk pattern | Moderate | Male: ~0 to +1.3 years; Female: ~0 to +1.4 years |
| Smoking | never/former/current | Strong behavior risk signal | High (within lifestyle) | Never->Current: ~+1.0 years |
| Alcohol | none/light/moderate/heavy | Lifestyle risk gradient | Low-Moderate | ~0 to +0.30 years |
| Drug use | none/occasional/regular | Lifestyle exposure risk | Low-Moderate | ~0 to +0.34 years |
| Caffeine | none/low/moderate/high | Smaller lifestyle modifier | Low | Low->High: ~+0.08 years |
| Sleep (combined) | Duration + quality + consistency | Recovery and restoration signal | Low-Moderate | Combined worst->best ~0 to +0.65 years |

\*Approximate effects are derived from current scoring constants, system weights, and linear risk-to-years mapping. Exact effect in a real case can vary based on other inputs and missing data handling.
