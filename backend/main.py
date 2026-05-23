#!/usr/bin/env python3
"""
DICOM AI Report Generator — FastAPI Backend
Uses Gemini 2.5 Flash (free) to analyze medical images
and generates structured JSON + PDF reports.

Install:
    pip install fastapi uvicorn pydicom numpy matplotlib reportlab Pillow google-generativeai python-multipart
"""

import os, io, json, base64, tempfile, re
from datetime import datetime
from pathlib import Path

import numpy as np
import pydicom
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

# ReportLab
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, Image as RLImage, HRFlowable, PageBreak
)

# Gemini
import google.generativeai as genai

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
GEMINI_MODEL   = "gemini-2.5-flash"
genai.configure(api_key=GEMINI_API_KEY)
gemini = genai.GenerativeModel(GEMINI_MODEL)

OUTPUT_DIR = Path("reports")
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="DICOM AI Report API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_tag(ds, keyword, default="N/A"):
    try:
        val = getattr(ds, keyword, None)
        if val is None:
            return default
        if isinstance(val, pydicom.sequence.Sequence):
            return f"[Sequence: {len(val)} items]"
        s = str(val).strip()
        return s if s else default
    except Exception:
        return default


def apply_windowing(pixel_array, ds):
    """Apply DICOM window center/width for proper display."""
    arr = pixel_array.astype(float)

    # Apply rescale if present
    slope = float(getattr(ds, "RescaleSlope", 1) or 1)
    intercept = float(getattr(ds, "RescaleIntercept", 0) or 0)
    arr = arr * slope + intercept

    # Window
    wc = getattr(ds, "WindowCenter", None)
    ww = getattr(ds, "WindowWidth", None)
    if wc is not None and ww is not None:
        wc = float(wc[0]) if hasattr(wc, "__iter__") and not isinstance(wc, str) else float(wc)
        ww = float(ww[0]) if hasattr(ww, "__iter__") and not isinstance(ww, str) else float(ww)
        lo, hi = wc - ww / 2, wc + ww / 2
        arr = np.clip(arr, lo, hi)
        arr = (arr - lo) / (ww) * 255.0
    else:
        arr -= arr.min()
        if arr.max() > 0:
            arr = arr / arr.max() * 255.0

    return arr.astype(np.uint8)


def pixel_to_png_bytes(pixel_array, ds):
    """Convert DICOM pixel array to PNG bytes."""
    img_arr = apply_windowing(pixel_array, ds)
    pil_img = Image.fromarray(img_arr).convert("L")
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def extract_slices(pixel_array, ds, n=5):
    """Extract n representative slices from a volume."""
    if pixel_array.ndim == 2:
        return [pixel_to_png_bytes(pixel_array, ds)]
    total = pixel_array.shape[0]
    indices = np.linspace(0, total - 1, min(n, total), dtype=int)
    return [pixel_to_png_bytes(pixel_array[i], ds) for i in indices]


def compute_pixel_stats(pixel_array, ds):
    """Compute HU stats and tissue breakdown."""
    arr = pixel_array.astype(float)
    slope = float(getattr(ds, "RescaleSlope", 1) or 1)
    intercept = float(getattr(ds, "RescaleIntercept", 0) or 0)
    hu = arr * slope + intercept

    stats = {
        "min": round(float(hu.min()), 1),
        "max": round(float(hu.max()), 1),
        "mean": round(float(hu.mean()), 1),
        "std": round(float(hu.std()), 1),
    }

    tissue_ranges = {
        "Air": (-1000, -900),
        "Lung": (-900, -500),
        "Fat": (-500, -100),
        "Water/CSF": (-10, 10),
        "Soft Tissue": (10, 80),
        "Blood": (30, 70),
        "Bone": (300, 2000),
    }
    total_px = hu.size
    tissue_pct = {}
    for tissue, (lo, hi) in tissue_ranges.items():
        count = int(np.sum((hu >= lo) & (hu < hi)))
        tissue_pct[tissue] = round(count / total_px * 100, 2)

    return stats, tissue_pct, hu


