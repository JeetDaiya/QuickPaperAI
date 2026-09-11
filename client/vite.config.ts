import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import tsconfigPaths from "vite-tsconfig-paths";
import { tanstackRouter } from "@tanstack/router-plugin/vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");

  return {
    plugins: [tsconfigPaths(), tanstackRouter({ target: "react", autoCodeSplitting: true }), react(), tailwindcss()],
    server: {
      // The backend's dev CORS allowlist only accepts 5173/8080/3000/8000 (see GOTCHAS).
      // strictPort makes an occupied port a startup error instead of a silent hop to 5174,
      // where every request would fail with a CORS error that looks like the backend is down.
      port: Number(env.VITE_DEV_PORT) || 8080,
      strictPort: true,
    },
  };
});
