"""CLI for deterministic Biological Age pipeline."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

from bioage.constants_loader import ConstantsValidationError
from bioage.pipeline import run_pipeline
from bioage.schema import SchemaValidationError

CLI_DISCLAIMER = "Educational wellness estimation only. Not a diagnosis, medical advice, or treatment plan."


def _demo_payload() -> dict:
    return {
        "demographics": {"chronological_age_years": 40, "sex": "male"},
        "vitals": {"sbp_mmHg": 128, "dbp_mmHg": 82, "pwv_m_per_s": 8.8},
        "anthropometrics": {"height_cm": 176, "weight_kg": 78, "waist_cm": 92},
        "lifestyle": {
            "smoking_status": "never",
            "alcohol_use": "light",
            "drug_use": "none",
            "caffeine_use": "moderate",
        },
        "sleep": {"sleep_hours": 7.5, "sleep_quality": "good", "sleep_consistency": "regular"},
        "client_metadata": {
            "prepared_for": "Demo Client",
            "consultant_id": "CONSULTANT-DEMO",
            "client_id": "CLIENT-DEMO",
            "security_key": "SEC-DEMO",
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bioage", description="Biological Age Calculator")
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run", help="Run pipeline from input JSON")
    run_parser.add_argument("--input", type=Path, required=True)
    run_parser.add_argument("--outdir", type=Path, required=True)
    run_parser.add_argument("--constants", type=Path, default=None)
    run_parser.add_argument("--assets", type=Path, default=None)
    run_parser.add_argument("--pdf", action="store_true")

    demo_parser = sub.add_parser("demo", help="Run pipeline using internal demo payload")
    demo_parser.add_argument("--outdir", type=Path, required=True)
    demo_parser.add_argument("--constants", type=Path, default=None)
    demo_parser.add_argument("--assets", type=Path, default=None)
    demo_parser.add_argument("--pdf", action="store_true")
    return parser


def _timestamped_run_dir(base: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return base / f"run_{ts}"


def _resolve_run_outdir(path: Path) -> Path:
    if path.exists() and path.is_dir():
        return _timestamped_run_dir(path)
    if str(path).endswith("/"):
        path.mkdir(parents=True, exist_ok=True)
        return _timestamped_run_dir(path)
    return path


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid input JSON: {exc}") from exc


def _run(payload: dict, outdir: Path, constants: Path | None, assets: Path | None, pdf: bool) -> int:
    run_pipeline(
        raw_input=payload,
        outdir=outdir,
        constants_path=constants,
        assets_path=assets,
        pdf=pdf,
        command_line=sys.argv,
    )
    print(CLI_DISCLAIMER)
    print(f"Artifacts written to: {outdir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "demo":
            return _run(_demo_payload(), args.outdir, args.constants, args.assets, args.pdf)
        if args.command == "run":
            outdir = _resolve_run_outdir(args.outdir)
            payload = _load_json(args.input)
            return _run(payload, outdir, args.constants, args.assets, args.pdf)
    except (SchemaValidationError, ValueError, FileNotFoundError, ConstantsValidationError, NotImplementedError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 0
