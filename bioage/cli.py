"""CLI for the Biological Age scaffolding package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from bioage.constants_loader import load_constants
from bioage.scoring import score_request
from bioage.schema import ClientMetadata, DemoResult, normalize_request
from bioage.report import charts
from bioage.report.render import TEMPLATES_DIR, render_report

CLI_DISCLAIMER = (
    "Educational wellness estimation only. Not a diagnosis, medical advice, or treatment plan."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bioage",
        description="Biological Age Calculator (Educational Wellness Estimation Tool)",
    )
    subparsers = parser.add_subparsers(dest="command")

    demo_parser = subparsers.add_parser("demo", help="Generate placeholder report artifacts")
    demo_parser.add_argument("--outdir", type=Path, required=True, help="Output directory for demo files")
    return parser


def run_demo(outdir: Path) -> int:
    outdir.mkdir(parents=True, exist_ok=True)
    charts_dir = outdir / "charts"

    client = ClientMetadata()
    result = DemoResult()

    normalized_inputs = normalize_request(
        {
            "demographics": {"chronological_age_years": 40, "sex": "male"},
            "vitals": {"sbp_mmHg": 128, "dbp_mmHg": 82},
            "anthropometrics": {"height_cm": 176, "weight_kg": 78, "waist_cm": 92},
            "lifestyle": {
                "smoking_status": "never",
                "alcohol_use": "light",
                "drug_use": "none",
                "caffeine_use": "moderate",
            },
            "sleep": {
                "sleep_hours": 7.5,
                "sleep_quality": "good",
                "sleep_consistency": "regular",
            },
            "client_metadata": {"source": "demo"},
            "measurement_metadata": {"self_reported": True},
        }
    )

    scores = score_request(normalized_inputs, load_constants())


    bio = charts.biological_age_bar(charts_dir / "bio_age_bar.png", result.actual_age, result.biological_age)
    stiff = charts.vertical_gauge(charts_dir / "arterial_stiffness_gauge.png", "Arterial Stiffness")
    bmi = charts.vertical_gauge(charts_dir / "bmi_gauge.png", "BMI")
    sbp, dbp = charts.blood_pressure_dual(charts_dir / "bp_sbp_gauge.png", charts_dir / "bp_dbp_gauge.png")

    context = {
        "client": client.to_dict(),
        "result": result.to_dict(),
        "charts": {
            "bio_age": str(bio.relative_to(outdir)),
            "arterial_stiffness": str(stiff.relative_to(outdir)),
            "bmi": str(bmi.relative_to(outdir)),
            "bp_sbp": str(sbp.relative_to(outdir)),
            "bp_dbp": str(dbp.relative_to(outdir)),
        },
    }

    render_report(context=context, output_html=outdir / "report.html")
    shutil.copy2(TEMPLATES_DIR / "styles.css", outdir / "styles.css")

    (outdir / "result.json").write_text(json.dumps(context, indent=2), encoding="utf-8")
    (outdir / "inputs_normalized.json").write_text(
        json.dumps(normalized_inputs.to_dict(), indent=2), encoding="utf-8"
    )
    (outdir / "scores.json").write_text(json.dumps(scores, indent=2), encoding="utf-8")

    print(CLI_DISCLAIMER)
    print(f"Demo report generated at: {outdir / 'report.html'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "demo":
        return run_demo(args.outdir)

    parser.print_help()
    print(f"\nDisclaimer: {CLI_DISCLAIMER}")
    return 0
