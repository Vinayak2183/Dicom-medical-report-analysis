"""Group, classify, sort, and sample DICOM series without loading full volumes."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pydicom

from app.models.schemas import SeriesInfo
from app.services.dicom.ingest import UploadedDicom
from app.utils.dicom_tags import safe_tag


SCOUT_KEYWORDS = (
    "SCOUT", "LOCALIZER", "TOPO", "TOPOGRAM", "OVERVIEW",
    "SCANOGRAM", "PLAN", "SURVEY", "REFERENCE",
)


@dataclass
class DicomSeries:
    series_uid: str
    instances: list[UploadedDicom] = field(default_factory=list)
    datasets: list[pydicom.Dataset] = field(default_factory=list)
    is_scout: bool = False
    modality: str = "N/A"
    series_description: str = "N/A"
    series_number: str = "N/A"

    @property
    def slice_count(self) -> int:
        return len(self.instances)

    def info(self, selected: bool = False) -> SeriesInfo:
        return SeriesInfo(
            series_uid=self.series_uid,
            series_description=self.series_description,
            series_number=self.series_number,
            modality=self.modality,
            slice_count=self.slice_count,
            is_scout=self.is_scout,
            selected=selected,
        )


@dataclass
class SampledSeriesData:
    """Representative slices loaded for AI/stats — not the full volume."""

    slice_count: int
    template_ds: pydicom.Dataset
    display_slices: list[tuple[pydicom.Dataset, np.ndarray]]
    stats_slices: list[tuple[pydicom.Dataset, np.ndarray]]
    series: DicomSeries


def _instance_sort_key(ds: pydicom.Dataset) -> tuple[float, int, str]:
    loc = getattr(ds, "SliceLocation", None)
    loc_val = 0.0
    if loc is not None:
        try:
            loc_val = float(loc[0] if hasattr(loc, "__iter__") and not isinstance(loc, str) else loc)
        except (TypeError, ValueError):
            loc_val = 0.0

    inst = getattr(ds, "InstanceNumber", 0) or 0
    try:
        inst_val = int(inst)
    except (TypeError, ValueError):
        inst_val = 0

    sop = safe_tag(ds, "SOPInstanceUID", "")
    return (loc_val, inst_val, sop)


def _is_scout_series(datasets: list[pydicom.Dataset]) -> bool:
    if not datasets:
        return False

    sample = datasets[0]
    desc = safe_tag(sample, "SeriesDescription", "").upper()
    image_type = safe_tag(sample, "ImageType", "").upper()

    if any(kw in desc for kw in SCOUT_KEYWORDS):
        return True
    if "LOCALIZER" in image_type or "SCOUT" in image_type:
        return True

    if len(datasets) <= 3:
        rows = int(getattr(sample, "Rows", 0) or 0)
        cols = int(getattr(sample, "Columns", 0) or 0)
        if rows * cols > 512 * 512:
            return True

    return False


def _has_pixel_data(ds: pydicom.Dataset) -> bool:
    """Detect image instances from metadata or loaded datasets.

    group_into_series keeps header-only parses (stop_before_pixels=True), so
    PixelData is usually absent even when the file contains image pixels.
    """
    if "PixelData" in ds:
        return True
    rows = int(getattr(ds, "Rows", 0) or 0)
    cols = int(getattr(ds, "Columns", 0) or 0)
    if rows > 0 and cols > 0:
        return True
    sop = safe_tag(ds, "SOPClassUID", "")
    # Standard and enhanced image storage SOP classes (CT, MR, CR, US, etc.)
    if sop.startswith("1.2.840.10008.5.1.4.1.1."):
        return True
    return False


def group_into_series(uploads: list[UploadedDicom]) -> list[DicomSeries]:
    buckets: dict[str, list[UploadedDicom]] = {}
    for item in uploads:
        uid = safe_tag(item.dataset, "SeriesInstanceUID", item.filename)
        buckets.setdefault(uid, []).append(item)

    series_list: list[DicomSeries] = []
    for uid, items in buckets.items():
        sorted_items = sorted(items, key=lambda u: _instance_sort_key(u.dataset))
        datasets = [u.dataset for u in sorted_items]
        sample = datasets[0]
        series = DicomSeries(
            series_uid=uid,
            instances=sorted_items,
            datasets=datasets,
            is_scout=_is_scout_series(datasets),
            modality=safe_tag(sample, "Modality"),
            series_description=safe_tag(sample, "SeriesDescription"),
            series_number=safe_tag(sample, "SeriesNumber"),
        )
        series_list.append(series)

    series_list.sort(key=lambda s: (s.is_scout, -s.slice_count))
    return series_list


def select_primary_series(series_list: list[DicomSeries]) -> DicomSeries:
    if not series_list:
        raise ValueError("No DICOM series found")

    with_pixels = [s for s in series_list if any(_has_pixel_data(ds) for ds in s.datasets)]
    if not with_pixels:
        raise ValueError("No series with pixel data found")

    diagnostic = [s for s in with_pixels if not s.is_scout]
    candidates = diagnostic or with_pixels
    return max(candidates, key=lambda s: s.slice_count)


def sample_series(
    series: DicomSeries,
    n_display: int = 8,
    n_stats: int = 32,
) -> SampledSeriesData:
    """Load only evenly-spaced slices needed for AI and HU stats."""
    total = len(series.instances)
    if total == 0:
        raise ValueError(f"Series {series.series_uid} has no instances")

    display_idx = np.linspace(0, total - 1, min(n_display, total), dtype=int)
    stats_idx = np.linspace(0, total - 1, min(n_stats, total), dtype=int)
    unique_idx = sorted(set(display_idx.tolist()) | set(stats_idx.tolist()))

    loaded: dict[int, tuple[pydicom.Dataset, np.ndarray]] = {}
    for idx in unique_idx:
        instance = series.instances[idx]
        ds = instance.load_with_pixels()
        if not _has_pixel_data(ds):
            continue
        arr = ds.pixel_array
        if arr.ndim != 2:
            continue
        loaded[idx] = (ds, arr)

    if not loaded:
        raise ValueError(f"Series {series.series_uid} has no readable 2D pixel slices")

    template_ds = loaded[unique_idx[0]][0]
    display_slices = [loaded[i] for i in display_idx if i in loaded]
    stats_slices = [loaded[i] for i in stats_idx if i in loaded]

    if not display_slices:
        display_slices = list(loaded.values())[:1]

    return SampledSeriesData(
        slice_count=total,
        template_ds=template_ds,
        display_slices=display_slices,
        stats_slices=stats_slices or display_slices,
        series=series,
    )
