from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_import_smoke() -> None:
    import bioage  # noqa: F401
    import bioage.cli  # noqa: F401
    import bioage.report.charts  # noqa: F401


def test_cli_help() -> None:
    proc = subprocess.run([sys.executable, "-m", "bioage", "--help"], capture_output=True, text=True)
    assert proc.returncode == 0
    assert "Biological Age Calculator" in proc.stdout


def test_demo_run_writes_expected_files(tmp_path: Path) -> None:
    outdir = tmp_path / "demo_run"
    proc = subprocess.run(
        [sys.executable, "-m", "bioage", "demo", "--outdir", str(outdir)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert (outdir / "report.html").exists()
    assert (outdir / "result.json").exists()
    assert (outdir / "styles.css").exists()
    assert (outdir / "inputs_normalized.json").exists()

    expected_charts = [
        "bio_age_bar.png",
        "arterial_stiffness_gauge.png",
        "bmi_gauge.png",
        "bp_sbp_gauge.png",
        "bp_dbp_gauge.png",
    ]
    for chart in expected_charts:
        assert (outdir / "charts" / chart).exists()
