# bioage

Biological Age Calculator (Educational Wellness Estimation Tool) scaffolding for deterministic, config-driven reporting workflows, with placeholder scoring/model logic and an HTML-first report pipeline that mirrors the uploaded sample guide's structure.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Run CLI smoke command

```bash
python -m bioage --help
python -m bioage demo --outdir outputs/demo_run/
```

## Notes

- Scoring is deterministic and config-driven: score thresholds, bins, and weights are loaded from `bioage/constants.yaml`.
- The demo command writes `scores.json` with per-metric risk scores and missing-data notes.
- Educational use only: output includes disclaimers and is not a diagnosis or medical advice.
- Explanations are deterministic and derived from constants.yaml tables (drivers, recommendations, and domain interpretations).
- Counterfactuals are educational simulations, not medical predictions.
- `constants.yaml` and research basis will be added in Task 1.5.

## Inputs & Units

`bioage.schema.normalize_request(raw)` validates and normalizes questionnaire payloads into canonical fields used by downstream scoring/model code.

- Demographics: `chronological_age_years` (years), `sex` (`male`/`female`).
- Vitals: `sbp_mmHg`, `dbp_mmHg`, optional `pwv_m_per_s` (m/s).
- Anthropometrics: `waist_cm` required; provide either `bmi` or both `height_cm` + `weight_kg`.
- Lifestyle enums: smoking/alcohol/drug/caffeine usage are normalized case-insensitively.
- Sleep: `sleep_hours`, `sleep_quality`, `sleep_consistency`.

The normalizer computes BMI from height+weight when available, checks sanity ranges, and adds deterministic warnings for suspicious inputs (for example likely unit mismatches or missing optional PWV). It does **not** apply scoring logic or clinical risk thresholds.


## Adjusting scoring constants safely

1. Edit `bioage/constants.yaml` (do not hardcode thresholds in Python).
2. Run `pytest -q` to validate boundary behavior against the updated config.
3. Re-run `python -m bioage demo --outdir outputs/demo_run/` to regenerate normalized inputs and scores.


## Model pipeline

The Task 4 model pipeline is deterministic and config-driven:

- `score_request` computes per-metric risk scores (`bp`, `pwv`, `bmi`, `waist`, `sleep`, `lifestyle`).
- `run_model` aggregates those into system subscores (`cardio`, `metabolic`, `lifestyle`, `recovery`).
- Subscores are combined into a weighted total risk score (0–100), with weight renormalization if a full system is unavailable.
- Total risk is mapped to age delta (years) with configured linear mapping + caps, then converted to biological age.

All model weights, subscore component definitions, and age-delta mapping parameters live in `bioage/constants.yaml` (not hardcoded in Python).
