import { useState, useRef, useCallback } from "react";

const API = "http://localhost:8000";

const STATUS = {
  idle: { label: "Drop your DICOM file", icon: "ti-file-medical", color: "var(--color-text-secondary)" },
  uploading: { label: "Uploading...", icon: "ti-loader-2", color: "var(--color-text-info)", spin: true },
  analyzing: { label: "AI analyzing image...", icon: "ti-brain", color: "var(--color-text-info)", spin: true },
  done: { label: "Report ready", icon: "ti-circle-check", color: "var(--color-text-success)" },
  error: { label: "Something went wrong", icon: "ti-alert-circle", color: "var(--color-text-danger)" },
};

const Tag = ({ label, value }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
    <span style={{ fontSize: 11, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</span>
    <span style={{ fontSize: 14, fontWeight: 500, color: "var(--color-text-primary)" }}>{value || "—"}</span>
  </div>
);

const SectionCard = ({ title, icon, children, accent }) => (
  <div style={{
    background: "var(--color-background-primary)",
    border: `0.5px solid ${accent ? "var(--color-border-info)" : "var(--color-border-tertiary)"}`,
    borderRadius: "var(--border-radius-lg)",
    overflow: "hidden",
    marginBottom: 16,
  }}>
    <div style={{
      padding: "12px 20px",
      borderBottom: "0.5px solid var(--color-border-tertiary)",
      display: "flex", alignItems: "center", gap: 10,
      background: accent ? "var(--color-background-info)" : "var(--color-background-secondary)",
    }}>
      <i className={`ti ${icon}`} style={{ fontSize: 16, color: accent ? "var(--color-text-info)" : "var(--color-text-secondary)" }} aria-hidden />
      <span style={{ fontSize: 13, fontWeight: 500, color: accent ? "var(--color-text-info)" : "var(--color-text-primary)" }}>{title}</span>
    </div>
    <div style={{ padding: "16px 20px" }}>{children}</div>
  </div>
);

const stripMarkdown = (text) =>
  text
    .replace(/\*\*(.*?)\*\*/g, "$1")   // bold
    .replace(/\*(.*?)\*/g, "$1")       // italic
    .replace(/#{1,3}\s*/g, "")         // headings
    .replace(/^\s*[-•]\s*/gm, "• ");   // bullets

const AiBlock = ({ label, text, highlight }) => {
  if (!text) return null;
  const clean = stripMarkdown(text);
  return (
    <div style={{ marginBottom: 16 }}>
      <p style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>{label}</p>
      <div style={{
        fontSize: 14, lineHeight: 1.7, color: "var(--color-text-primary)",
        background: highlight ? "var(--color-background-warning)" : "transparent",
        borderLeft: highlight ? "3px solid var(--color-border-warning)" : "none",
        padding: highlight ? "10px 14px" : 0,
        borderRadius: highlight ? "0 var(--border-radius-md) var(--border-radius-md) 0" : 0,
      }}>
        {clean.split("\n").filter(Boolean).map((line, i) => <p key={i} style={{ margin: "0 0 6px" }}>{line}</p>)}
      </div>
    </div>
  );
};

export default function App() {
  const [status, setStatus] = useState("idle");
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("ai");
  const inputRef = useRef();

  const processFile = useCallback(async (f) => {
    setFile(f);
    setError("");
    setReport(null);
    setStatus("uploading");

    const fd = new FormData();
    fd.append("file", f);

    try {
      setStatus("analyzing");
      const res = await fetch(`${API}/analyze`, { method: "POST", body: fd });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Analysis failed");
      }
      const data = await res.json();

      // Fetch full JSON report
      const jsonRes = await fetch(`${API}/report/${data.report_id}/json`);
      const fullReport = await jsonRes.json();

      setReport({ ...data, full: fullReport });
      setStatus("done");
      setActiveTab("ai");
    } catch (e) {
      setError(e.message);
      setStatus("error");
    }
  }, []);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) processFile(f);
  }, [processFile]);

  const onDragOver = (e) => { e.preventDefault(); setDragging(true); };
  const onDragLeave = () => setDragging(false);

  const st = STATUS[status];
  const meta = report?.full?.metadata || {};
  const ai = report?.full?.ai_analysis || {};
  const stats = report?.full?.pixel_stats || {};
  const tissue = report?.full?.tissue_breakdown || {};
  const allTags = report?.full?.all_tags || {};

  const tabs = [
    { id: "ai", label: "AI Analysis", icon: "ti-brain" },
    { id: "meta", label: "Patient Info", icon: "ti-user" },
    { id: "pixel", label: "Pixel Stats", icon: "ti-chart-histogram" },
    { id: "tags", label: "All Tags", icon: "ti-tags" },
  ];

  return (
    <div style={{ fontFamily: "var(--font-sans)", maxWidth: 860, margin: "0 auto", padding: "2rem 1rem" }}>
      <h2 className="sr-only">DICOM AI Radiology Report Generator</h2>

      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <i className="ti ti-report-medical" style={{ fontSize: 22, color: "var(--color-text-info)" }} aria-hidden />
          <h1 style={{ fontSize: 22, fontWeight: 500, margin: 0, color: "var(--color-text-primary)" }}>DICOM AI Report</h1>
        </div>
        <p style={{ fontSize: 14, color: "var(--color-text-secondary)", margin: 0 }}>
          Upload a <code>.dcm</code> file — Gemini 1.5 Flash analyzes the image and generates a full PDF report.
        </p>
      </div>

      {/* Drop Zone */}
      <div
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={() => status !== "uploading" && status !== "analyzing" && inputRef.current?.click()}
        style={{
          border: `1.5px dashed ${dragging ? "var(--color-border-info)" : "var(--color-border-secondary)"}`,
          borderRadius: "var(--border-radius-lg)",
          background: dragging ? "var(--color-background-info)" : "var(--color-background-secondary)",
          padding: "36px 24px",
          textAlign: "center",
          cursor: status === "uploading" || status === "analyzing" ? "wait" : "pointer",
          transition: "all 0.15s",
          marginBottom: 24,
        }}
      >
        <input ref={inputRef} type="file" accept=".dcm,.dicom" style={{ display: "none" }}
          onChange={e => e.target.files[0] && processFile(e.target.files[0])} />
        <i className={`ti ${st.icon}${st.spin ? " spin" : ""}`}
          style={{ fontSize: 32, color: st.color, display: "block", marginBottom: 10 }} aria-hidden />
        <p style={{ margin: 0, fontWeight: 500, color: "var(--color-text-primary)", fontSize: 15 }}>{st.label}</p>
        {status === "idle" && (
          <p style={{ margin: "6px 0 0", fontSize: 13, color: "var(--color-text-secondary)" }}>
            Drag & drop or click to browse · .dcm / .dicom files
          </p>
        )}
        {file && status !== "idle" && (
          <p style={{ margin: "6px 0 0", fontSize: 12, color: "var(--color-text-secondary)" }}>
            {file.name} · {(file.size / 1024).toFixed(0)} KB
          </p>
        )}
        {status === "error" && (
          <p style={{ margin: "8px 0 0", fontSize: 13, color: "var(--color-text-danger)" }}>{error}</p>
        )}
      </div>

      {/* Progress steps while loading */}
      {(status === "uploading" || status === "analyzing") && (
        <div style={{ display: "flex", gap: 8, marginBottom: 24, justifyContent: "center" }}>
          {["Uploading file", "Extracting DICOM data", "AI analyzing image", "Building PDF"].map((step, i) => {
            const active = (status === "uploading" && i === 0) || (status === "analyzing" && i >= 1);
            return (
              <div key={i} style={{
                display: "flex", alignItems: "center", gap: 6, fontSize: 12,
                color: active ? "var(--color-text-info)" : "var(--color-text-secondary)",
                fontWeight: active ? 500 : 400,
              }}>
                {i > 0 && <i className="ti ti-chevron-right" style={{ fontSize: 12 }} aria-hidden />}
                {step}
              </div>
            );
          })}
        </div>
      )}

      {/* Report */}
      {status === "done" && report && (
        <div>
          {/* Summary bar */}
          <div style={{
            background: "var(--color-background-primary)",
            border: "0.5px solid var(--color-border-tertiary)",
            borderRadius: "var(--border-radius-lg)",
            padding: "16px 20px",
            marginBottom: 20,
            display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12,
          }}>
            <div style={{ display: "flex", gap: 28, flexWrap: "wrap" }}>
              <Tag label="Patient" value={meta.PatientName} />
              <Tag label="Modality" value={meta.Modality} />
              <Tag label="Body Part" value={meta.BodyPartExamined} />
              <Tag label="Study Date" value={meta.StudyDate} />
              <Tag label="Slices" value={report.num_slices > 1 ? `${report.num_slices} frames` : "Single frame"} />
              <Tag label="AI Model" value={report.model || "gemini-2.5-flash"} />
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <a href={`${API}/report/${report.report_id}/json`} target="_blank" rel="noreferrer">
                <button style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                  <i className="ti ti-download" style={{ fontSize: 15 }} aria-hidden /> JSON
                </button>
              </a>
              <a href={`${API}/report/${report.report_id}/pdf`} target="_blank" rel="noreferrer">
                <button style={{
                  display: "flex", alignItems: "center", gap: 6, fontSize: 13,
                  background: "var(--color-background-info)",
                  color: "var(--color-text-info)",
                  border: "0.5px solid var(--color-border-info)",
                }}>
                  <i className="ti ti-file-type-pdf" style={{ fontSize: 15 }} aria-hidden /> Download PDF
                </button>
              </a>
            </div>
          </div>

          {/* Tabs */}
          <div style={{ display: "flex", gap: 4, marginBottom: 16, borderBottom: "0.5px solid var(--color-border-tertiary)", paddingBottom: 0 }}>
            {tabs.map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
                display: "flex", alignItems: "center", gap: 6, fontSize: 13,
                padding: "8px 14px",
                border: "none",
                borderBottom: activeTab === tab.id ? "2px solid var(--color-text-info)" : "2px solid transparent",
                borderRadius: 0,
                background: "transparent",
                color: activeTab === tab.id ? "var(--color-text-info)" : "var(--color-text-secondary)",
                fontWeight: activeTab === tab.id ? 500 : 400,
                cursor: "pointer",
              }}>
                <i className={`ti ${tab.icon}`} style={{ fontSize: 15 }} aria-hidden />
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab: AI Analysis */}
          {activeTab === "ai" && (
            <div>
              <div style={{
                background: "var(--color-background-danger)",
                border: "0.5px solid var(--color-border-danger)",
                borderRadius: "var(--border-radius-md)",
                padding: "10px 14px",
                fontSize: 12,
                color: "var(--color-text-danger)",
                marginBottom: 16,
                display: "flex", alignItems: "center", gap: 8,
              }}>
                <i className="ti ti-alert-triangle" style={{ fontSize: 15 }} aria-hidden />
                AI-generated for research/education only. Not a clinical diagnosis. Consult a qualified radiologist.
              </div>

              <SectionCard title="Anatomy Observed" icon="ti-body-scan" accent>
                <AiBlock text={ai.anatomy_observed} />
              </SectionCard>
              <SectionCard title="Image Quality" icon="ti-camera">
                <AiBlock text={ai.image_quality} />
              </SectionCard>
              <SectionCard title="Findings" icon="ti-search">
                <AiBlock text={ai.findings} />
              </SectionCard>
              <SectionCard title="Potential Abnormalities" icon="ti-alert-circle">
                <AiBlock text={ai.potential_abnormalities} highlight />
              </SectionCard>
              <SectionCard title="Impression" icon="ti-notes" accent>
                <AiBlock text={ai.impression} />
              </SectionCard>
              <SectionCard title="Recommendations" icon="ti-clipboard-list">
                <AiBlock text={ai.recommendations} />
              </SectionCard>

              {/* Fallback: show raw if all sections empty */}
              {!ai.anatomy_observed && !ai.findings && !ai.impression && ai.raw && (
                <SectionCard title="AI Response (raw)" icon="ti-message">
                  <div style={{ fontSize: 13, lineHeight: 1.8, color: "var(--color-text-primary)", whiteSpace: "pre-wrap" }}>
                    {ai.raw}
                  </div>
                </SectionCard>
              )}
            </div>
          )}

          {/* Tab: Patient Info */}
          {activeTab === "meta" && (
            <div>
              {[
                {
                  title: "Patient", icon: "ti-user",
                  fields: [["Name", meta.PatientName], ["ID", meta.PatientID], ["Date of Birth", meta.PatientBirthDate], ["Sex", meta.PatientSex], ["Age", meta.PatientAge], ["Weight", meta.PatientWeight]],
                },
                {
                  title: "Study", icon: "ti-stethoscope",
                  fields: [["Study Date", meta.StudyDate], ["Study Time", meta.StudyTime], ["Description", meta.StudyDescription], ["Accession #", meta.AccessionNumber], ["Institution", meta.InstitutionName]],
                },
                {
                  title: "Image", icon: "ti-scan",
                  fields: [["Modality", meta.Modality], ["Body Part", meta.BodyPartExamined], ["Rows × Cols", `${meta.Rows} × ${meta.Columns}`], ["Pixel Spacing", meta.PixelSpacing], ["Slice Thickness", meta.SliceThickness], ["Bits Allocated", meta.BitsAllocated]],
                },
                {
                  title: "Equipment", icon: "ti-device-desktop-analytics",
                  fields: [["Manufacturer", meta.Manufacturer], ["Model", meta.ManufacturerModelName], ["KVP", meta.KVP], ["Window Center", meta.WindowCenter], ["Window Width", meta.WindowWidth]],
                },
              ].map(section => (
                <SectionCard key={section.title} title={section.title} icon={section.icon}>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "14px 24px" }}>
                    {section.fields.map(([label, value]) => <Tag key={label} label={label} value={value} />)}
                  </div>
                </SectionCard>
              ))}
            </div>
          )}

          {/* Tab: Pixel Stats */}
          {activeTab === "pixel" && (
            <div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
                {[["Min HU", stats.min], ["Max HU", stats.max], ["Mean HU", stats.mean], ["Std Dev", stats.std]].map(([label, val]) => (
                  <div key={label} style={{ background: "var(--color-background-secondary)", borderRadius: "var(--border-radius-md)", padding: "14px 16px" }}>
                    <p style={{ fontSize: 11, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 4px" }}>{label}</p>
                    <p style={{ fontSize: 22, fontWeight: 500, margin: 0, color: "var(--color-text-primary)" }}>{val ?? "—"}</p>
                  </div>
                ))}
              </div>

              <SectionCard title="Tissue Breakdown (% of voxels)" icon="ti-chart-bar">
                {Object.entries(tissue).map(([name, pct]) => (
                  <div key={name} style={{ marginBottom: 10 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
                      <span style={{ color: "var(--color-text-primary)" }}>{name}</span>
                      <span style={{ color: "var(--color-text-secondary)", fontWeight: 500 }}>{pct}%</span>
                    </div>
                    <div style={{ height: 6, background: "var(--color-background-secondary)", borderRadius: 3, overflow: "hidden" }}>
                      <div style={{
                        height: "100%", width: `${Math.min(pct * 10, 100)}%`,
                        background: "var(--color-text-info)",
                        borderRadius: 3, transition: "width 0.4s ease",
                      }} />
                    </div>
                  </div>
                ))}
              </SectionCard>
            </div>
          )}

          {/* Tab: All Tags */}
          {activeTab === "tags" && (
            <SectionCard title={`All DICOM Tags (${Object.keys(allTags).length})`} icon="ti-tags">
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px 24px" }}>
                {Object.entries(allTags).sort(([a],[b]) => a.localeCompare(b)).map(([key, val]) => (
                  <div key={key} style={{ display: "flex", gap: 8, padding: "5px 0", borderBottom: "0.5px solid var(--color-border-tertiary)" }}>
                    <span style={{ fontSize: 12, color: "var(--color-text-secondary)", minWidth: 120, flexShrink: 0 }}>{key}</span>
                    <span style={{ fontSize: 12, color: "var(--color-text-primary)", wordBreak: "break-all" }}>{String(val).slice(0, 80)}</span>
                  </div>
                ))}
              </div>
            </SectionCard>
          )}

          {/* New scan button */}
          <div style={{ textAlign: "center", marginTop: 24 }}>
            <button onClick={() => { setStatus("idle"); setReport(null); setFile(null); }}
              style={{ fontSize: 13, display: "inline-flex", alignItems: "center", gap: 6 }}>
              <i className="ti ti-refresh" style={{ fontSize: 15 }} aria-hidden /> Analyze another file
            </button>
          </div>
        </div>
      )}

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); }
      `}</style>
    </div>
  );
}
