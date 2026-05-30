import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const PROXY_TIMEOUT_MS = 10 * 60 * 1000; // 10 minutes for large DICOM uploads

const proxyOptions = {
  target: "http://127.0.0.1:8000",
  changeOrigin: true,
  timeout: PROXY_TIMEOUT_MS,
  proxyTimeout: PROXY_TIMEOUT_MS,
};

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/analyze": proxyOptions,
      "/report": proxyOptions,
      "/reports": proxyOptions,
      "/health": proxyOptions,
    },
  },
});
