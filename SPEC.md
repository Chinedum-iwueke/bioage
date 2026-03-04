# Biological Age Calculator — System Specification (Current Implementation)

## 1) Purpose and scope

The Biological Age Calculator is an **educational wellness estimation system**. It transforms user-provided cardiometabolic and lifestyle inputs into:

- metric-level risk scores
- system subscores
- composite risk (`total_risk`)
- age delta (`age_delta_years`)
- biological age estimate (`biological_age_years`)
- explanation bundle with recommendations and counterfactuals
- static report artifacts (HTML + chart images)

It is not a diagnostic or treatment system.

## 2) Interfaces

### 2.1 CLI

Entry point: `python -m bioage`

Commands:
- `demo --outdir <path> [--constants <path>] [--assets <path>] [--pdf]`
- `run --input <path.json> --outdir <path> [--constants <path>] [--assets <path>] [--pdf]`

Behavior notes:
- `run` creates a timestamped run folder when `--outdir` is an existing directory.
- `--pdf` currently raises `NotImplementedError` (PDF backend intentionally not configured).

### 2.2 Web UI (FastAPI)

Base app: `app.main:app`

Routes:
- `GET /` input form
- `POST /calculate` run pipeline from form data
- `GET /runs/{run_id}/report` view rendered HTML report
- `GET /runs/{run_id}/download/report.html`
- `GET /runs/{run_id}/download/report.pdf` (404 unless PDF exists)
- `GET /runs/{run_id}/charts` list run chart images
- `GET /health`

Web configuration:
- `BIOAGE_OUTPUT_DIR` (default `outputs/web`)
- `BIOAGE_CONSTANTS_PATH` (constants override)

## 3) Input schema

Top-level required objects:
- `demographics`
- `vitals`
- `anthropometrics`
- `lifestyle`
- `sleep`

Optional top-level fields:
- `client_metadata` (object)
- `measurement_metadata` (object)
- `submitted_at` (string)
- `model_version` (string)

### 3.1 Field definitions

- `demographics.chronological_age_years` integer, range `[10,120]`
- `demographics.sex` enum: `male | female`
- `vitals.sbp_mmHg` integer, range `[70,260]`
- `vitals.dbp_mmHg` integer, range `[40,160]`
- `vitals.pwv_m_per_s` optional float, range `[3.0,25.0]`
- `anthropometrics.waist_cm` required float, range `[20,200]`
- `anthropometrics.bmi` optional float, range `[12,70]`
- `anthropometrics.height_cm` optional float, range `[90,260]`
- `anthropometrics.weight_kg` optional float, range `[20,250]`
- `lifestyle.smoking_status` enum: `never | former | current`
- `lifestyle.alcohol_use` enum: `none | light | moderate | heavy`
- `lifestyle.drug_use` enum: `none | occasional | regular`
- `lifestyle.caffeine_use` enum: `none | low | moderate | high`
- `sleep.sleep_hours` float, range `[0,16]`
- `sleep.sleep_quality` enum: `poor | fair | good | excellent`
- `sleep.sleep_consistency` enum: `irregular | somewhat_regular | regular`

### 3.2 Derived BMI behavior

- User must provide either:
  - `bmi`, or
  - both `height_cm` and `weight_kg`.
- If `height_cm`+`weight_kg` are provided, BMI is computed.
- If computed BMI differs materially from provided BMI, a warning flag is emitted and computed BMI is used.

## 4) Validation and warnings

Validation is strict for schema shape, enums, and numeric ranges. Warnings/guard flags are generated for non-fatal concerns.

Guard flag format:
- `code`
- `severity` (`info` or `warning`)
- `message`
- optional `field`

Examples:
- missing optional PWV
- BMI mismatch between provided and computed
- near-boundary values
- unit plausibility warnings

Warnings are persisted in `inputs_normalized.json` and propagated to `result.json`.

## 5) Scoring method

Scoring is config-driven by `bioage/constants.yaml` thresholds and weights.

### 5.1 Metric scores

Primary metric scores are emitted in `scores.json` and mirrored in `result.json`:
- `bp`
- `pwv` (nullable)
- `bmi`
- `waist`
- `sleep`
- `lifestyle`

Each metric is transformed to a point score where higher is worse (0–100 style scale; exact bins from constants).

### 5.2 Subscores and missing-data handling

Configured subsystems (`model.subscores.systems`):
- `cardio` (`bp`, `pwv`)
- `metabolic` (`bmi`, `waist`)
- `lifestyle` (`lifestyle`)
- `recovery` (`sleep`)

Aggregation mode is mean (current implementation).

If a component is missing (e.g., PWV), the subsystem mean is computed from available components only. Missing component keys are recorded in `missing_metrics`.

### 5.3 Composite risk

System subscores are combined by normalized configured weights (`model.total_risk.system_weights`).

`total_risk` is clamped to `[0,100]`.

## 6) Risk-to-age mapping

Age delta mapping is linear and configuration-driven:
- `pivot_risk`
- `pivot_delta_years`
- `slope_years_per_risk_point`
- caps: `min_years`, `max_years`

Form:
`age_delta_uncapped = pivot_delta + (total_risk - pivot_risk) * slope`

`age_delta_years` is capped to configured min/max.

`biological_age_years = max(0, chronological_age_years + age_delta_years)`.

## 7) Explanation bundle

`explanations.json` includes:

- `disclaimer_short`
- `domain_summaries`
- `drivers`
  - metric-level contribution ranking
  - system contribution ranking
- `recommendations`
  - rule-based tips per metric label
  - prioritized action list
- `counterfactuals`
  - deterministic simulations for BP, waist, smoking, and sleep target improvements
  - `estimated_years_recoverable`

Counterfactual targets are read from constants and rescored through the same model pipeline.

## 8) Reporting

The report engine renders:

- `report.html`
- `charts/` PNG files
  - biological vs chronological age bar chart
  - arterial stiffness gauge (if PWV provided)
  - BMI gauge
  - SBP and DBP gauges

Report sections include cover/title, disclaimer, table of contents, biological age summary, blood pressure section, BMI and stiffness sections, recommendations, and appendices from templates.

## 9) Run artifacts

A successful run folder contains:
- `run_meta.json`
- `inputs_raw.json`
- `inputs_normalized.json`
- `scores.json`
- `result.json`
- `explanations.json`
- `report.html`
- `styles.css`
- `charts/*.png`
- optional `report.pdf` (not generated by current default implementation)

`run_meta.json` captures provenance:
- `run_id`
- timestamps
- `constants_hash`
- `model_version`
- `input_hash`
- runtime environment details

## 10) Determinism and reproducibility

Determinism is enforced by:
- fixed config-driven transforms
- stable JSON serialization (`sort_keys=True`, fixed formatting)
- explicit constants hashing
- versioned model output fields

Given the same normalized input and constants file, scoring and model results are deterministic.

## 11) Future improvements

- Optional PDF backend integration (e.g., WeasyPrint).
- Stronger constants loader compatibility with full YAML features.
- Authn/authz and hardened deployment posture for multi-user web operation.
- Outcome-linked calibration and external validation studies.
