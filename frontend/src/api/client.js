const API = "";
const UPLOAD_TIMEOUT_MS = 10 * 60 * 1000;

export async function analyzeFiles(fileList) {
  const fd = new FormData();
  for (const file of fileList) {
    fd.append("files", file, file.webkitRelativePath || file.name);
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), UPLOAD_TIMEOUT_MS);

  try {
    const res = await fetch(`${API}/analyze`, {
      method: "POST",
      body: fd,
      signal: controller.signal,
    });

    if (!res.ok) {
      let detail = "Analysis failed";
      try {
        const err = await res.json();
        detail = err.detail || detail;
      } catch {
        /* ignore */
      }
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return res.json();
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error(
        "Upload timed out. For large studies (1000+ slices), zip the Images folder and use Upload .zip."
      );
    }
    if (err.message === "Failed to fetch") {
      throw new Error(
        "Could not reach the backend on port 8000. " +
        "Ensure `python run.py` is running in backend/ and was not restarted mid-upload. " +
        "For large studies (500+ slices), zip the Images folder first — it uploads faster and more reliably."
      );
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchReportJson(reportId) {
  const res = await fetch(`${API}/report/${reportId}/json`);
  if (!res.ok) throw new Error("Could not load report");
  return res.json();
}

export function reportJsonUrl(reportId) {
  return `${API}/report/${reportId}/json`;
}

export function reportPdfUrl(reportId) {
  return `${API}/report/${reportId}/pdf`;
}
