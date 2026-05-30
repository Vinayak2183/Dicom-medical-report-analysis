export const Tag = ({ label, value }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
    <span style={{ fontSize: 11, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</span>
    <span style={{ fontSize: 14, fontWeight: 500, color: "var(--color-text-primary)" }}>{value || "—"}</span>
  </div>
);

export const SectionCard = ({ title, icon, children, accent }) => (
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
  String(text || "")
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/\*(.*?)\*/g, "$1")
    .replace(/#{1,3}\s*/g, "")
    .replace(/^\s*[-•]\s*/gm, "• ");

export const AiBlock = ({ label, text, highlight }) => {
  if (!text) return null;
  const clean = stripMarkdown(text);
  return (
    <div style={{ marginBottom: 16 }}>
      {label && (
        <p style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>{label}</p>
      )}
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

export const Disclaimer = () => (
  <div style={{
    background: "var(--color-background-danger)",
    border: "0.5px solid var(--color-border-danger)",
    borderRadius: "var(--border-radius-md)",
    padding: "10px 14px",
    fontSize: 12,
    color: "var(--color-text-danger)",
    marginBottom: 16,
    display: "flex", alignItems: "flex-start", gap: 8,
  }}>
    <i className="ti ti-alert-triangle" style={{ fontSize: 15, marginTop: 2 }} aria-hidden />
    <span>
      AI-generated for research and education only. <strong>Not a clinical diagnosis.</strong>{" "}
      A qualified radiologist must review all findings before any medical decision.
    </span>
  </div>
);
