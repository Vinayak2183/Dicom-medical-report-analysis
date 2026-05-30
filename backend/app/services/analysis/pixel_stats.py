"""Hounsfield unit statistics and histogram generation."""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pydicom


TISSUE_RANGES: dict[str, tuple[int, int]] = {
    "Air": (-1000, -900),
    "Lung": (-900, -500),
    "Fat": (-500, -100),
    "Water/CSF": (-10, 10),
    "Soft Tissue": (10, 80),
    "Blood": (30, 70),
    "Bone": (300, 2000),
}


def to_hounsfield(pixel_array: np.ndarray, ds: pydicom.Dataset) -> np.ndarray:
    arr = pixel_array.astype(float)
    slope = float(getattr(ds, "RescaleSlope", 1) or 1)
    intercept = float(getattr(ds, "RescaleIntercept", 0) or 0)
    return arr * slope + intercept


def compute_volume_stats(volume: np.ndarray, ds: pydicom.Dataset) -> tuple[dict, dict, np.ndarray]:
    hu = to_hounsfield(volume, ds)
    stats = {
        "min": round(float(hu.min()), 1),
        "max": round(float(hu.max()), 1),
        "mean": round(float(hu.mean()), 1),
        "std": round(float(hu.std()), 1),
    }

    total_px = hu.size
    tissue_pct: dict[str, float] = {}
    for tissue, (lo, hi) in TISSUE_RANGES.items():
        count = int(np.sum((hu >= lo) & (hu < hi)))
        tissue_pct[tissue] = round(count / total_px * 100, 2)

    return stats, tissue_pct, hu


def make_histogram_png(hu_array: np.ndarray) -> bytes:
    fig, ax = plt.subplots(figsize=(6, 2.5))
    flat = hu_array.flatten()
    flat = flat[(flat > -1100) & (flat < 3000)]
    ax.hist(flat, bins=150, color="#2563eb", alpha=0.8, edgecolor="none")
    ax.set_xlabel("Hounsfield Units (HU)", fontsize=8)
    ax.set_ylabel("Voxel Count", fontsize=8)
    ax.set_title("HU Distribution", fontsize=9, fontweight="bold")
    ax.tick_params(labelsize=7)
    ax.spines[["top", "right"]].set_visible(False)

    bands = [
        (-1000, -500, "#bfdbfe", "Lung/Air"),
        (-500, -100, "#fef9c3", "Fat"),
        (10, 80, "#bbf7d0", "Soft Tissue"),
        (300, 2000, "#fecaca", "Bone"),
    ]
    for lo, hi, col, _label in bands:
        ax.axvspan(lo, hi, alpha=0.25, color=col)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="PNG", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def format_stats_for_prompt(stats: dict, tissue: dict, slice_count: int) -> str:
    tissue_lines = "\n".join(f"  - {name}: {pct}%" for name, pct in tissue.items())
    return f"""QUANTITATIVE PIXEL ANALYSIS (ground truth from DICOM pixels):
- Volume slices analyzed: {slice_count}
- HU min / max / mean / std: {stats.get('min')} / {stats.get('max')} / {stats.get('mean')} / {stats.get('std')}
- Tissue composition (% voxels):
{tissue_lines}
Use these measurements to support or qualify your visual findings. Flag contradictions explicitly."""
