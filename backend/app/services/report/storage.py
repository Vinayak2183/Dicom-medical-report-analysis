"""Report persistence helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.services.report.pdf import build_pdf


def save_report(
    report: dict[str, Any],
    slice_pngs: list[bytes],
    hist_png: bytes | None,
    settings: Settings | None = None,
) -> tuple[Path, Path]:
    cfg = settings or get_settings()
    report_id = report["report_id"]
    json_path = cfg.reports_path / f"{report_id}.json"
    pdf_path = cfg.reports_path / f"{report_id}.pdf"

    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)

    build_pdf(report, slice_pngs, hist_png, str(pdf_path))
    return json_path, pdf_path
