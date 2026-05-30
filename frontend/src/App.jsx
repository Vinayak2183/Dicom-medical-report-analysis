import DropZone from "./components/DropZone.jsx";
import ReportView from "./components/ReportView.jsx";
import { useAnalyze } from "./hooks/useAnalyze.js";

export default function App() {
  const { status, files, report, error, processFiles, reset } = useAnalyze();

  return (
    <div style={{ fontFamily: "var(--font-sans)", maxWidth: 900, margin: "0 auto", padding: "2rem 1rem" }}>
      <header style={{ marginBottom: 32 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <i className="ti ti-report-medical" style={{ fontSize: 22, color: "var(--color-text-info)" }} aria-hidden />
          <h1 style={{ fontSize: 22, fontWeight: 500, margin: 0 }}>DICOM AI Report</h1>
        </div>
        <p style={{ fontSize: 14, color: "var(--color-text-secondary)", margin: 0, lineHeight: 1.6 }}>
          Upload a full DICOM study — hospital <code>Images/</code> folder, multiple <code>.dic</code> slices, or a zip.
          The system stacks the 3D volume, runs multi-slice AI analysis, and generates a structured PDF report.
        </p>
      </header>

      {status !== "done" && (
        <DropZone
          status={status}
          files={files}
          error={error}
          onFiles={processFiles}
          onReset={reset}
        />
      )}

      {status === "done" && report && (
        <ReportView report={report} onReset={reset} />
      )}

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
