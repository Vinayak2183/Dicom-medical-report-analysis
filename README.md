# DICOM AI Report Generator

Upload a hospital DICOM study (folder, individual slices, or `.zip`) and get an **AI-generated structured report** with findings, pixel statistics, and downloadable **JSON + PDF**.

Built for real hospital CD layouts — e.g. an `Images/` folder full of `.dic` slices — without needing a PACS or DICOM viewer.

---

## What it does

1. **Ingests** DICOM files from a folder, multiple files, or a zip archive
2. **Groups** slices into series and picks the main diagnostic series (skips scout/localizer)
3. **Samples** representative slices across the volume and computes Hounsfield Unit (HU) stats
4. **Analyzes** images with medical AI (Dr7.ai or Google Gemini)
5. **Generates** a structured JSON report and PDF you can download from the UI

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.10+ (3.11 recommended) |
| Node.js | 18+ |
| npm | 9+ |

You also need **at least one AI API key**:

- **[Dr7.ai](https://dr7.ai/access-api)** — recommended for medical imaging (CheXagent, MedGemma, LLaVA-Med)
- **[Google Gemini](https://aistudio.google.com)** — fallback / standalone option

---

## Quick start

### 1. Clone and open the project

```powershell
cd Dicom-medical-report-analysis
```

### 2. Backend setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy the example env file and add your API key(s):

```powershell
copy .env.example .env
```

Edit `backend/.env` — set at least one of:

```env
DR7_API_KEY=sk-your-dr7-key          # recommended
GEMINI_API_KEY=your-gemini-key       # required if DR7 is not set
AI_PROVIDER=auto                     # auto | dr7 | gemini
```

### 3. Frontend setup

```powershell
cd ..\frontend
npm install
```

### 4. Run (two terminals)

**Terminal 1 — Backend** (API on port 8000):

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python run.py
```

You should see:

```
Backend API:  http://127.0.0.1:8000/
API docs:     http://127.0.0.1:8000/docs
Frontend UI:  http://localhost:3000
```

**Terminal 2 — Frontend** (UI on port 3000):

```powershell
cd frontend
npm run dev
```

Open **http://localhost:3000** in your browser.

> The frontend proxies API calls to the backend. Both servers must be running.

---

## How to upload a study

On the web UI you have three options:

| Button | Best for |
|--------|----------|
| **Select folder** | Hospital CD `Images/` folder (hundreds or thousands of slices) |
| **Select files** | A few `.dic`, `.dcm`, `.ima`, or extensionless DICOM files |
| **Upload .zip** | Large studies — zip the `Images/` folder first (most reliable for 500+ slices) |

### Recommended workflow for hospital CDs

```
PatientStudy/
├── DICOMDIR              ← ignored
├── Images/
│   ├── 1.3.12...001.dic  ← slice 1
│   ├── 1.3.12...002.dic  ← slice 2
│   └── ...
└── DICOMViewer.exe       ← ignored
```

1. Zip the **`Images`** folder (not the whole CD root) for large studies
2. Use **Upload .zip** — faster and more stable than selecting 1000+ files in the browser
3. Wait for upload → series grouping → AI analysis → report

### Supported file types

- Extensions: `.dic`, `.dcm`, `.dicom`, `.ima`
- Extensionless DICOM files (common on hospital CDs)
- `.zip` archives containing DICOM slices (nested folders inside the zip are fine)
- Automatically skipped: `DICOMDIR`, `.exe`, `.dll`, `.txt`, `.html`, etc.

### Upload limits (configurable in `.env`)

| Setting | Default |
|---------|---------|
| `MAX_UPLOAD_SIZE_MB` | 512 MB |
| `MAX_UPLOAD_FILES` | 2000 files |
| Upload timeout | 10 minutes |

---

## Using the report

After analysis completes:

1. Review tabs: **AI Analysis**, **Series**, **Patient Info**, **Pixel Stats**
2. Download **PDF** or **JSON**
3. Click **Analyze another study** to reset

Reports are also saved on disk at `backend/reports/{report_id}/`.

---

## Environment variables

All settings live in `backend/.env`. See `backend/.env.example` for the full template.

| Variable | Default | Description |
|----------|---------|-------------|
| `DR7_API_KEY` | — | Dr7.ai API key (`sk-...`) |
| `DR7_BASE_URL` | `https://dr7.ai/api/v1` | Dr7 API base URL |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `AI_PROVIDER` | `auto` | `auto` (prefer Dr7), `dr7`, or `gemini` |
| `HOST` | `127.0.0.1` | Backend bind address |
| `PORT` | `8000` | Backend port |
| `AI_SLICE_COUNT` | `8` | Slices sent to AI for vision analysis |
| `MAX_UPLOAD_FILES` | `2000` | Max files per upload request |
| `MAX_UPLOAD_SIZE_MB` | `512` | Max total upload size |

**Provider resolution (`AI_PROVIDER=auto`):**

1. Dr7 if `DR7_API_KEY` is set and starts with `sk-`
2. Otherwise Gemini if `GEMINI_API_KEY` is set
3. Otherwise startup/analysis fails with a clear config error

---

## API reference

Interactive docs: **http://127.0.0.1:8000/docs**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | API status and configured AI provider |
| `POST` | `/analyze` | Upload DICOM files (multipart field: `files`) |
| `GET` | `/report/{id}/json` | Download JSON report |
| `GET` | `/report/{id}/pdf` | Download PDF report |
| `GET` | `/reports` | List saved reports |

Example health check:

```powershell
curl http://127.0.0.1:8000/health
```

---

## AI models (by modality)

When using Dr7 (`AI_PROVIDER=auto` or `dr7`):

| Modality | Vision model | Refine model |
|----------|--------------|--------------|
| X-ray (CR, DX, XR) | CheXagent | Baichuan-M3 |
| CT / MRI / PET / NM | MedGemma-27B | Baichuan-M3 |
| Other | LLaVA-Med | MedGemma-27B |

When using Gemini (`AI_PROVIDER=gemini`, or Dr7 fallback): **Gemini 2.5 Flash**.

---

## Project structure

```
Dicom-medical-report-analysis/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Settings from .env
│   │   ├── api/routes/          # /analyze, /health, /report
│   │   ├── models/schemas.py    # Request/response models
│   │   ├── services/
│   │   │   ├── dicom/           # Ingest, series grouping, windowing
│   │   │   ├── analysis/        # Pipeline, HU/pixel statistics
│   │   │   ├── ai/              # Dr7, Gemini, modality routing
│   │   │   └── report/          # PDF generation, file storage
│   │   └── utils/               # DICOM tag helpers
│   ├── reports/                 # Generated reports (gitignored)
│   ├── .env                     # Your secrets (gitignored — do not commit)
│   ├── .env.example             # Template to copy
│   ├── requirements.txt
│   └── run.py                   # Start: python run.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Main page
│   │   ├── api/client.js        # Backend API client
│   │   ├── components/          # DropZone, ReportView
│   │   └── hooks/useAnalyze.js  # Upload + analysis state
│   ├── vite.config.js           # Dev server + API proxy to :8000
│   └── package.json
└── README.md
```

---

## Troubleshooting

### "Could not reach the backend on port 8000"

- Start the backend first: `python run.py` in `backend/`
- Keep both terminals open while uploading
- Do not stop the backend mid-upload — uvicorn reload will drop the connection
- For large folders, **zip first** instead of selecting 500+ files

### "No series with pixel data found"

- Upload the **full study** (entire `Images/` folder or zip), not just a few random files
- Ensure files are actual image slices, not only `DICOMDIR` or viewer metadata
- Supported formats: `.dic`, `.dcm`, `.ima`, or extensionless DICOM with pixel data

### "No DICOM files found"

- Check that you selected the folder containing slices (usually `Images/`)
- Try zipping the folder and using **Upload .zip**
- Non-DICOM files (`.exe`, `.txt`, `DICOMDIR`) are skipped automatically

### "Upload timed out"

- Zip the study and upload the `.zip` file
- Increase limits in `.env` if your study exceeds 512 MB

### "No AI provider configured"

- Set `DR7_API_KEY` and/or `GEMINI_API_KEY` in `backend/.env`
- Restart the backend after editing `.env`

### Port already in use

```powershell
# Find what is using port 8000 or 3000
netstat -ano | findstr ":8000"
netstat -ano | findstr ":3000"

# Stop the process (replace PID)
taskkill /PID <pid> /F
```

### Verify backend is healthy

```powershell
curl http://127.0.0.1:8000/health
```

---

## Development notes

- Backend runs with **auto-reload** (`uvicorn --reload`) — code changes restart the server
- Frontend dev server proxies `/analyze`, `/report`, `/health` to `http://127.0.0.1:8000`
- Generated reports in `backend/reports/` are gitignored
- **Never commit** `backend/.env` — it contains API keys

### Production build (frontend only)

```powershell
cd frontend
npm run build
npm run preview
```

For production, serve the built frontend and point API calls at your deployed backend (update proxy or `API` base URL in `frontend/src/api/client.js`).

---

## Disclaimer

**For research and educational use only.**

AI-generated findings are **not** a clinical diagnosis. Always consult a qualified radiologist or physician for medical decisions. Do not upload real patient data to third-party APIs unless you have proper authorization and compliance in place.
