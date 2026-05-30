"""Model selection by modality and provider."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelRoute:
    vision_model: str
    refine_model: str
    label: str


XRAY_MODALITIES = {"CR", "DX", "XR", "RG", "PX"}
CT_MR_MODALITIES = {"CT", "MR", "MRI", "PT", "NM"}


def route_dr7(modality: str) -> ModelRoute:
    mod = (modality or "").upper()
    if mod in XRAY_MODALITIES:
        return ModelRoute("chexagent", "baichuan-m3", "Dr7 CheXagent + Baichuan-M3")
    if mod in CT_MR_MODALITIES:
        return ModelRoute("medgemma-27b-it", "baichuan-m3", "Dr7 MedGemma-27B + Baichuan-M3")
    return ModelRoute("llava-med", "medgemma-27b-it", "Dr7 LLaVA-Med + MedGemma-27B")


def route_gemini(modality: str) -> ModelRoute:
    _ = modality
    return ModelRoute("gemini-2.5-flash", "gemini-2.5-flash", "Gemini 2.5 Flash")
