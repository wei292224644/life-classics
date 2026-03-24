import { defineConfig } from "vite";
import uni from "@dcloudio/vite-plugin-uni";
import UnoCSS from "unocss/vite";

export default defineConfig({
  server: {
    port: 5174,
  },
  plugins: [
    UnoCSS({ configFile: './src/uno.config.ts' }),
    uni(),
  ],
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: '@import "uview-plus/theme.scss";',
      },
    },
    // rpx conversion: px values in UnoCSS output → rpx for miniapp compatibility
    // NOTE: postcss-rpx-transform plugin to be added after Phase 1 verification
    postcss: process.env.UNI_PLATFORM !== 'h5' ? {
      plugins: [
        // TODO: Add postcss-rpx-transform here after Phase 1 verification
        // Example: transformRpx({ viewportWidth: 750, mode: 'rpx' })
      ]
    } : undefined
  },
});
