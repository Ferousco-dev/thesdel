import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon-32.png"],
      manifest: {
        name: "Thesdel",
        short_name: "Thesdel",
        description:
          "Your class timetable, then Litheral builds your study time and your whole week around it.",
        theme_color: "#121212",
        background_color: "#121212",
        display: "standalone",
        start_url: "/timetable",
        icons: [
          { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
          {
            src: "/icon-maskable-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        // Never cache API responses in the service worker's precache/runtime
        // strategy by default — the app's own tokenStore/timetable cache
        // (see frontend/AGENTS.md, docs/ARCHITECTURE.md offline-first notes)
        // already owns offline behavior for timetable data. A blanket SW
        // cache here would risk silently serving stale auth/API responses.
        navigateFallbackDenylist: [/^\/v1\//],
      },
    }),
  ],
  server: {
    port: 5173,
  },
});
