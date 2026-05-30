"""Dr7.ai medical AI provider."""

from __future__ import annotations

import base64
import json
import re

import httpx

from app.config import Settings
from app.core.exceptions import AIProviderError
from app.models.schemas import AIAnalysisReport
from app.services.ai.prompts import build_refinement_prompt, build_vision_prompt


class Dr7Provider:
    def __init__(self, settings: Settings):
        if not settings.dr7_enabled:
            raise AIProviderError("DR7_API_KEY is not configured")
        self.settings = settings
        self.base_url = settings.dr7_base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.dr7_api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _parse_json(text: str) -> AIAnalysisReport:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return AIAnalysisReport.model_validate(json.loads(cleaned))
        except (json.JSONDecodeError, ValueError) as exc:
            raise AIProviderError(f"Dr7.ai returned invalid JSON: {exc}") from exc

    def _chat(self, model: str, messages: list[dict], max_tokens: int = 4096) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }
        url = f"{self.base_url}/medical/chat/completions"
        try:
            with httpx.Client(timeout=180.0) as client:
                resp = client.post(url, headers=self._headers(), json=payload)
                if resp.status_code >= 400:
                    raise AIProviderError(
                        f"Dr7.ai API error {resp.status_code}: {resp.text[:500]}"
                    )
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPError as exc:
            raise AIProviderError(f"Dr7.ai request failed: {exc}") from exc

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

        content: list[dict] = [{"type": "text", "text": prompt}]
        for png in png_slices:
            b64 = base64.b64encode(png).decode()
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            })

        messages = [{"role": "user", "content": content}]
        try:
            raw = self._chat(vision_model, messages)
            draft = self._parse_json(raw)
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderError(f"Dr7.ai vision analysis failed: {exc}") from exc

        models_used = [vision_model]
        refine_prompt = build_refinement_prompt(draft, metadata, stats_block)
        try:
            refined_raw = self._chat(
                refine_model,
                [{"role": "user", "content": refine_prompt}],
            )
            final = self._parse_json(refined_raw)
            models_used.append(refine_model)
            return final, models_used
        except Exception:
            return draft, models_used
