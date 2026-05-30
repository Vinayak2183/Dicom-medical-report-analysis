export const STATUS = {
  idle: { label: "Drop DICOM folder, files, or zip", icon: "ti-folder-up", color: "var(--color-text-secondary)" },
  uploading: { label: "Uploading...", icon: "ti-loader-2", color: "var(--color-text-info)", spin: true },
  analyzing: { label: "Building volume & AI analysis...", icon: "ti-brain", color: "var(--color-text-info)", spin: true },
  done: { label: "Report ready", icon: "ti-circle-check", color: "var(--color-text-success)" },
  error: { label: "Something went wrong", icon: "ti-alert-circle", color: "var(--color-text-danger)" },
};

export const STEPS = [
  "Uploading files",
  "Grouping DICOM series",
  "Stacking 3D volume",
  "AI multi-slice analysis",
  "Building PDF report",
];

export const ACCEPT = ".dcm,.dicom,.dic,.ima,.zip,application/dicom";
