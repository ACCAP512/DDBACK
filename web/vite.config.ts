import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Drawback Broker OS SPA. In dev, the broker-OS FastAPI backend runs on :8001
// (`make server`) and we proxy /api to it; in production that same process serves
// this build from web/dist, so relative /api calls resolve against the same origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
