import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Drawback Engine SPA. In dev, the FastAPI backend runs on :8000 and we proxy
// /api to it; in production the same FastAPI process serves this build from
// web/dist, so relative /api calls resolve against the same origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
