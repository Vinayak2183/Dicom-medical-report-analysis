import { useRef } from "react";
import { ACCEPT, STATUS, STEPS } from "../constants.js";

export default function DropZone({ status, files, error, onFiles, onReset }) {
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const zipInputRef = useRef(null);
  const st = STATUS[status];
  const busy = status === "uploading" || status === "analyzing";

  const totalKb = files.reduce((sum, f) => sum + f.size, 0) / 1024;

  return (
    <div style={{ marginBottom: 24 }}>
      <div
        style={{
          border: "1.5px dashed var(--color-border-secondary)",
          borderRadius: "var(--border-radius-lg)",
          background: "var(--color-background-secondary)",
          padding: "28px 24px",
          textAlign: "center",
        }}
      >
        <i className={`ti ${st.icon}${st.spin ? " spin" : ""}`}
          style={{ fontSize: 32, color: st.color, display: "block", marginBottom: 10 }} aria-hidden />
        <p style={{ margin: 0, fontWeight: 500, color: "var(--color-text-primary)", fontSize: 15 }}>{st.label}</p>

        {status === "idle" && (
          <>
            <p style={{ margin: "8px 0 16px", fontSize: 13, color: "var(--color-text-secondary)" }}>
              Hospital CD format supported — upload the <code>Images</code> folder, or zip it first for large studies (1000+ slices)
            </p>
            <div style={{ display: "flex", gap: 8, justifyContent: "center", flexWrap: "wrap" }}>
              <button type="button" onClick={() => folderInputRef.current?.click()} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                <i className="ti ti-folder" aria-hidden /> Select folder
              </button>
              <button type="button" onClick={() => fileInputRef.current?.click()} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                <i className="ti ti-files" aria-hidden /> Select files
              </button>
              <button type="button" onClick={() => zipInputRef.current?.click()} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                <i className="ti ti-file-zip" aria-hidden /> Upload .zip
              </button>
            </div>
          </>
        )}

        {files.length > 0 && status !== "idle" && (
          <p style={{ margin: "8px 0 0", fontSize: 12, color: "var(--color-text-secondary)" }}>
            {files.length} file{files.length !== 1 ? "s" : ""} · {(totalKb / 1024).toFixed(1)} MB
            {files.length === 1 ? ` · ${files[0].name}` : ""}
          </p>
        )}

        {status === "error" && (
          <div style={{ marginTop: 12 }}>
            <p style={{ margin: "0 0 8px", fontSize: 13, color: "var(--color-text-danger)" }}>{error}</p>
            <button type="button" onClick={onReset}>Try again</button>
          </div>
        )}
      </div>

      {(status === "uploading" || status === "analyzing") && (
        <div style={{ display: "flex", gap: 8, marginTop: 16, justifyContent: "center", flexWrap: "wrap" }}>
          {STEPS.map((step, i) => {
            const active = (status === "uploading" && i === 0) || (status === "analyzing" && i >= 1);
            return (
              <div key={step} style={{
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

      <input ref={folderInputRef} type="file" webkitdirectory="" directory="" multiple style={{ display: "none" }}
        onChange={(e) => e.target.files?.length && onFiles(e.target.files)} />
      <input ref={fileInputRef} type="file" accept={ACCEPT} multiple style={{ display: "none" }}
        onChange={(e) => e.target.files?.length && onFiles(e.target.files)} />
      <input ref={zipInputRef} type="file" accept=".zip,application/zip" style={{ display: "none" }}
        onChange={(e) => e.target.files?.[0] && onFiles([e.target.files[0]])} />
    </div>
  );
}
