"""Placeholder chart builders modeled after the style in the sample guide."""

from __future__ import annotations

from pathlib import Path
import base64


COLORS = {
    "good": "#6fbf73",
    "moderate": "#f2c14e",
    "high": "#e76f51",
    "marker": "#1f2937",
}

_MINIMAL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9K6a0AAAAASUVORK5CYII="
)


def _prepare(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_fallback_png(path: Path) -> Path:
    _prepare(path)
    path.write_bytes(_MINIMAL_PNG)
    return path


def biological_age_bar(path: Path, actual_age: float, biological_age: float) -> Path:
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError:
        return _write_fallback_png(path)

    _prepare(path)
    fig, ax = plt.subplots(figsize=(8, 2.5))
    ax.barh(["Actual Age", "Biological Age"], [actual_age, biological_age], color=["#93c5fd", "#2563eb"])
    ax.set_xlabel("Years")
    ax.set_title("Age Comparison")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def vertical_gauge(path: Path, title: str, marker_value: float = 0.6) -> Path:
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError:
        return _write_fallback_png(path)

    _prepare(path)
    fig, ax = plt.subplots(figsize=(2.6, 5))
    ax.bar(0, 0.33, bottom=0.0, color=COLORS["good"], width=0.5)
    ax.bar(0, 0.33, bottom=0.33, color=COLORS["moderate"], width=0.5)
    ax.bar(0, 0.34, bottom=0.66, color=COLORS["high"], width=0.5)
    ax.axhline(marker_value, color=COLORS["marker"], linewidth=3)
    ax.set_xlim(-0.8, 0.8)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def blood_pressure_dual(path_sbp: Path, path_dbp: Path) -> tuple[Path, Path]:
    vertical_gauge(path_sbp, "SBP Gauge", marker_value=0.58)
    vertical_gauge(path_dbp, "DBP Gauge", marker_value=0.50)
    return path_sbp, path_dbp