def make_histogram_png(hu_array):
    """Generate HU histogram as PNG bytes."""
    fig, ax = plt.subplots(figsize=(6, 2.5))
    flat = hu_array.flatten()
    flat = flat[(flat > -1100) & (flat < 3000)]
    ax.hist(flat, bins=150, color="#2563eb", alpha=0.8, edgecolor="none")
    ax.set_xlabel("Hounsfield Units (HU)", fontsize=8)
    ax.set_ylabel("Voxel Count", fontsize=8)
    ax.set_title("HU Distribution", fontsize=9, fontweight="bold")
    ax.tick_params(labelsize=7)
    ax.spines[["top","right"]].set_visible(False)

    # Tissue bands
    bands = [(-1000,-500,"#bfdbfe","Lung/Air"),(-500,-100,"#fef9c3","Fat"),(10,80,"#bbf7d0","Soft Tissue"),(300,2000,"#fecaca","Bone")]
    for lo, hi, col, label in bands:
        ax.axvspan(lo, hi, alpha=0.25, color=col, label=label)

    ax.legend(fontsize=6, loc="upper right")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="PNG", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def analyze_with_gemini(png_bytes, metadata):
    """Send image to Gemini for structured AI analysis."""
    modality    = metadata.get("Modality", "Unknown")
    body_part   = metadata.get("BodyPartExamined", "Unknown")
    study_desc  = metadata.get("StudyDescription", "Unknown")
    manufacturer = metadata.get("Manufacturer", "Unknown")
    kvp         = metadata.get("KVP", "Unknown")
    slice_thick = metadata.get("SliceThickness", "Unknown")

    prompt = f"""You are a highly experienced radiologist. Analyze the medical image provided and produce a detailed, structured radiology report.

SCAN DETAILS:
- Modality: {modality}
- Body Part: {body_part}
- Study Description: {study_desc}
- Scanner: {manufacturer}
- KVP: {kvp}
- Slice Thickness: {slice_thick}

You MUST respond using EXACTLY these section headers, each on its own line, followed by your content.
Do NOT use markdown formatting like ** or ##. Do NOT skip any section.

1. ANATOMY OBSERVED
List every anatomical structure visible. Be specific — name each bone, organ, vessel, or soft tissue region you can identify. State the side (left/right) where applicable.

2. IMAGE QUALITY
Evaluate: technical adequacy, patient positioning, exposure/contrast, noise level, presence of artifacts, and overall diagnostic quality. Rate as: Excellent / Good / Adequate / Poor.

3. FINDINGS
Describe ALL findings systematically. For each finding state:
- Location (exact anatomical region, side)
- Size (dimensions if measurable)
- Density / Signal / Echogenicity
- Margins (well-defined, irregular, spiculated)
- Character (solid, cystic, calcified, etc.)
Include both normal and abnormal findings. If a structure appears normal, explicitly state it.

4. POTENTIAL ABNORMALITIES
List each potential abnormality as a separate numbered point:
1. [Structure] — [Description of abnormality] — [Confidence: High/Medium/Low]
If no abnormalities are identified, state: "No obvious abnormalities identified on this image."

5. IMPRESSION
Write 2–4 concise sentences summarising the most clinically significant findings. This should read like a formal radiology impression.

6. RECOMMENDATIONS
List specific actionable recommendations:
- Additional imaging views or sequences needed
- Follow-up imaging (with suggested timeframe)
- Clinical correlation points
- Urgent referral if indicated

IMPORTANT: This report is AI-generated for research and educational use only. Clinical correlation with patient history is always required."""

    img_part = {"mime_type": "image/png", "data": base64.b64encode(png_bytes).decode()}
    response  = gemini.generate_content([prompt, img_part])
    return response.text


