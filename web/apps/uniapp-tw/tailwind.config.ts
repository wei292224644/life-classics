import type { Config } from 'tailwindcss'
import { getIconCollections, iconsPlugin } from '@egoist/tailwindcss-icons'
import cssMacro from 'weapp-tailwindcss/css-macro'
import { isMp } from './platform'

export default <Config>{
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{html,js,ts,jsx,tsx,vue}'],
  theme: {
    extend: {
      colors: {
        // shadcn 语义变量命名
        'background': 'var(--color-background)',
        'foreground': 'var(--color-foreground)',
        'card': 'var(--color-card)',
        'card-foreground': 'var(--color-card-foreground)',
        'primary': 'var(--color-primary)',
        'primary-foreground': 'var(--color-primary-foreground)',
        'secondary': 'var(--color-secondary)',
        'secondary-foreground': 'var(--color-secondary-foreground)',
        'muted': 'var(--color-muted)',
        'muted-foreground': 'var(--color-muted-foreground)',
        'accent': 'var(--color-accent)',
        'accent-foreground': 'var(--color-accent-foreground)',
        'destructive': 'var(--color-destructive)',
        'destructive-foreground': 'var(--color-destructive-foreground)',
        'border': 'var(--color-border)',
        'input': 'var(--color-input)',
        'ring': 'var(--color-ring)',

        // 风险色
        'risk-t4': 'var(--color-risk-t4)',
        'risk-t3': 'var(--color-risk-t3)',
        'risk-t2': 'var(--color-risk-t2)',
        'risk-t1': 'var(--color-risk-t1)',
        'risk-t0': 'var(--color-risk-t0)',
        'risk-unknown': 'var(--color-risk-unknown)',

        // 复杂 component token
        'bottom-bar-bg': 'var(--bottom-bar-bg)',
        'bottom-bar-border': 'var(--bottom-bar-border)',
        'header-scrolled-bg': 'var(--header-scrolled-bg)',
        'ai-label-bg': 'var(--ai-label-bg)',
        'nutrition-bg': 'var(--nutrition-bg)',
        'nutrition-border': 'var(--nutrition-border)',
        'nutrition-glow': 'var(--nutrition-glow)',
        'status-bar-bg': 'var(--status-bar-bg)',
        'status-bar-text': 'var(--status-bar-text)',
        'banner-bg': 'var(--banner-bg)',
        'banner-label': 'var(--banner-label)',
        'banner-badge-bg': 'var(--banner-badge-bg)',
        'banner-badge-border': 'var(--banner-badge-border)',
        'banner-badge-shadow': 'var(--banner-badge-shadow)',
        'accent-glow': 'var(--accent-glow)',

        // accent pink 色系
        'accent-pink-light': 'var(--accent-pink-light)',
        'accent-pink': 'var(--accent-pink)',

        // 调色板色 (SectionHeader icon backgrounds)
        'palette-blue-500': 'var(--palette-blue-500)',
        'palette-purple-500': 'var(--palette-purple-500)',
        'palette-green-500': 'var(--palette-green-500)',
        'palette-orange-500': 'var(--palette-orange-500)',
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
      },
      boxShadow: {
        sm: 'var(--shadow-sm)',
      },
    },
  },
  plugins: [
    cssMacro({
      variantsMap: {
        'wx': 'MP-WEIXIN',
        '-wx': { value: 'MP-WEIXIN', negative: true },
      },
    }),
    iconsPlugin({
      collections: getIconCollections(['svg-spinners', 'mdi']),
    }),
  ],
  corePlugins: {
    preflight: !isMp,
    container: !isMp,
  },
}
