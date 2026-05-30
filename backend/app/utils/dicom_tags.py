"""DICOM tag extraction helpers."""

from __future__ import annotations

import pydicom


STANDARD_META_KEYS = [
    "PatientName", "PatientID", "PatientBirthDate", "PatientSex", "PatientAge", "PatientWeight",
    "StudyDate", "StudyTime", "StudyDescription", "AccessionNumber",
    "Modality", "BodyPartExamined", "SeriesDescription", "SeriesNumber",
    "Manufacturer", "ManufacturerModelName", "InstitutionName", "StationName",
    "Rows", "Columns", "PixelSpacing", "SliceThickness", "SliceLocation",
    "BitsAllocated", "BitsStored", "KVP", "WindowCenter", "WindowWidth",
    "RescaleSlope", "RescaleIntercept", "PhotometricInterpretation",
    "SOPClassUID", "SOPInstanceUID", "StudyInstanceUID", "SeriesInstanceUID",
    "InstanceNumber", "ImageType",
]


def safe_tag(ds: pydicom.Dataset, keyword: str, default: str = "N/A") -> str:
    try:
        val = getattr(ds, keyword, None)
        if val is None:
            return default
        if isinstance(val, pydicom.sequence.Sequence):
            return f"[Sequence: {len(val)} items]"
        s = str(val).strip()
        return s if s else default
    except Exception:
        return default


def extract_metadata(ds: pydicom.Dataset) -> dict[str, str]:
    return {k: safe_tag(ds, k) for k in STANDARD_META_KEYS}


def extract_all_tags(ds: pydicom.Dataset, limit: int = 200) -> dict[str, str]:
    tags: dict[str, str] = {}
    for elem in ds:
        if elem.keyword and elem.keyword != "PixelData":
            try:
                tags[elem.keyword] = str(elem.value)[:limit]
            except Exception:
                tags[elem.keyword] = "<unreadable>"
    return tags
