"""Report retrieval routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings
from app.models.schemas import ReportListItem

router = APIRouter(tags=["reports"])


@router.get("/report/{report_id}/json")
def get_json(report_id: str):
    path = get_settings().reports_path / f"{report_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path, media_type="application/json", filename=f"report_{report_id}.json")


@router.get("/report/{report_id}/pdf")
def get_pdf(report_id: str):
    path = get_settings().reports_path / f"{report_id}.pdf"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path, media_type="application/pdf", filename=f"report_{report_id}.pdf")


@router.get("/reports", response_model=list[ReportListItem])
def list_reports() -> list[ReportListItem]:
    reports: list[ReportListItem] = []
    for path in sorted(get_settings().reports_path.glob("*.json"), reverse=True):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            reports.append(ReportListItem(
                report_id=data["report_id"],
                filename=data.get("filename", ""),
                generated_at=data.get("generated_at", ""),
                patient=data.get("metadata", {}).get("PatientName", "N/A"),
                modality=data.get("metadata", {}).get("Modality", "N/A"),
                num_slices=data.get("num_slices", 0),
                ai_provider=data.get("ai_provider", ""),
            ))
        except (json.JSONDecodeError, KeyError, OSError):
            continue
    return reports
