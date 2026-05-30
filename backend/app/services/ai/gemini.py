"""Google Gemini provider."""

from __future__ import annotations

import base64
import json
import re

import google.generativeai as genai

from app.config import Settings
from app.core.exceptions import AIProviderError
from app.models.schemas import AIAnalysisReport
from app.services.ai.prompts import build_refinement_prompt, build_vision_prompt


class GeminiProvider:
    def __init__(self, settings: Settings):
        if not settings.gemini_enabled:
            raise AIProviderError("GEMINI_API_KEY is not configured")
        genai.configure(api_key=settings.gemini_api_key)
        self.settings = settings

    def _model(self, name: str) -> genai.GenerativeModel:
        model_name = name if name.startswith("gemini") else self.settings.gemini_model
        return genai.GenerativeModel(
            model_name,
            generation_config={
                "temperature": 0.2,
                "response_mime_type": "application/json",
            },
        )

    @staticmethod
    def _parse_json(text: str) -> AIAnalysisReport:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            payload = json.loads(cleaned)
            return AIAnalysisReport.model_validate(payload)
        except (json.JSONDecodeError, ValueError) as exc:
            raise AIProviderError(f"Gemini returned invalid JSON: {exc}") from exc

    def analyze(
        self,
        png_slices: list[bytes],
        metadata: dict,
        stats_block: str,
        slice_count: int,
        series_desc: str,
        vision_model: str,
        refine_model: str,
    ) -> tuple[AIAnalysisReport, list[str]]:
        prompt = build_vision_prompt(metadata, stats_block, slice_count, series_desc)
        parts: list = [prompt]
        for png in png_slices:
            parts.append({"mime_type": "image/png", "data": base64.b64encode(png).decode()})

        try:
            response = self._model(vision_model).generate_content(parts)
            draft = self._parse_json(response.text)
        except Exception as exc:
            raise AIProviderError(f"Gemini vision analysis failed: {exc}") from exc

        models_used = [vision_model if vision_model.startswith("gemini") else self.settings.gemini_model]

        refine_name = refine_model if refine_model.startswith("gemini") else self.settings.gemini_refine_model
        refine_prompt = build_refinement_prompt(draft, metadata, stats_block)
        try:
            refined = self._model(refine_name).generate_content(refine_prompt)
            final = self._parse_json(refined.text)
            models_used.append(refine_name)
            return final, models_used
        except Exception:
            return draft, models_used