def parse_ai_sections(ai_text):
    """Parse Gemini response into structured sections.
    Handles all common Gemini output formats:
      '1. ANATOMY OBSERVED', '## Anatomy Observed', '**FINDINGS**', 'FINDINGS:', etc.
    """
    sections = {
        "anatomy_observed": "",
        "image_quality": "",
        "findings": "",
        "potential_abnormalities": "",
        "impression": "",
        "recommendations": "",
    }

    # Map any keyword variant → section key
    keyword_map = {
        "ANATOMY": "anatomy_observed",
        "ANATOMY OBSERVED": "anatomy_observed",
        "IMAGE QUALITY": "image_quality",
        "QUALITY": "image_quality",
        "FINDINGS": "findings",
        "FINDING": "findings",
        "POTENTIAL ABNORMALITIES": "potential_abnormalities",
        "ABNORMALITIES": "potential_abnormalities",
        "ABNORMALITY": "potential_abnormalities",
        "IMPRESSION": "impression",
        "RECOMMENDATIONS": "recommendations",
        "RECOMMENDATION": "recommendations",
    }

    # Regex: optional markdown/numbering + keyword + optional colon
    # Matches: "1. ANATOMY OBSERVED", "## Findings", "**IMPRESSION**:", "FINDINGS:", etc.
    header_re = re.compile(
        r'^\s*(?:#{1,3}\s*|\*{1,2})?'       # optional ## or **
        r'(?:\d+[\.\)]\s*)?'                 # optional "1." or "1)"
        r'\*{0,2}'                           # optional closing **
        r'([A-Z][A-Z\s]{2,30}?)'            # the keyword (3–30 uppercase chars)
        r'\*{0,2}'                           # optional closing **
        r'\s*:?\s*$',                        # optional colon, end of line
        re.IGNORECASE
    )

    current_key = None
    lines = ai_text.splitlines()

    for line in lines:
        match = header_re.match(line)
        if match:
            candidate = match.group(1).strip().upper()
            # Find best matching key
            matched_key = None
            for keyword, key in keyword_map.items():
                if candidate == keyword or candidate.startswith(keyword):
                    matched_key = key
                    break
            if matched_key:
                current_key = matched_key
                continue  # don't add the header line as content

        if current_key:
            sections[current_key] += line + "\n"

    result = {k: v.strip() for k, v in sections.items()}

    # Fallback: if nothing parsed, dump everything into findings
    if not any(result.values()):
        result["findings"] = ai_text.strip()

    # Debug log — visible in your terminal
    print("\n=== GEMINI RAW RESPONSE (first 800 chars) ===")
    print(ai_text[:800])
    print("=== PARSED SECTIONS ===")
    for k, v in result.items():
        print(f"  {k}: {len(v)} chars")
    print("=" * 40)

    return result


# ── Build PDF ─────────────────────────────────────────────────────────────────

