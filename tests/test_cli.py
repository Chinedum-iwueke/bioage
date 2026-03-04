from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_python_m_bioage_help() -> None:
    proc = subprocess.run([sys.executable, "-m", "bioage", "--help"], capture_output=True, text=True)
    assert proc.returncode == 0


def test_demo_creates_artifacts(tmp_path: Path) -> None:
    outdir = tmp_path / "demo"
    proc = subprocess.run([sys.executable, "-m", "bioage", "demo", "--outdir", str(outdir)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    for file in ["report.html", "inputs_normalized.json", "scores.json", "result.json", "explanations.json", "run_meta.json"]:
        assert (outdir / file).exists()


def test_run_from_json_creates_artifacts(tmp_path: Path) -> None:
    payload = {
        "demographics": {"chronological_age_years": 39, "sex": "male"},
        "vitals": {"sbp_mmHg": 122, "dbp_mmHg": 79, "pwv_m_per_s": 7.8},
        "anthropometrics": {"height_cm": 178, "weight_kg": 80, "waist_cm": 91},
        "lifestyle": {
            "smoking_status": "never",
            "alcohol_use": "light",
            "drug_use": "none",
            "caffeine_use": "low",
        },
        "sleep": {"sleep_hours": 7.2, "sleep_quality": "good", "sleep_consistency": "regular"},
    }
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    outdir = tmp_path / "run_dir"

    proc = subprocess.run(
        [sys.executable, "-m", "bioage", "run", "--input", str(input_path), "--outdir", str(outdir)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr

    for file in [
        "inputs_raw.json",
        "inputs_normalized.json",
        "scores.json",
        "result.json",
        "explanations.json",
        "report.html",
        "run_meta.json",
    ]:
        assert (outdir / file).exists()

    run_meta = json.loads((outdir / "run_meta.json").read_text(encoding="utf-8"))
    assert "constants_hash" in run_meta
    assert "input_hash" in run_meta
