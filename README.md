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

- This project currently generates placeholder charts, report HTML, and result JSON.
- Educational use only: output includes disclaimers and is not a diagnosis or medical advice.
- `constants.yaml` and research basis will be added in Task 1.5.

## Inputs & Units

`bioage.schema.normalize_request(raw)` validates and normalizes questionnaire payloads into canonical fields used by downstream scoring/model code.

- Demographics: `chronological_age_years` (years), `sex` (`male`/`female`).
- Vitals: `sbp_mmHg`, `dbp_mmHg`, optional `pwv_m_per_s` (m/s).
- Anthropometrics: `waist_cm` required; provide either `bmi` or both `height_cm` + `weight_kg`.
- Lifestyle enums: smoking/alcohol/drug/caffeine usage are normalized case-insensitively.
- Sleep: `sleep_hours`, `sleep_quality`, `sleep_consistency`.

The normalizer computes BMI from height+weight when available, checks sanity ranges, and adds deterministic warnings for suspicious inputs (for example likely unit mismatches or missing optional PWV). It does **not** apply scoring logic or clinical risk thresholds.

