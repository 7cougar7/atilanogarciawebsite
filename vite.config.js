import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

// Vite builds React islands into Django's static tree at mainwebsite/static/dist/.
// The {% vite_asset %} template tag (mainwebsite/templatetags/vite.py) reads
// dist/.vite/manifest.json and wraps each entry in {% static %} so Django's
// ManifestStaticFilesStorage hashing still applies on top of Vite's hashing.
//
// inlineDynamicImports + single entry => one JS bundle with no inter-chunk imports,
// so Django re-hashing the filenames can't break internal references.
export default defineConfig({
  plugins: [react()],
  root: resolve(__dirname, "frontend"),
  base: "/static/dist/",
  build: {
    manifest: true,
    outDir: resolve(__dirname, "mainwebsite/static/dist"),
    emptyOutDir: true,
    rollupOptions: {
      input: resolve(__dirname, "frontend/src/main.jsx"),
      output: {
        inlineDynamicImports: true,
        entryFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
  // Used only when running `npm run dev` alongside Django with VITE_DEV_MODE=true.
  server: {
    origin: "http://localhost:5173",
  },
});