def build_pdf(report: dict, slice_pngs: list, hist_png: bytes, output_path: str):
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle("Title", fontSize=20, fontName="Helvetica-Bold",
                                  textColor=colors.HexColor("#0f172a"), spaceAfter=4)
    subtitle_style = ParagraphStyle("Subtitle", fontSize=9, fontName="Helvetica",
                                     textColor=colors.HexColor("#64748b"), spaceAfter=12)
    h2_style = ParagraphStyle("H2", fontSize=12, fontName="Helvetica-Bold",
                               textColor=colors.HexColor("#1e40af"), spaceBefore=14, spaceAfter=6)
    h3_style = ParagraphStyle("H3", fontSize=10, fontName="Helvetica-Bold",
                               textColor=colors.HexColor("#374151"), spaceBefore=8, spaceAfter=4)
    body_style = ParagraphStyle("Body", fontSize=8.5, fontName="Helvetica",
                                 textColor=colors.HexColor("#1f2937"), leading=13, spaceAfter=4)
    disclaimer_style = ParagraphStyle("Disc", fontSize=7.5, fontName="Helvetica-Oblique",
                                       textColor=colors.HexColor("#dc2626"),
                                       backColor=colors.HexColor("#fef2f2"),
                                       borderPadding=6, spaceAfter=8)
    cell_style = ParagraphStyle("Cell", fontSize=8, fontName="Helvetica",
                                 textColor=colors.HexColor("#1f2937"), leading=10)
    cell_bold = ParagraphStyle("CellB", fontSize=8, fontName="Helvetica-Bold",
                                textColor=colors.HexColor("#0f172a"), leading=10)

    table_style = TableStyle([
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#eff6ff")),
        ("BACKGROUND", (1,0), (1,-1), colors.white),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.HexColor("#f8fafc"), colors.white]),
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 7),
        ("RIGHTPADDING", (0,0), (-1,-1), 7),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ])

    story = []
    meta = report["metadata"]
    ai = report["ai_analysis"]
    stats = report["pixel_stats"]
    tissue = report["tissue_breakdown"]

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("DICOM AI Radiology Report", title_style))
    story.append(Paragraph(
        f"Generated: {report['generated_at']}  |  AI Model: {report.get('model', GEMINI_MODEL)}  |  File: {report['filename']}",
        subtitle_style
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1e40af"), spaceAfter=12))

    # ── Disclaimer ────────────────────────────────────────────────────────────
    story.append(Paragraph(
        "⚠ DISCLAIMER: This report is AI-generated for research and educational purposes only. "
        "It is NOT a clinical diagnosis. Always consult a qualified radiologist for medical decisions.",
        disclaimer_style
    ))

    # ── Patient & Study Info ──────────────────────────────────────────────────
    story.append(Paragraph("Patient & Study Information", h2_style))
    info_rows = [
        [Paragraph("Patient Name", cell_bold), Paragraph(meta.get("PatientName","N/A"), cell_style),
         Paragraph("Modality", cell_bold), Paragraph(meta.get("Modality","N/A"), cell_style)],
        [Paragraph("Patient ID", cell_bold), Paragraph(meta.get("PatientID","N/A"), cell_style),
         Paragraph("Body Part", cell_bold), Paragraph(meta.get("BodyPartExamined","N/A"), cell_style)],
        [Paragraph("Date of Birth", cell_bold), Paragraph(meta.get("PatientBirthDate","N/A"), cell_style),
         Paragraph("Study Date", cell_bold), Paragraph(meta.get("StudyDate","N/A"), cell_style)],
        [Paragraph("Sex", cell_bold), Paragraph(meta.get("PatientSex","N/A"), cell_style),
         Paragraph("Study Time", cell_bold), Paragraph(meta.get("StudyTime","N/A"), cell_style)],
        [Paragraph("Age", cell_bold), Paragraph(meta.get("PatientAge","N/A"), cell_style),
         Paragraph("Institution", cell_bold), Paragraph(meta.get("InstitutionName","N/A"), cell_style)],
    ]
    t = Table(info_rows, colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 5.5*cm])
    t.setStyle(table_style)
    story.append(t)
    story.append(Spacer(1, 0.3*cm))

    # ── Equipment ─────────────────────────────────────────────────────────────
    story.append(Paragraph("Equipment & Acquisition", h2_style))
    eq_rows = [
        [Paragraph("Manufacturer", cell_bold), Paragraph(meta.get("Manufacturer","N/A"), cell_style),
         Paragraph("Model", cell_bold), Paragraph(meta.get("ManufacturerModelName","N/A"), cell_style)],
        [Paragraph("Image Size", cell_bold), Paragraph(f"{meta.get('Rows','?')} x {meta.get('Columns','?')} px", cell_style),
         Paragraph("Slice Thickness", cell_bold), Paragraph(meta.get("SliceThickness","N/A"), cell_style)],
        [Paragraph("Pixel Spacing", cell_bold), Paragraph(meta.get("PixelSpacing","N/A"), cell_style),
         Paragraph("Bits Allocated", cell_bold), Paragraph(meta.get("BitsAllocated","N/A"), cell_style)],
        [Paragraph("KVP", cell_bold), Paragraph(meta.get("KVP","N/A"), cell_style),
         Paragraph("Window C/W", cell_bold), Paragraph(f"{meta.get('WindowCenter','N/A')} / {meta.get('WindowWidth','N/A')}", cell_style)],
    ]
    t2 = Table(eq_rows, colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 5.5*cm])
    t2.setStyle(table_style)
    story.append(t2)

    # ── Images ────────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Medical Image(s)", h2_style))

    tmp_imgs = []
    if len(slice_pngs) == 1:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.write(slice_pngs[0]); tmp.flush()
        tmp_imgs.append(tmp.name)
        story.append(RLImage(tmp.name, width=12*cm, height=12*cm, kind="proportional"))
    else:
        cols = 3
        rows_of_imgs = [slice_pngs[i:i+cols] for i in range(0, len(slice_pngs), cols)]
        for row in rows_of_imgs:
            row_data = []
            for png in row:
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                tmp.write(png); tmp.flush()
                tmp_imgs.append(tmp.name)
                row_data.append(RLImage(tmp.name, width=5.5*cm, height=5.5*cm, kind="proportional"))
            while len(row_data) < cols:
                row_data.append(Paragraph("", cell_style))
            img_table = Table([row_data], colWidths=[6*cm]*cols)
            story.append(img_table)
            story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(f"Showing {len(slice_pngs)} representative slices from the volume.", body_style))

    # ── AI Analysis ───────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph(f"AI Analysis — {report.get('model', GEMINI_MODEL)}", h2_style))

    section_labels = [
        ("anatomy_observed", "Anatomy Observed"),
        ("image_quality", "Image Quality"),
        ("findings", "Findings"),
        ("potential_abnormalities", "Potential Abnormalities"),
        ("impression", "Impression"),
        ("recommendations", "Recommendations"),
    ]

    # Color-code impression and abnormalities
    highlight_styles = {
        "impression": ParagraphStyle("Imp", parent=body_style,
                                      backColor=colors.HexColor("#eff6ff"),
                                      borderPadding=6),
        "potential_abnormalities": ParagraphStyle("Abn", parent=body_style,
                                                   backColor=colors.HexColor("#fef9c3"),
                                                   borderPadding=6),
    }

    for key, label in section_labels:
        text = ai.get(key, "").strip()
        if text:
            story.append(Paragraph(label, h3_style))
            s = highlight_styles.get(key, body_style)
            for line in text.splitlines():
                if line.strip():
                    story.append(Paragraph(line.strip(), s))
            story.append(Spacer(1, 0.15*cm))

    # ── Pixel Stats ───────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Pixel & Hounsfield Unit Analysis", h2_style))

    stat_rows = [[
        Paragraph("Min HU", cell_bold), Paragraph(str(stats.get("min","N/A")), cell_style),
        Paragraph("Max HU", cell_bold), Paragraph(str(stats.get("max","N/A")), cell_style),
    ],[
        Paragraph("Mean HU", cell_bold), Paragraph(str(stats.get("mean","N/A")), cell_style),
        Paragraph("Std Dev", cell_bold), Paragraph(str(stats.get("std","N/A")), cell_style),
    ]]
    t3 = Table(stat_rows, colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 5.5*cm])
    t3.setStyle(table_style)
    story.append(t3)
    story.append(Spacer(1, 0.3*cm))

    # Histogram
    if hist_png:
        tmp_hist = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp_hist.write(hist_png); tmp_hist.flush()
        tmp_imgs.append(tmp_hist.name)
        story.append(RLImage(tmp_hist.name, width=15*cm, height=6*cm))
        story.append(Spacer(1, 0.3*cm))

    # Tissue breakdown table
    story.append(Paragraph("Tissue Composition (% of voxels)", h3_style))
    tissue_rows = [["Tissue Type", "HU Range", "% Voxels"]]
    tissue_hu = {
        "Air": "(-1000, -900)", "Lung": "(-900, -500)", "Fat": "(-500, -100)",
        "Water/CSF": "(-10, 10)", "Soft Tissue": "(10, 80)", "Blood": "(30, 70)", "Bone": "(300, 2000)"
    }
    for t_name, pct in tissue.items():
        tissue_rows.append([t_name, tissue_hu.get(t_name,""), f"{pct}%"])

    tissue_table = Table(tissue_rows, colWidths=[5*cm, 5*cm, 5*cm])
    tissue_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1e40af")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#e2e8f0")),
        ("ALIGN", (2,0), (2,-1), "CENTER"),
        ("LEFTPADDING", (0,0), (-1,-1), 7),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(tissue_table)

    # ── All Metadata ──────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Complete DICOM Metadata", h2_style))
    all_tags = report.get("all_tags", {})
    meta_rows = [["Tag", "Value"]]
    for k, v in sorted(all_tags.items()):
        meta_rows.append([Paragraph(k, cell_bold), Paragraph(str(v)[:120], cell_style)])
    meta_table = Table(meta_rows, colWidths=[7*cm, 11*cm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1e40af")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 7),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(meta_table)

    doc.build(story)

    # Cleanup temp images
    for p in tmp_imgs:
        try: os.unlink(p)
        except: pass


# ── API Routes ────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "DICOM AI Report API is running", "version": "1.0.0"}


@app.post("/analyze")
async def analyze_dicom(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".dcm", ".dicom")) and "dicom" not in (file.content_type or ""):
        # Allow any file but warn
        pass

    raw = await file.read()

    try:
        ds = pydicom.dcmread(io.BytesIO(raw), force=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read DICOM file: {e}")

    # ── Extract metadata ───────────────────────────────────────────────────
    meta_keys = [
        "PatientName","PatientID","PatientBirthDate","PatientSex","PatientAge","PatientWeight",
        "StudyDate","StudyTime","StudyDescription","AccessionNumber",
        "Modality","BodyPartExamined","SeriesDescription","SeriesNumber",
        "Manufacturer","ManufacturerModelName","InstitutionName","StationName",
        "Rows","Columns","PixelSpacing","SliceThickness","SliceLocation",
        "BitsAllocated","BitsStored","KVP","WindowCenter","WindowWidth",
        "RescaleSlope","RescaleIntercept","PhotometricInterpretation",
        "SOPClassUID","SOPInstanceUID","StudyInstanceUID","SeriesInstanceUID",
    ]
    metadata = {k: safe_tag(ds, k) for k in meta_keys}

    # All tags
    all_tags = {}
    for elem in ds:
        if elem.keyword and elem.keyword != "PixelData":
            try:
                all_tags[elem.keyword] = str(elem.value)[:200]
            except Exception:
                all_tags[elem.keyword] = "<unreadable>"

    # ── Pixel processing ───────────────────────────────────────────────────
    has_pixels = hasattr(ds, "PixelData")
    slice_pngs = []
    pixel_stats = {}
    tissue_breakdown = {}
    hist_png = None
    ai_analysis = {}

    if has_pixels:
        try:
            px = ds.pixel_array
            slice_pngs = extract_slices(px, ds, n=6)

            # Stats on first or only slice
            sample = px[px.shape[0]//2] if px.ndim == 3 else px
            pixel_stats, tissue_breakdown, hu_arr = compute_pixel_stats(sample, ds)
            hist_png = make_histogram_png(hu_arr)

            # AI analysis on middle/only slice
            ai_png = slice_pngs[len(slice_pngs)//2]
            raw_ai = analyze_with_gemini(ai_png, metadata)
            ai_analysis = parse_ai_sections(raw_ai)
            ai_analysis["raw"] = raw_ai

        except Exception as e:
            ai_analysis = {"raw": f"Image processing error: {e}"}

    # ── Build JSON report ──────────────────────────────────────────────────
    report_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = {
        "report_id": report_id,
        "filename": file.filename,
        "generated_at": datetime.now().isoformat(),
        "model": GEMINI_MODEL,
        "metadata": metadata,
        "all_tags": all_tags,
        "pixel_stats": pixel_stats,
        "tissue_breakdown": tissue_breakdown,
        "ai_analysis": ai_analysis,
        "has_pixel_data": has_pixels,
        "num_slices": len(slice_pngs),
    }

    # Save JSON
    json_path = OUTPUT_DIR / f"{report_id}.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Build PDF
    pdf_path = str(OUTPUT_DIR / f"{report_id}.pdf")
    build_pdf(report, slice_pngs, hist_png, pdf_path)

    return JSONResponse({
        "report_id": report_id,
        "model": GEMINI_MODEL,
        "json_url": f"/report/{report_id}/json",
        "pdf_url": f"/report/{report_id}/pdf",
        "summary": {
            "patient": metadata.get("PatientName", "N/A"),
            "modality": metadata.get("Modality", "N/A"),
            "study_date": metadata.get("StudyDate", "N/A"),
            "num_slices": len(slice_pngs),
            "impression": ai_analysis.get("impression", ""),
        }
    })


@app.get("/report/{report_id}/json")
def get_json(report_id: str):
    path = OUTPUT_DIR / f"{report_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path, media_type="application/json", filename=f"report_{report_id}.json")


@app.get("/report/{report_id}/pdf")
def get_pdf(report_id: str):
    path = OUTPUT_DIR / f"{report_id}.pdf"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path, media_type="application/pdf", filename=f"report_{report_id}.pdf")


@app.get("/reports")
def list_reports():
    reports = []
    for p in sorted(OUTPUT_DIR.glob("*.json"), reverse=True):
        try:
            with open(p) as f:
                r = json.load(f)
            reports.append({
                "report_id": r["report_id"],
                "filename": r["filename"],
                "generated_at": r["generated_at"],
                "patient": r["metadata"].get("PatientName","N/A"),
                "modality": r["metadata"].get("Modality","N/A"),
            })
        except Exception:
            pass
    return reports


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
