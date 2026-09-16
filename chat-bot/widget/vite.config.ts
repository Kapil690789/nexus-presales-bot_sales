import { defineConfig } from "vite";

export default defineConfig({
  build: {
    lib: {
      entry: "src/index.ts",
      name: "DevConsultAdvisor",
      fileName: () => "consultant.js",
      formats: ["iife"],
    },
    outDir: "dist",
    emptyOutDir: true,
    cssCodeSplit: false,
  },
});
