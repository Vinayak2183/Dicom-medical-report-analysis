import { useCallback, useState } from "react";
import { analyzeFiles, fetchReportJson } from "../api/client.js";

export function useAnalyze() {
  const [status, setStatus] = useState("idle");
  const [files, setFiles] = useState([]);
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");

  const reset = useCallback(() => {
    setStatus("idle");
    setFiles([]);
    setReport(null);
    setError("");
  }, []);

  const processFiles = useCallback(async (fileList) => {
    const list = Array.from(fileList).filter((f) => {
      const n = f.name.toLowerCase();
      return (
        n.endsWith(".dcm") ||
        n.endsWith(".dicom") ||
        n.endsWith(".dic") ||
        n.endsWith(".ima") ||
        n.endsWith(".zip") ||
        !n.includes(".")
      );
    });

    if (!list.length) {
      setError("No DICOM files found. Select .dic/.dcm files, a folder, or a .zip archive.");
      setStatus("error");
      return;
    }

    setFiles(list);
    setError("");
    setReport(null);
    setStatus("uploading");

    try {
      setStatus("analyzing");
      const data = await analyzeFiles(list);
      const fullReport = await fetchReportJson(data.report_id);
      setReport({ ...data, full: fullReport });
      setStatus("done");
    } catch (e) {
      setError(e.message);
      setStatus("error");
    }
  }, []);

  return { status, files, report, error, processFiles, reset, setError, setStatus };
}
