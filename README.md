# Biological Age Calculator

The Biological Age Calculator is an educational wellness estimation tool that converts self-reported health and lifestyle inputs into a deterministic **biological age estimate**. It is designed for coaching-style interpretation, not clinical diagnosis. The model combines blood pressure, arterial stiffness (optional PWV), body composition, lifestyle, and sleep indicators into a composite risk score, then maps that score to an age delta relative to chronological age.

Each run produces more than a single number: you get system subscores, top drivers, recommendation lists, and counterfactual simulations ("what could change if key risk factors improved"). The report package includes an HTML report and charts so results can be reviewed and shared as a static artifact.

All scoring thresholds, component weights, and explanatory copy are configuration-driven via `bioage/constants.yaml`. This keeps the pipeline reproducible and transparent for operator handoff. For every run, the system records provenance metadata such as constants hash and model version to support traceability.

This project is intentionally scoped as an educational estimator. It does **not** diagnose disease, predict lifespan, or replace medical evaluation.

## Disclaimer

> Educational guidance only. These results are not a diagnosis or treatment plan. Discuss personal decisions with a qualified healthcare professional.

---

## Quickstart

### 1) Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### 2) Run CLI demo

```bash
python -m bioage demo --outdir outputs/demo_run/
```

### 3) Run CLI with JSON input

```bash
python -m bioage run --input examples/input_minimal_bmi.json --outdir outputs/
```

If `--outdir` points to an existing directory, CLI creates `run_YYYYMMDD_HHMMSS` inside it.

### 4) Run Web UI (FastAPI)

```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/`.

### 5) View outputs

- CLI: in the run directory printed by command output.
- Web: under `outputs/web/` by default.
- Open `report.html` in a browser.
- Open `charts/*.png` directly for generated visuals.

---

## Input formats

Units:
- Blood pressure: `mmHg`
- Height: `cm`
- Weight: `kg`
- PWV: `m/s`
- Waist: `cm`

### A) BMI-only payload

```json
{
  "demographics": {"chronological_age_years": 45, "sex": "female"},
  "vitals": {"sbp_mmHg": 130, "dbp_mmHg": 85},
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

### B) Height + weight (derived BMI)

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

### C) With optional PWV

```json
{
  "demographics": {"chronological_age_years": 52, "sex": "female"},
  "vitals": {"sbp_mmHg": 138, "dbp_mmHg": 88, "pwv_m_per_s": 9.4},
  "anthropometrics": {"bmi": 29.1, "waist_cm": 96},
  "lifestyle": {
    "smoking_status": "former",
    "alcohol_use": "moderate",
    "drug_use": "none",
    "caffeine_use": "moderate"
  },
  "sleep": {"sleep_hours": 6.0, "sleep_quality": "fair", "sleep_consistency": "somewhat_regular"}
}
```

---

## Outputs and artifacts

Each successful run writes:

- `inputs_raw.json`
- `inputs_normalized.json` (includes normalized values + warnings + guard flags)
- `scores.json`
- `result.json`
- `explanations.json`
- `report.html`
- `charts/*.png`
- `run_meta.json` (includes `constants_hash`, `model_version`, `input_hash`, runtime metadata)
- `report.pdf` only when a PDF backend is implemented; currently optional and not emitted by default

---

## Configuration

`bioage/constants.yaml` is the single source of truth for:
- threshold bins and score points
- component/system weights
- age-delta mapping and caps
- disclaimer and report copy
- recommendation text and counterfactual labels/targets

Override constants:
- CLI: `--constants /path/to/constants.yaml`
- Web: set `BIOAGE_CONSTANTS_PATH=/path/to/constants.yaml`

Versioning/provenance:
- `result.json` includes `model_version`
- `run_meta.json` includes `constants_hash` (SHA-256) and `input_hash`

---

## Guardrails and reliability

- Unit mismatch heuristics generate warnings (for example, likely inches/lbs entry) but do not silently rewrite values.
- PWV is optional; missing PWV is flagged and handled without breaking run generation.
- BMI can be derived from height+weight; if a provided BMI conflicts, a warning is added and computed BMI is used.
- `total_risk` is clamped to `[0,100]`.
- Age delta is capped by configured min/max years.
- Biological age is clamped to `>= 0`.
- Outputs are deterministic for identical inputs/constants (stable JSON serialization and config-driven scoring).

---

## Deployment notes (MVP)

- Production-style launch example:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

- Current web UI is a no-auth MVP. For operational use, place behind VPN, internal reverse proxy, or authenticated access gateway.

---

## Verification

Run these checks after install:

```bash
pytest -q
python -m bioage demo --outdir outputs/demo_run/
python -m bioage run --input examples/input_minimal_bmi.json --outdir outputs/
uvicorn app.main:app --reload
```

Then visit `/` in a browser and submit the form.
