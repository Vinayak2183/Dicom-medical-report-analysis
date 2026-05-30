"""Radiology prompt templates."""

from __future__ import annotations

import json

from app.models.schemas import AIAnalysisReport


def build_vision_prompt(metadata: dict, stats_block: str, slice_count: int, series_desc: str) -> str:
    return f"""You are a board-certified radiologist producing a structured radiology report.

SCAN CONTEXT:
- Modality: {metadata.get('Modality', 'Unknown')}
- Body Part: {metadata.get('BodyPartExamined', 'Unknown')}
- Study Description: {metadata.get('StudyDescription', 'Unknown')}
- Series Description: {series_desc}
- Scanner: {metadata.get('Manufacturer', 'Unknown')} {metadata.get('ManufacturerModelName', '')}
- KVP: {metadata.get('KVP', 'Unknown')}
- Slice Thickness: {metadata.get('SliceThickness', 'Unknown')}
- Slices in series: {slice_count}
- Images provided: representative slices evenly sampled across the full volume

{stats_block}

INSTRUCTIONS:
- You are reviewing a FULL DICOM series via multiple representative slices, not a single image.
- Cross-reference visual findings with the HU statistics above.
- Be systematic: anatomy → quality → findings → abnormalities → impression → recommendations.
- Assign confidence (High/Medium/Low) to each potential abnormality.
- Set needs_radiologist_review=true for any uncertain or clinically significant finding.
- If no abnormality is seen, say so explicitly — do not invent pathology.
- State limitations if slice sampling may miss small lesions.

Respond with ONLY valid JSON matching this schema (no markdown fences):
{json.dumps(AIAnalysisReport.model_json_schema(), indent=2)}"""


def build_refinement_prompt(draft: AIAnalysisReport, metadata: dict, stats_block: str) -> str:
    return f"""You are a senior radiologist reviewing and refining an AI draft report.

Patient context:
- Modality: {metadata.get('Modality')}
- Body Part: {metadata.get('BodyPartExamined')}
- Study: {metadata.get('StudyDescription')}

{stats_block}

DRAFT REPORT JSON:
{draft.model_dump_json(indent=2)}

Tasks:
1. Correct any findings inconsistent with HU statistics.
2. Improve clinical language to formal radiology report standard.
3. Ensure impression summarizes only supported findings.
4. Adjust confidence levels conservatively — prefer Medium/Low when uncertain.
5. Add clear limitations if volume was subsampled.

Return ONLY valid JSON matching the same schema. No markdown."""
