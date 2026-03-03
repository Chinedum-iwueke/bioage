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
