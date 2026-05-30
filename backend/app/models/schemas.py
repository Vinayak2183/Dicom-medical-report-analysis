"""Pydantic schemas for API requests and report payloads."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ConfidenceLevel = Literal["High", "Medium", "Low"]
QualityRating = Literal["Excellent", "Good", "Adequate", "Poor"]


class FindingItem(BaseModel):
    structure: str = ""
    description: str = ""
    confidence: ConfidenceLevel = "Medium"
    needs_radiologist_review: bool = False


class AIAnalysisReport(BaseModel):
    anatomy_observed: str = ""
    image_quality: str = ""
    image_quality_rating: QualityRating = "Adequate"
    findings: str = ""
    potential_abnormalities: list[FindingItem] = Field(default_factory=list)
    impression: str = ""
    recommendations: str = ""
    overall_confidence: ConfidenceLevel = "Medium"
    limitations: str = ""
    disclaimer: str = (
        "AI-generated for research and educational purposes only. "
        "Not a clinical diagnosis. Radiologist review is required."
    )

    def to_legacy_dict(self) -> dict[str, Any]:
        """Format compatible with existing frontend sections."""
        abnormalities_text = "\n".join(
            f"{i + 1}. {item.structure} — {item.description} "
            f"— Confidence: {item.confidence}"
            + (" — Needs radiologist review" if item.needs_radiologist_review else "")
            for i, item in enumerate(self.potential_abnormalities)
        )
        if not abnormalities_text:
            abnormalities_text = "No obvious abnormalities identified."

        return {
            "anatomy_observed": self.anatomy_observed,
            "image_quality": f"{self.image_quality_rating}: {self.image_quality}".strip(": "),
            "findings": self.findings,
            "potential_abnormalities": abnormalities_text,
            "impression": self.impression,
            "recommendations": self.recommendations,
            "overall_confidence": self.overall_confidence,
            "limitations": self.limitations,
            "disclaimer": self.disclaimer,
            "structured_abnormalities": [a.model_dump() for a in self.potential_abnormalities],
        }


class SeriesInfo(BaseModel):
    series_uid: str
    series_description: str = "N/A"
    series_number: str = "N/A"
    modality: str = "N/A"
    slice_count: int = 0
    is_scout: bool = False
    selected: bool = False


class AnalyzeSummary(BaseModel):
    patient: str = "N/A"
    modality: str = "N/A"
    study_date: str = "N/A"
    num_slices: int = 0
    series_count: int = 0
    selected_series: str = "N/A"
    impression: str = ""
    overall_confidence: str = "Medium"
    ai_provider: str = ""
    ai_models: list[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    report_id: str
    model: str
    ai_provider: str
    ai_models: list[str] = Field(default_factory=list)
    json_url: str
    pdf_url: str
    summary: AnalyzeSummary
    series_info: list[SeriesInfo] = Field(default_factory=list)


class ReportListItem(BaseModel):
    report_id: str
    filename: str
    generated_at: str
    patient: str = "N/A"
    modality: str = "N/A"
    num_slices: int = 0
    ai_provider: str = ""


class HealthResponse(BaseModel):
    status: str
    version: str
    ai_provider: str
    dr7_configured: bool
    gemini_configured: bool
