"""End-to-end deterministic pipeline orchestration."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bioage import __version__
from bioage.constants_loader import DEFAULT_CONSTANTS_PATH, load_constants
from bioage.explain import build_explanation_bundle
from bioage.model import run_model
from bioage.report.render import render_report_bundle
from bioage.schema import BioAgeRequest, normalize_request
from bioage.scoring import score_request


def _json_dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_pipeline(
    raw_input: dict,
    outdir: Path,
    constants_path: Path | None,
    assets_path: Path | None,
    pdf: bool,
    command_line: list[str] | None = None,
) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)

    constants_file = (constants_path or DEFAULT_CONSTANTS_PATH).expanduser().resolve()
    constants = load_constants(constants_file)

    req: BioAgeRequest = normalize_request(raw_input)
    scores = score_request(req, constants)
    result = run_model(req, constants)
    explanations = build_explanation_bundle(req, result, constants)

    _json_dump(outdir / "inputs_raw.json", raw_input)
    _json_dump(outdir / "inputs_normalized.json", req.to_dict())
    _json_dump(outdir / "scores.json", scores)
    _json_dump(outdir / "result.json", result)
    _json_dump(outdir / "explanations.json", explanations)

    report_bundle = render_report_bundle(outdir, req, result, explanations, constants)
    if pdf:
        raise NotImplementedError("--pdf requested but PDF backend is not configured. Recommended: WeasyPrint.")

    raw_json_stable = json.dumps(raw_input, sort_keys=True, separators=(",", ":")).encode("utf-8")
    run_meta = {
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "model_version": result.get("model_version"),
        "constants_hash": _hash_bytes(constants_file.read_bytes()),
        "input_hash": _hash_bytes(raw_json_stable),
        "command_line": command_line or [],
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "package_version": __version__,
            "executable": sys.executable,
        },
    }
    _json_dump(outdir / "run_meta.json", run_meta)

    return {
        "outdir": outdir,
        "report_html": report_bundle["report_html"],
        "charts": report_bundle["charts"],
        "report_pdf": report_bundle["report_pdf"],
        "biological_age": result["biological_age_years"],
        "age_delta": result["age_delta_years"],
    }
