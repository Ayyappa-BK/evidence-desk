import { defineConfig } from "vite";
export default defineConfig({
  server: { port: 8413, proxy: { "/api": "http://127.0.0.1:8313" } },
});
