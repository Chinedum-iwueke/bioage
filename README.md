# bioage

Biological Age Calculator (educational wellness estimation tool) with deterministic scoring/modeling, explanation generation, and HTML-first report output.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## CLI

```bash
python -m bioage --help
python -m bioage demo --outdir outputs/demo_run/
python -m bioage run --input examples/input.json --outdir outputs/
```

### Commands

- `bioage demo --outdir <path> [--pdf] [--constants <path>] [--assets <path>]`
- `bioage run --input <path.json> --outdir <path> [--pdf] [--constants <path>] [--assets <path>]`

If `bioage run` is given an existing directory (for example `outputs/`), it creates a UTC timestamped run folder: `run_YYYYMMDD_HHMMSS`.

## Input JSON examples

### BMI-only payload

```json
{
  "demographics": {"chronological_age_years": 45, "sex": "female"},
  "vitals": {"sbp_mmHg": 130, "dbp_mmHg": 85, "pwv_m_per_s": 9.1},
  "anthropometrics": {"bmi": 27.2, "waist_cm": 91},
  "lifestyle": {
    "smoking_status": "never",
    "alcohol_use": "light",
    "drug_use": "none",
    "caffeine_use": "moderate"
  },
  "sleep": {"sleep_hours": 7.0, "sleep_quality": "good", "sleep_consistency": "regular"}
}
```

### Height + weight payload

```json
{
  "demographics": {"chronological_age_years": 39, "sex": "male"},
  "vitals": {"sbp_mmHg": 122, "dbp_mmHg": 79},
  "anthropometrics": {"height_cm": 178, "weight_kg": 80, "waist_cm": 91},
  "lifestyle": {
    "smoking_status": "never",
    "alcohol_use": "light",
    "drug_use": "none",
    "caffeine_use": "low"
  },
  "sleep": {"sleep_hours": 7.2, "sleep_quality": "good", "sleep_consistency": "regular"}
}
```

## Output artifact layout

Each successful run writes:

- `inputs_raw.json`
- `inputs_normalized.json`
- `scores.json`
- `result.json`
- `explanations.json`
- `report.html`
- `charts/*.png`
- `run_meta.json` (contains `constants_hash`, `input_hash`, model/environment metadata)
- `report.pdf` only when a PDF backend is implemented (currently optional/stub)

## Constants override

Use `--constants <path/to/constants.yaml>` to load a different constants file. Hashing in `run_meta.json` is computed from the resolved constants file bytes to preserve run traceability.

## Notes

- Deterministic outputs: JSON is written with sorted keys and stable indentation.
- Disclaimers are embedded prominently in the report intro and footer.
- PDF export is intentionally optional; recommended future method is WeasyPrint (`report.html` → `report.pdf`).
