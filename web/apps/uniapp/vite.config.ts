import { defineConfig } from "vite";
import uni from "@dcloudio/vite-plugin-uni";

export default defineConfig({
  server: {
    port: 5174,
  },
  plugins: [uni()],
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: '@import "uview-plus/theme.scss";',
      },
    },
  },
});
