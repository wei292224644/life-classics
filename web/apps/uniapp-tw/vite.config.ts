import uni from "@dcloudio/vite-plugin-uni";
import { defineConfig } from "vite";
import { UnifiedViteWeappTailwindcssPlugin } from "weapp-tailwindcss/vite";
import { WeappTailwindcssDisabled } from "./platform";
import postcssPlugins from "./postcss.config";
import path from "node:path";

// https://vitejs.dev/config/
export default defineConfig(async () => {
  // 新版本的 unplugin-auto-import 改成了只有 esm 格式的产物，而 uni-app 目前必须 cjs 格式
  // 所以需要改成动态 import 的写法来进行引入
  // 详见 https://github.com/sonofmagic/uni-app-vite-vue3-tailwind-vscode-template/issues/29
  const { default: AutoImport } = await import("unplugin-auto-import/vite");
  return {
    // 让该 uniapp 子应用也读取仓库 web/ 目录的 .env
    // 当前文件在 web/apps/uniapp-tw/vite.config.ts
    // 所以 ../.. 对应到 web/
    envDir: path.resolve(__dirname, "../.."),
    server: {
      port: 5175,
      hmr: {
        overlay: true,
      },
    },
    // uvtw 一定要放在 uni 后面
    plugins: [
      uni(),
      UnifiedViteWeappTailwindcssPlugin({
        rem2rpx: true,
        disabled: WeappTailwindcssDisabled,
        cache: false,
      }),
      AutoImport({
        imports: ["vue", "uni-app", "pinia"],
        dts: "./src/auto-imports.d.ts",
        eslintrc: {
          enabled: true,
        },
      }),
    ],
    // 内联 postcss 注册 tailwindcss
    css: {
      postcss: {
        plugins: postcssPlugins,
      },
      // https://vitejs.dev/config/shared-options.html#css-preprocessoroptions
      preprocessorOptions: {
        scss: {
          silenceDeprecations: ["legacy-js-api"],
        },
      },
    },
  };
});
