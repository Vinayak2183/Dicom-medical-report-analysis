"""DICOM windowing and image conversion."""

from __future__ import annotations

import io

import numpy as np
import pydicom
from PIL import Image


def apply_windowing(pixel_array: np.ndarray, ds: pydicom.Dataset) -> np.ndarray:
    arr = pixel_array.astype(float)
    slope = float(getattr(ds, "RescaleSlope", 1) or 1)
    intercept = float(getattr(ds, "RescaleIntercept", 0) or 0)
    arr = arr * slope + intercept

    wc = getattr(ds, "WindowCenter", None)
    ww = getattr(ds, "WindowWidth", None)
    if wc is not None and ww is not None:
        wc_val = float(wc[0]) if hasattr(wc, "__iter__") and not isinstance(wc, str) else float(wc)
        ww_val = float(ww[0]) if hasattr(ww, "__iter__") and not isinstance(ww, str) else float(ww)
        lo, hi = wc_val - ww_val / 2, wc_val + ww_val / 2
        arr = np.clip(arr, lo, hi)
        arr = (arr - lo) / ww_val * 255.0
    else:
        arr -= arr.min()
        if arr.max() > 0:
            arr = arr / arr.max() * 255.0

    return arr.astype(np.uint8)


def pixel_to_png_bytes(pixel_array: np.ndarray, ds: pydicom.Dataset) -> bytes:
    img_arr = apply_windowing(pixel_array, ds)
    pil_img = Image.fromarray(img_arr).convert("L")
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def extract_representative_slices(
    volume: np.ndarray,
    template_ds: pydicom.Dataset,
    n: int = 8,
) -> list[bytes]:
    if volume.ndim == 2:
        return [pixel_to_png_bytes(volume, template_ds)]

    total = volume.shape[0]
    count = min(n, total)
    indices = np.linspace(0, total - 1, count, dtype=int)
    return [pixel_to_png_bytes(volume[i], template_ds) for i in indices]
