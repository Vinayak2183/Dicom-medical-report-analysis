"""Upload ingestion: single files, folders, zip archives, DICOMDIR."""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pydicom

from app.core.exceptions import DicomProcessingError

DICOM_EXTENSIONS = {".dcm", ".dicom", ".dic", ".ima"}
SKIP_NAMES = {
    "dicomdir", "autorun.inf", "desktop.ini", "thumbs.db",
}
SKIP_EXTENSIONS = {".exe", ".dll", ".config", ".inf", ".txt", ".html", ".htm", ".xml", ".json"}


def _should_skip(filename: str) -> bool:
    base = Path(filename).name.lower()
    if base in SKIP_NAMES:
        return True
    if Path(base).suffix.lower() in SKIP_EXTENSIONS:
        return True
    return False


def is_dicom_payload(filename: str, data: bytes) -> bool:
    if _should_skip(filename):
        return False
    name = filename.lower()
    if Path(name).suffix.lower() in DICOM_EXTENSIONS:
        return True
    if name.endswith(".dcm") or name.endswith(".dicom") or name.endswith(".dic"):
        return True
    if len(data) >= 132 and data[128:132] == b"DICM":
        return True
    try:
        pydicom.dcmread(io.BytesIO(data), stop_before_pixels=True, force=True)
        return True
    except Exception:
        return False


def read_metadata(data: bytes) -> pydicom.Dataset:
    """Parse headers only — avoids loading pixel data into memory."""
    return pydicom.dcmread(io.BytesIO(data), stop_before_pixels=True, force=True)


def read_full(data: bytes) -> pydicom.Dataset:
    return pydicom.dcmread(io.BytesIO(data), force=True)


@dataclass
class UploadedDicom:
    filename: str
    data: bytes
    _meta: pydicom.Dataset | None = field(default=None, repr=False, compare=False)

    @classmethod
    def from_bytes(cls, filename: str, data: bytes) -> UploadedDicom:
        if not is_dicom_payload(filename, data):
            raise DicomProcessingError(f"Not a DICOM file: {filename}")
        item = cls(filename=filename, data=data)
        item._meta = read_metadata(data)
        return item

    @property
    def dataset(self) -> pydicom.Dataset:
        if self._meta is None:
            self._meta = read_metadata(self.data)
        return self._meta

    def load_with_pixels(self) -> pydicom.Dataset:
        return read_full(self.data)


def expand_zip(data: bytes) -> list[tuple[str, bytes]]:
    files: list[tuple[str, bytes]] = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename.replace("\\", "/")
                base = Path(name).name
                if not base or base.lower() in SKIP_NAMES:
                    continue
                if base.lower() == "dicomdir":
                    continue
                payload = zf.read(info)
                if is_dicom_payload(base, payload):
                    files.append((base, payload))
    except zipfile.BadZipFile as exc:
        raise DicomProcessingError("Invalid zip archive") from exc
    return files


def ingest_uploads(named_blobs: list[tuple[str, bytes]]) -> list[UploadedDicom]:
    """Flatten uploads (files and/or zip) into parsed DICOM datasets."""
    expanded: list[tuple[str, bytes]] = []

    for filename, data in named_blobs:
        lower = filename.lower()
        if lower.endswith(".zip"):
            expanded.extend(expand_zip(data))
        elif is_dicom_payload(filename, data):
            expanded.append((Path(filename).name, data))

    if not expanded:
        raise DicomProcessingError(
            "No DICOM files found. Upload .dcm/.dic files, a folder of slices, or a .zip archive."
        )

    datasets: list[UploadedDicom] = []
    errors: list[str] = []
    for name, blob in expanded:
        try:
            datasets.append(UploadedDicom.from_bytes(name, blob))
        except DicomProcessingError as exc:
            errors.append(str(exc))

    if not datasets:
        detail = errors[0] if errors else "No readable DICOM instances"
        raise DicomProcessingError(detail)

    return datasets
