"""DICOM analysis upload endpoint."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.exceptions import AIProviderError, DicomProcessingError
from app.models.schemas import AnalyzeResponse, AnalyzeSummary, SeriesInfo
from app.services.analysis.pipeline import AnalysisPipeline
from app.services.report.storage import save_report

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analysis"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_dicom(
    files: Annotated[list[UploadFile], File(description="DICOM files, folder contents, or .zip archive")],
):
    settings = get_settings()

    if not files:
        raise HTTPException(
            status_code=400,
            detail="No files uploaded. Send DICOM slices, a folder, or a .zip archive.",
        )

    if len(files) > settings.max_upload_files:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files ({len(files)}). Maximum is {settings.max_upload_files}.",
        )

    uploads: list[tuple[str, bytes]] = []
    total_bytes = 0
    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    for upload in files:
        name = upload.filename or "unknown"
        data = await upload.read()
        total_bytes += len(data)
        if total_bytes > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Upload exceeds {settings.max_upload_size_mb} MB limit.",
            )
        uploads.append((name, data))

    if len(uploads) == 1:
        source_label = uploads[0][0]
    elif len(uploads) <= 5:
        source_label = ", ".join(u[0] for u in uploads)
    else:
        source_label = f"{uploads[0][0]} + {len(uploads) - 1} more files"

    logger.info("Analyze request: %d file(s), %.1f MB", len(uploads), total_bytes / (1024 * 1024))

    try:
        result = AnalysisPipeline(settings).run(uploads, source_label)
        logger.info(
            "Analysis complete: report=%s slices=%d",
            result.report["report_id"],
            result.report.get("num_slices", 0),
        )
    except DicomProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    save_report(result.report, result.slice_pngs, result.hist_png, settings)

    report = result.report
    ai = report["ai_analysis"]
    summary = AnalyzeSummary(
        patient=report["metadata"].get("PatientName", "N/A"),
        modality=report["metadata"].get("Modality", "N/A"),
        study_date=report["metadata"].get("StudyDate", "N/A"),
        num_slices=report.get("num_slices", 0),
        series_count=report.get("series_count", 1),
        selected_series=report.get("selected_series_description", "N/A"),
        impression=ai.get("impression", ""),
        overall_confidence=ai.get("overall_confidence", "Medium"),
        ai_provider=report.get("ai_provider", ""),
        ai_models=report.get("ai_models", []),
    )

    response = AnalyzeResponse(
        report_id=report["report_id"],
        model=report.get("model", ""),
        ai_provider=report.get("ai_provider", ""),
        ai_models=report.get("ai_models", []),
        json_url=f"/report/{report['report_id']}/json",
        pdf_url=f"/report/{report['report_id']}/pdf",
        summary=summary,
        series_info=[SeriesInfo.model_validate(s) for s in report.get("series_info", [])],
    )
    return JSONResponse(response.model_dump())
