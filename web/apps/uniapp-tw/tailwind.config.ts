import type { Config } from "tailwindcss";
import { getIconCollections, iconsPlugin } from "@egoist/tailwindcss-icons";
import cssMacro from "weapp-tailwindcss/css-macro";
import { isMp } from "./platform";

export default <Config>{
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{html,js,ts,jsx,tsx,vue}"],
  safelist: [
    // 风险色全集：所有前缀 × 所有等级 × 所有标准透明度（含不带透明度）
    // variants 覆盖常用交互与暗色模式，动态拼接 risk class 时无需担心扫描问题
    {
      pattern:
        /^(bg|text|border|shadow|ring|outline|fill|stroke|from|to|via)-risk-(t0|t1|t2|t3|t4|unknown)(\/([0-9]|[1-9][0-9]|100))?$/,
      variants: [
        "hover",
        "active",
        "focus",
        "dark",
        "group-hover",
        "group-active",
      ],
    },
  ],
  theme: {
    extend: {
      colors: {
        root: "var(--root)",
        // shadcn 语义变量命名
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: "var(--card)",
        "card-foreground": "var(--card-foreground)",
        primary: "var(--primary)",
        "primary-foreground": "var(--primary-foreground)",
        secondary: "var(--secondary)",
        "secondary-foreground": "var(--secondary-foreground)",
        muted: "var(--muted)",
        "muted-foreground": "var(--muted-foreground)",
        accent: "var(--accent)",
        "accent-foreground": "var(--accent-foreground)",
        destructive: "var(--destructive)",
        "destructive-foreground": "var(--destructive-foreground)",
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
        "chart-1": "var(--chart-1)",
        "chart-2": "var(--chart-2)",
        "chart-3": "var(--chart-3)",
        "chart-4": "var(--chart-4)",
        "chart-5": "var(--chart-5)",
        radius: "var(--radius)",
        sidebar: "var(--sidebar)",
        "sidebar-foreground": "var(--sidebar-foreground)",
        "sidebar-primary": "var(--sidebar-primary)",
        "sidebar-primary-foreground": "var(--sidebar-primary-foreground)",
        "sidebar-accent": "var(--sidebar-accent)",
        "sidebar-accent-foreground": "var(--sidebar-accent-foreground)",
        "sidebar-border": "var(--sidebar-border)",
        "sidebar-ring": "var(--sidebar-ring)",

        risk: {
          t4: "oklch(50% 0.22 25 / <alpha-value>)",
          t3: "oklch(55% 0.2 50 / <alpha-value>)",
          t2: "oklch(60% 0.18 85 / <alpha-value>)",
          t1: "oklch(65% 0.16 145 / <alpha-value>)",
          t0: "oklch(55% 0.15 145 / <alpha-value>)",
          // 允许 `bg-risk-unknown/50` 这类透明度修饰符
          unknown: "oklch(60% 0.01 265 / <alpha-value>)",
        },

        // 复杂 component token
        "bottom-bar-bg": "var(--bottom-bar-bg)",
        "bottom-bar-border": "var(--bottom-bar-border)",
        "header-scrolled-bg": "var(--header-scrolled-bg)",
        "ai-label-bg": "var(--ai-label-bg)",
        "nutrition-bg": "var(--nutrition-bg)",
        "nutrition-border": "var(--nutrition-border)",
        "nutrition-glow": "var(--nutrition-glow)",
        "status-bar-bg": "var(--status-bar-bg)",
        "status-bar-text": "var(--status-bar-text)",
        "banner-bg": "var(--banner-bg)",
        "banner-label": "var(--banner-label)",
        "banner-badge-bg": "var(--banner-badge-bg)",
        "banner-badge-border": "var(--banner-badge-border)",
        "banner-badge-shadow": "var(--banner-badge-shadow)",
        "accent-glow": "var(--accent-glow)",

        // accent pink 色系
        "accent-pink-light": "var(--accent-pink-light)",
        "accent-pink": "var(--accent-pink)",

        // 调色板色 (SectionHeader icon backgrounds)
        "palette-blue-500": "var(--palette-blue-500)",
        "palette-purple-500": "var(--palette-purple-500)",
        "palette-green-500": "var(--palette-green-500)",
        "palette-orange-500": "var(--palette-orange-500)",
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
      },
      spacing: {
        topbar: "var(--topbar-height)",
      },
    },
  },
  plugins: [
    cssMacro({
      variantsMap: {
        wx: "MP-WEIXIN",
        "-wx": { value: "MP-WEIXIN", negative: true },
      },
    }),
    iconsPlugin({
      collections: getIconCollections(["svg-spinners", "mdi"]),
    }),
  ],
  corePlugins: {
    preflight: !isMp,
    container: !isMp,
  },
};
