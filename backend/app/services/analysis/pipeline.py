"""End-to-end analysis orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np

from app.config import Settings, get_settings
from app.core.exceptions import AIProviderError
from app.models.schemas import AIAnalysisReport
from app.services.ai.dr7 import Dr7Provider
from app.services.ai.gemini import GeminiProvider
from app.services.ai.router import route_dr7, route_gemini
from app.services.analysis.pixel_stats import (
    compute_volume_stats,
    format_stats_for_prompt,
    make_histogram_png,
)
from app.services.dicom.ingest import ingest_uploads
from app.services.dicom.series import group_into_series, sample_series, select_primary_series
from app.services.dicom.windowing import pixel_to_png_bytes
from app.utils.dicom_tags import extract_all_tags, extract_metadata


@dataclass
class AnalysisResult:
    report: dict[str, Any]
    slice_pngs: list[bytes]
    hist_png: bytes | None
    ai_report: AIAnalysisReport


class AnalysisPipeline:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def _compute_stats_from_samples(self, stats_slices: list[tuple]) -> tuple[dict, dict, np.ndarray]:
        arrays = [arr for _ds, arr in stats_slices]
        if len(arrays) == 1:
            projection = arrays[0]
        else:
            projection = np.mean(np.stack(arrays, axis=0), axis=0)
        template_ds = stats_slices[0][0]
        return compute_volume_stats(projection, template_ds)

    def run(self, named_blobs: list[tuple[str, bytes]], source_label: str) -> AnalysisResult:
        uploads = ingest_uploads(named_blobs)
        all_series = group_into_series(uploads)
        primary = select_primary_series(all_series)
        sampled = sample_series(
            primary,
            n_display=self.settings.ai_slice_count,
            n_stats=min(32, max(8, self.settings.ai_slice_count * 2)),
        )

        metadata = extract_metadata(sampled.template_ds)
        all_tags = extract_all_tags(sampled.template_ds)

        pixel_stats, tissue_breakdown, hu_arr = self._compute_stats_from_samples(
            sampled.stats_slices
        )
        hist_png = make_histogram_png(hu_arr)

        slice_pngs = [
            pixel_to_png_bytes(arr, ds) for ds, arr in sampled.display_slices
        ]
        stats_block = format_stats_for_prompt(
            pixel_stats, tissue_breakdown, sampled.slice_count
        )

        provider_name = self.settings.resolve_provider()
        modality = metadata.get("Modality", "Unknown")
        route = route_dr7(modality) if provider_name == "dr7" else route_gemini(modality)

        try:
            if provider_name == "dr7":
                provider = Dr7Provider(self.settings)
            else:
                provider = GeminiProvider(self.settings)

            ai_report, models_used = provider.analyze(
                png_slices=slice_pngs,
                metadata=metadata,
                stats_block=stats_block,
                slice_count=sampled.slice_count,
                series_desc=primary.series_description,
                vision_model=route.vision_model,
                refine_model=route.refine_model,
            )
        except AIProviderError:
            if provider_name == "dr7" and self.settings.gemini_enabled:
                provider = GeminiProvider(self.settings)
                fallback = route_gemini(modality)
                ai_report, models_used = provider.analyze(
                    png_slices=slice_pngs,
                    metadata=metadata,
                    stats_block=stats_block,
                    slice_count=sampled.slice_count,
                    series_desc=primary.series_description,
                    vision_model=fallback.vision_model,
                    refine_model=fallback.refine_model,
                )
                provider_name = "gemini"
                route = fallback
            else:
                raise

        ai_dict = ai_report.to_legacy_dict()
        ai_dict["raw"] = ai_report.model_dump()

        series_info = [
            s.info(selected=(s.series_uid == primary.series_uid)) for s in all_series
        ]

        report_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        report = {
            "report_id": report_id,
            "filename": source_label,
            "generated_at": datetime.now().isoformat(),
            "model": route.label,
            "ai_provider": provider_name,
            "ai_models": models_used,
            "metadata": metadata,
            "all_tags": all_tags,
            "pixel_stats": pixel_stats,
            "tissue_breakdown": tissue_breakdown,
            "ai_analysis": ai_dict,
            "has_pixel_data": True,
            "num_slices": sampled.slice_count,
            "series_count": len(all_series),
            "series_info": [s.model_dump() for s in series_info],
            "selected_series_uid": primary.series_uid,
            "selected_series_description": primary.series_description,
            "is_scout_series": primary.is_scout,
        }

        return AnalysisResult(
            report=report,
            slice_pngs=slice_pngs,
            hist_png=hist_png,
            ai_report=ai_report,
        )
