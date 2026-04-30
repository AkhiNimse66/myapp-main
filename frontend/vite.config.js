import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    // .jsx before .js so extensionless imports (e.g. "./App") find App.jsx first.
    // The old .js stubs contain only comments.
    extensions: [".mjs", ".jsx", ".js", ".ts", ".tsx", ".json"],
  },
  optimizeDeps: {
    // Pre-bundler needs to know .js files may contain JSX (legacy CRA convention).
    esbuildOptions: {
      loader: { ".js": "jsx" },
    },
  },
  server: {
    port: 3000,
    open: true,
  },
});
