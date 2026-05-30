import { useState } from "react";
import { reportJsonUrl, reportPdfUrl } from "../api/client.js";
import { AiBlock, Disclaimer, SectionCard, Tag } from "./ui.jsx";

const TABS = [
  { id: "ai", label: "AI Analysis", icon: "ti-brain" },
  { id: "series", label: "Series", icon: "ti-stack-2" },
  { id: "meta", label: "Patient Info", icon: "ti-user" },
  { id: "pixel", label: "Pixel Stats", icon: "ti-chart-histogram" },
  { id: "tags", label: "All Tags", icon: "ti-tags" },
];

export default function ReportView({ report, onReset }) {
  const [activeTab, setActiveTab] = useState("ai");
  const meta = report?.full?.metadata || {};
  const ai = report?.full?.ai_analysis || {};
  const stats = report?.full?.pixel_stats || {};
  const tissue = report?.full?.tissue_breakdown || {};
  const allTags = report?.full?.all_tags || {};
  const seriesInfo = report?.series_info || report?.full?.series_info || [];
  const structured = ai.structured_abnormalities || [];

  return (
    <div>
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
          <Tag label="Slices" value={`${report.summary?.num_slices ?? report.full?.num_slices ?? 0} in series`} />
          <Tag label="Series" value={report.summary?.selected_series || report.full?.selected_series_description} />
          <Tag label="Confidence" value={ai.overall_confidence || report.summary?.overall_confidence} />
          <Tag label="AI" value={report.model || report.full?.model} />
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <a href={reportJsonUrl(report.report_id)} target="_blank" rel="noreferrer">
            <button type="button" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
              <i className="ti ti-download" aria-hidden /> JSON
            </button>
          </a>
          <a href={reportPdfUrl(report.report_id)} target="_blank" rel="noreferrer">
            <button type="button" style={{
              display: "flex", alignItems: "center", gap: 6, fontSize: 13,
              background: "var(--color-background-info)",
              color: "var(--color-text-info)",
              border: "0.5px solid var(--color-border-info)",
            }}>
              <i className="ti ti-file-type-pdf" aria-hidden /> Download PDF
            </button>
          </a>
        </div>
      </div>

      <div style={{ display: "flex", gap: 4, marginBottom: 16, borderBottom: "0.5px solid var(--color-border-tertiary)" }}>
        {TABS.map((tab) => (
          <button key={tab.id} type="button" onClick={() => setActiveTab(tab.id)} style={{
            display: "flex", alignItems: "center", gap: 6, fontSize: 13, padding: "8px 14px",
            border: "none",
            borderBottom: activeTab === tab.id ? "2px solid var(--color-text-info)" : "2px solid transparent",
            borderRadius: 0, background: "transparent",
            color: activeTab === tab.id ? "var(--color-text-info)" : "var(--color-text-secondary)",
            fontWeight: activeTab === tab.id ? 500 : 400, cursor: "pointer",
          }}>
            <i className={`ti ${tab.icon}`} style={{ fontSize: 15 }} aria-hidden />
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "ai" && (
        <div>
          <Disclaimer />
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
            {structured.length > 0 && (
              <div style={{ marginTop: 12, overflowX: "auto" }}>
                <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ textAlign: "left", borderBottom: "1px solid var(--color-border-tertiary)" }}>
                      <th style={{ padding: 8 }}>Structure</th>
                      <th style={{ padding: 8 }}>Description</th>
                      <th style={{ padding: 8 }}>Confidence</th>
                      <th style={{ padding: 8 }}>Review</th>
                    </tr>
                  </thead>
                  <tbody>
                    {structured.map((item, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid var(--color-border-tertiary)" }}>
                        <td style={{ padding: 8 }}>{item.structure}</td>
                        <td style={{ padding: 8 }}>{item.description}</td>
                        <td style={{ padding: 8 }}>{item.confidence}</td>
                        <td style={{ padding: 8 }}>{item.needs_radiologist_review ? "Yes" : "No"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>
          <SectionCard title="Impression" icon="ti-notes" accent>
            <AiBlock text={ai.impression} />
          </SectionCard>
          <SectionCard title="Recommendations" icon="ti-clipboard-list">
            <AiBlock text={ai.recommendations} />
          </SectionCard>
          {ai.limitations && (
            <SectionCard title="Limitations" icon="ti-info-circle">
              <AiBlock text={ai.limitations} />
            </SectionCard>
          )}
        </div>
      )}

      {activeTab === "series" && (
        <SectionCard title={`DICOM Series (${seriesInfo.length})`} icon="ti-stack-2" accent>
          {seriesInfo.length === 0 ? (
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>No series metadata available.</p>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ textAlign: "left" }}>
                    <th style={{ padding: 8 }}>Description</th>
                    <th style={{ padding: 8 }}>Modality</th>
                    <th style={{ padding: 8 }}>Slices</th>
                    <th style={{ padding: 8 }}>Type</th>
                    <th style={{ padding: 8 }}>Used for report</th>
                  </tr>
                </thead>
                <tbody>
                  {seriesInfo.map((s) => (
                    <tr key={s.series_uid} style={{
                      borderBottom: "1px solid var(--color-border-tertiary)",
                      background: s.selected ? "var(--color-background-info)" : "transparent",
                    }}>
                      <td style={{ padding: 8 }}>{s.series_description}</td>
                      <td style={{ padding: 8 }}>{s.modality}</td>
                      <td style={{ padding: 8 }}>{s.slice_count}</td>
                      <td style={{ padding: 8 }}>{s.is_scout ? "Scout / localizer" : "Diagnostic"}</td>
                      <td style={{ padding: 8 }}>{s.selected ? "Yes" : "No"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      )}

      {activeTab === "meta" && (
        <div>
          {[
            { title: "Patient", icon: "ti-user", fields: [["Name", meta.PatientName], ["ID", meta.PatientID], ["DOB", meta.PatientBirthDate], ["Sex", meta.PatientSex], ["Age", meta.PatientAge]] },
            { title: "Study", icon: "ti-stethoscope", fields: [["Study Date", meta.StudyDate], ["Description", meta.StudyDescription], ["Institution", meta.InstitutionName]] },
            { title: "Image", icon: "ti-scan", fields: [["Modality", meta.Modality], ["Body Part", meta.BodyPartExamined], ["Slice Thickness", meta.SliceThickness], ["Rows × Cols", `${meta.Rows} × ${meta.Columns}`]] },
          ].map((section) => (
            <SectionCard key={section.title} title={section.title} icon={section.icon}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "14px 24px" }}>
                {section.fields.map(([label, value]) => <Tag key={label} label={label} value={value} />)}
              </div>
            </SectionCard>
          ))}
        </div>
      )}

      {activeTab === "pixel" && (
        <div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
            {[["Min HU", stats.min], ["Max HU", stats.max], ["Mean HU", stats.mean], ["Std Dev", stats.std]].map(([label, val]) => (
              <div key={label} style={{ background: "var(--color-background-secondary)", borderRadius: "var(--border-radius-md)", padding: "14px 16px" }}>
                <p style={{ fontSize: 11, color: "var(--color-text-secondary)", textTransform: "uppercase", margin: "0 0 4px" }}>{label}</p>
                <p style={{ fontSize: 22, fontWeight: 500, margin: 0 }}>{val ?? "—"}</p>
              </div>
            ))}
          </div>
          <SectionCard title="Tissue Breakdown" icon="ti-chart-bar">
            {Object.entries(tissue).map(([name, pct]) => (
              <div key={name} style={{ marginBottom: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
                  <span>{name}</span>
                  <span style={{ color: "var(--color-text-secondary)" }}>{pct}%</span>
                </div>
                <div style={{ height: 6, background: "var(--color-background-secondary)", borderRadius: 3 }}>
                  <div style={{ height: "100%", width: `${Math.min(pct * 10, 100)}%`, background: "var(--color-text-info)", borderRadius: 3 }} />
                </div>
              </div>
            ))}
          </SectionCard>
        </div>
      )}

      {activeTab === "tags" && (
        <SectionCard title={`All DICOM Tags (${Object.keys(allTags).length})`} icon="ti-tags">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px 24px" }}>
            {Object.entries(allTags).sort(([a], [b]) => a.localeCompare(b)).map(([key, val]) => (
              <div key={key} style={{ display: "flex", gap: 8, padding: "5px 0", borderBottom: "0.5px solid var(--color-border-tertiary)" }}>
                <span style={{ fontSize: 12, color: "var(--color-text-secondary)", minWidth: 120 }}>{key}</span>
                <span style={{ fontSize: 12, wordBreak: "break-all" }}>{String(val).slice(0, 80)}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      <div style={{ textAlign: "center", marginTop: 24 }}>
        <button type="button" onClick={onReset} style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13 }}>
          <i className="ti ti-refresh" aria-hidden /> Analyze another study
        </button>
      </div>
    </div>
  );
}
