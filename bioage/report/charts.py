"""Deterministic matplotlib chart builders for report rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _prepare(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _band_max(bands: list[dict[str, Any]]) -> float:
    return max(float(b["max"]) for b in bands)


def _safe_value(value: float, bands: list[dict[str, Any]]) -> float:
    low = float(min(b["min"] for b in bands))
    high = _band_max(bands)
    return max(low, min(float(value), high))


def plot_bioage_bar(chron_age: float, bio_age: float, outpath: Path) -> Path:
    import matplotlib.pyplot as plt

    _prepare(outpath)
    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    labels = ["Chronological Age", "Biological Age"]
    values = [float(chron_age), float(bio_age)]
    colors = ["#8ab4f8", "#2b6cb0"]
    bars = ax.bar(labels, values, color=colors, width=0.6)

    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.4, f"{value:.1f}", ha="center", va="bottom", fontsize=10)

    ax.set_ylabel("Years")
    ax.set_title("Age Comparison")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)
    return outpath


def plot_gauge(value: float, bands: list[dict], outpath: Path, title: str, subtitle: str | None = None) -> Path:
    import matplotlib.pyplot as plt

    _prepare(outpath)
    total_max = _band_max(bands)
    v = _safe_value(float(value), bands)

    fig, ax = plt.subplots(figsize=(6.4, 1.8))
    for band in bands:
        left = float(band["min"])
        width = float(band["max"]) - left
        ax.barh(0, width, left=left, height=0.48, color=str(band["color"]), edgecolor="white")

    ax.plot([v, v], [-0.45, 0.45], color="#1f2937", linewidth=2.4)
    ax.text(v, 0.6, f"{value:.1f}", ha="center", va="bottom", fontsize=10, color="#111827")

    ax.set_xlim(float(min(b["min"] for b in bands)), total_max)
    ax.set_ylim(-0.9, 1.0)
    ax.set_yticks([])
    ax.set_xlabel(subtitle or "")
    ax.set_title(title, fontsize=12, loc="left")

    tick_values = sorted({float(b["min"]) for b in bands} | {float(b["max"]) for b in bands})
    ax.set_xticks(tick_values)
    ax.grid(axis="x", linestyle=":", alpha=0.3)
    for spine in ax.spines.values():
        spine.set_visible(False)

    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)
    return outpath


def plot_bp_gauges(sbp: float, dbp: float, sbp_bands: list[dict], dbp_bands: list[dict], outdir: Path) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    sbp_path = outdir / "bp_sbp_gauge.png"
    dbp_path = outdir / "bp_dbp_gauge.png"
    plot_gauge(float(sbp), sbp_bands, sbp_path, title="Systolic Blood Pressure", subtitle="mmHg")
    plot_gauge(float(dbp), dbp_bands, dbp_path, title="Diastolic Blood Pressure", subtitle="mmHg")
    return {"sbp": sbp_path, "dbp": dbp_path}
