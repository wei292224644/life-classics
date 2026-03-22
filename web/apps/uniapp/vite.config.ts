import { defineConfig } from "vite";
import uni from "@dcloudio/vite-plugin-uni";
import uviewPlus from "uview-plus/lib/config/vite";

export default defineConfig({
  plugins: [
    uni(),
    uviewPlus(),
  ],
});
