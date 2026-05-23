# DICOM AI Report Generator

Upload a `.dcm` file → Gemini 1.5 Flash analyzes the scan → get a full PDF + JSON report.

## What it does

- Reads any DICOM file (X-ray, CT, MRI)
- Extracts all metadata tags (patient, study, equipment, UIDs)
- Applies correct windowing so images look like a radiologist sees them
- Sends the image to **Gemini 1.5 Flash (free)** for AI analysis
- Generates structured sections: Anatomy, Findings, Abnormalities, Impression, Recommendations
- Computes Hounsfield Unit stats + tissue breakdown (air, fat, bone, soft tissue...)
- Saves everything as **JSON** and renders a **PDF report**
- React frontend with drag-and-drop upload, tabbed report viewer, one-click PDF download

---

## Project Structure

```
dicom-report/
├── backend/
│   ├── main.py            # FastAPI app — all processing logic
│   └── requirements.txt
├── frontend/
│   ├── index.html         # HTML shell + CSS variables
│   ├── main.jsx           # React entry point
│   ├── App.jsx            # Full React UI
│   ├── vite.config.js     # Vite + proxy config
│   └── package.json
└── README.md
```

---

## Setup

### 1. Get a free Gemini API key

Go to https://aistudio.google.com → Sign in → "Get API key" → copy it.

### 2. Backend

```bash
cd backend
pip install -r requirements.txt

# Set your Gemini API key
export GEMINI_API_KEY="your_key_here"   # Mac/Linux
set GEMINI_API_KEY=your_key_here        # Windows

python main.py
# → API running at http://localhost:8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# → UI running at http://localhost:3000
```

---

## Usage

1. Open http://localhost:3000
2. Drag and drop a `.dcm` file (or click to browse)
3. Wait ~15–30 seconds for AI analysis
4. View the report in 4 tabs: AI Analysis, Patient Info, Pixel Stats, All Tags
5. Click **Download PDF** to save the full report

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/analyze` | Upload `.dcm` file, returns report_id + URLs |
| GET | `/report/{id}/json` | Download the JSON report |
| GET | `/report/{id}/pdf` | Download the PDF report |
| GET | `/reports` | List all past reports |

---

## PDF Report Sections

1. **Patient & Study Info** — name, ID, modality, dates, institution
2. **Equipment & Acquisition** — scanner, KVP, window settings
3. **Medical Image(s)** — windowed grayscale, up to 6 representative slices
4. **AI Analysis** — anatomy, image quality, findings, abnormalities, impression, recommendations
5. **Pixel & HU Analysis** — min/max/mean/std, HU histogram, tissue breakdown table
6. **Complete DICOM Metadata** — every tag in the file

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Your Gemini API key (required) | `YOUR_GEMINI_API_KEY_HERE` |

---

## Disclaimer

This tool is for **research and educational purposes only**. AI-generated findings are not a clinical diagnosis. Always consult a qualified radiologist for medical decisions.
