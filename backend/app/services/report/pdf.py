"""PDF report generation."""

from __future__ import annotations

import os
import tempfile
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.analysis.pixel_stats import TISSUE_RANGES


def build_pdf(report: dict[str, Any], slice_pngs: list[bytes], hist_png: bytes | None, output_path: str) -> None:
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "Title", fontSize=20, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0f172a"), spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", fontSize=9, fontName="Helvetica",
        textColor=colors.HexColor("#64748b"), spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        "H2", fontSize=12, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1e40af"), spaceBefore=14, spaceAfter=6,
    )
    h3_style = ParagraphStyle(
        "H3", fontSize=10, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#374151"), spaceBefore=8, spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body", fontSize=8.5, fontName="Helvetica",
        textColor=colors.HexColor("#1f2937"), leading=13, spaceAfter=4,
    )
    disclaimer_style = ParagraphStyle(
        "Disc", fontSize=7.5, fontName="Helvetica-Oblique",
        textColor=colors.HexColor("#dc2626"),
        backColor=colors.HexColor("#fef2f2"),
        borderPadding=6, spaceAfter=8,
    )
    cell_style = ParagraphStyle(
        "Cell", fontSize=8, fontName="Helvetica",
        textColor=colors.HexColor("#1f2937"), leading=10,
    )
    cell_bold = ParagraphStyle(
        "CellB", fontSize=8, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0f172a"), leading=10,
    )

    table_style = TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eff6ff")),
        ("BACKGROUND", (1, 0), (1, -1), colors.white),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ])

    story: list = []
    meta = report["metadata"]
    ai = report["ai_analysis"]
    stats = report.get("pixel_stats", {})
    tissue = report.get("tissue_breakdown", {})
    tmp_imgs: list[str] = []

    story.append(Paragraph("DICOM AI Radiology Report", title_style))
    story.append(Paragraph(
        f"Generated: {report['generated_at']}  |  Provider: {report.get('ai_provider', 'N/A')}  "
        f"|  Model: {report.get('model', 'N/A')}  |  Source: {report['filename']}",
        subtitle_style,
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1e40af"), spaceAfter=12))

    story.append(Paragraph(
        "DISCLAIMER: AI-generated for research and educational purposes only. "
        "NOT a clinical diagnosis. Radiologist review is always required.",
        disclaimer_style,
    ))

    story.append(Paragraph("Patient & Study Information", h2_style))
    info_rows = [
        [Paragraph("Patient Name", cell_bold), Paragraph(meta.get("PatientName", "N/A"), cell_style),
         Paragraph("Modality", cell_bold), Paragraph(meta.get("Modality", "N/A"), cell_style)],
        [Paragraph("Patient ID", cell_bold), Paragraph(meta.get("PatientID", "N/A"), cell_style),
         Paragraph("Body Part", cell_bold), Paragraph(meta.get("BodyPartExamined", "N/A"), cell_style)],
        [Paragraph("Study Date", cell_bold), Paragraph(meta.get("StudyDate", "N/A"), cell_style),
         Paragraph("Series", cell_bold), Paragraph(report.get("selected_series_description", "N/A"), cell_style)],
        [Paragraph("Total Slices", cell_bold), Paragraph(str(report.get("num_slices", 0)), cell_style),
         Paragraph("Confidence", cell_bold), Paragraph(ai.get("overall_confidence", "Medium"), cell_style)],
    ]
    t = Table(info_rows, colWidths=[3.5 * cm, 5.5 * cm, 3.5 * cm, 5.5 * cm])
    t.setStyle(table_style)
    story.append(t)
    story.append(Spacer(1, 0.3 * cm))

    if report.get("series_info"):
        story.append(Paragraph("DICOM Series Detected", h2_style))
        series_rows = [["Description", "Modality", "Slices", "Type", "Used"]]
        for s in report["series_info"]:
            series_rows.append([
                s.get("series_description", "N/A")[:40],
                s.get("modality", "N/A"),
                str(s.get("slice_count", 0)),
                "Scout" if s.get("is_scout") else "Diagnostic",
                "Yes" if s.get("selected") else "No",
            ])
        st = Table(series_rows, colWidths=[6 * cm, 2.5 * cm, 2 * cm, 3 * cm, 2 * cm])
        st.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ]))
        story.append(st)

    story.append(PageBreak())
    story.append(Paragraph("Representative Slices", h2_style))

    if len(slice_pngs) == 1:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.write(slice_pngs[0])
        tmp.flush()
        tmp_imgs.append(tmp.name)
        story.append(RLImage(tmp.name, width=12 * cm, height=12 * cm, kind="proportional"))
    else:
        cols = 3
        for i in range(0, len(slice_pngs), cols):
            row_data = []
            for png in slice_pngs[i:i + cols]:
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                tmp.write(png)
                tmp.flush()
                tmp_imgs.append(tmp.name)
                row_data.append(RLImage(tmp.name, width=5.5 * cm, height=5.5 * cm, kind="proportional"))
            while len(row_data) < cols:
                row_data.append(Paragraph("", cell_style))
            story.append(Table([row_data], colWidths=[6 * cm] * cols))
            story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(
            f"Showing {len(slice_pngs)} representative slices from {report.get('num_slices', 0)} total.",
            body_style,
        ))

    story.append(PageBreak())
    story.append(Paragraph(f"AI Analysis — {report.get('model', 'N/A')}", h2_style))

    for key, label in [
        ("anatomy_observed", "Anatomy Observed"),
        ("image_quality", "Image Quality"),
        ("findings", "Findings"),
        ("potential_abnormalities", "Potential Abnormalities"),
        ("impression", "Impression"),
        ("recommendations", "Recommendations"),
        ("limitations", "Limitations"),
    ]:
        text = ai.get(key, "").strip()
        if text:
            story.append(Paragraph(label, h3_style))
            for line in text.splitlines():
                if line.strip():
                    story.append(Paragraph(line.strip(), body_style))
            story.append(Spacer(1, 0.15 * cm))

    structured = ai.get("structured_abnormalities") or []
    if structured:
        story.append(Paragraph("Structured Abnormality Table", h3_style))
        abn_rows = [["Structure", "Description", "Confidence", "Review?"]]
        for item in structured:
            abn_rows.append([
                item.get("structure", ""),
                item.get("description", "")[:80],
                item.get("confidence", ""),
                "Yes" if item.get("needs_radiologist_review") else "No",
            ])
        abn_table = Table(abn_rows, colWidths=[4 * cm, 7 * cm, 2.5 * cm, 2 * cm])
        abn_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ]))
        story.append(abn_table)

    story.append(PageBreak())
    story.append(Paragraph("Pixel & Hounsfield Unit Analysis", h2_style))

    if stats:
        stat_rows = [[
            Paragraph("Min HU", cell_bold), Paragraph(str(stats.get("min", "N/A")), cell_style),
            Paragraph("Max HU", cell_bold), Paragraph(str(stats.get("max", "N/A")), cell_style),
        ], [
            Paragraph("Mean HU", cell_bold), Paragraph(str(stats.get("mean", "N/A")), cell_style),
            Paragraph("Std Dev", cell_bold), Paragraph(str(stats.get("std", "N/A")), cell_style),
        ]]
        t3 = Table(stat_rows, colWidths=[3.5 * cm, 5.5 * cm, 3.5 * cm, 5.5 * cm])
        t3.setStyle(table_style)
        story.append(t3)

    if hist_png:
        tmp_hist = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp_hist.write(hist_png)
        tmp_hist.flush()
        tmp_imgs.append(tmp_hist.name)
        story.append(Spacer(1, 0.3 * cm))
        story.append(RLImage(tmp_hist.name, width=15 * cm, height=6 * cm))

    if tissue:
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Tissue Composition (% of voxels)", h3_style))
        tissue_rows = [["Tissue Type", "HU Range", "% Voxels"]]
        for t_name, pct in tissue.items():
            lo, hi = TISSUE_RANGES.get(t_name, (0, 0))
            tissue_rows.append([t_name, f"({lo}, {hi})", f"{pct}%"])
        tissue_table = Table(tissue_rows, colWidths=[5 * cm, 5 * cm, 5 * cm])
        tissue_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ]))
        story.append(tissue_table)

    doc.build(story)

    for path in tmp_imgs:
        try:
            os.unlink(path)
        except OSError:
            pass
