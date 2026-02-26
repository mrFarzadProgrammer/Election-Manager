import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig(({ mode }) => ({
  plugins: [react()],

  server: mode === "development"
    ? {
        port: 5173,
        host: "0.0.0.0",
        strictPort: true,

        proxy: {
          "/api": {
            target: "http://127.0.0.1:8000",
            changeOrigin: true,
          },
          "/uploads": {
            target: "http://127.0.0.1:8000",
            changeOrigin: true,
          },
        },
      }
    : undefined,

  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
}));
