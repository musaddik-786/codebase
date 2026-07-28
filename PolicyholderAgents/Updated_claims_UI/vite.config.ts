import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";
import { policyDetailsApi } from "./vite-plugins/policy-details";
import { voiceExtractionApi } from "./vite-plugins/voice-extraction";
import { fnolSubmissionApi } from "./vite-plugins/fnol-submission";
import { claimsApi } from "./vite-plugins/claims";
import { claimJourneyApi } from "./vite-plugins/claim-journey";
import { documentsApi } from "./vite-plugins/documents";
import { claimInsightsApi } from "./vite-plugins/claim-insights";

export default defineConfig(({ mode }) => {
  // Load ALL .env vars (empty prefix) into process.env so that Vite plugin
  // server-side code (db.ts getPool(), etc.) can read AZURE_DATABASE_URL.
  // Vite only injects VITE_-prefixed vars into import.meta.env; non-prefixed
  // vars like AZURE_DATABASE_URL are invisible to plugins without this step.
  const env = loadEnv(mode, process.cwd(), "");
  Object.assign(process.env, env);

  return {
  base: "/",
  plugins: [
    react(),
    tailwindcss(),
    policyDetailsApi(),
    voiceExtractionApi(),
    fnolSubmissionApi(),
    claimsApi(),
    claimJourneyApi(),
    documentsApi(),
    claimInsightsApi(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "src"),
      "@assets": path.resolve(import.meta.dirname, "attached_assets"),
    },
    dedupe: ["react", "react-dom"],
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  server: {
    host: "0.0.0.0",
    port: Number(process.env.PORT) || 7133,
    allowedHosts: true,
    watch: {
      ignored: ["**/.local/**", "**/dist/**", "**/.git/**"],
    },
  },
  preview: {
    host: "0.0.0.0",
    port: Number(process.env.PORT) || 4173,
    allowedHosts: true,
  },
  };
});
