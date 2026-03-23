import { defineConfig, presetUno, presetIcons, presetAttributify } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),
    presetAttributify(),
    presetIcons({
      scale: 1.2,
      extraProperties: {
        'display': 'inline-block',
        'vertical-align': 'middle'
      }
    })
  ],

  theme: {
    colors: {
      gray: {
        50: 'var(--palette-gray-50)',
        100: 'var(--palette-gray-100)',
        200: 'var(--palette-gray-200)',
        300: 'var(--palette-gray-300)',
        400: 'var(--palette-gray-400)',
        500: 'var(--palette-gray-500)',
        600: 'var(--palette-gray-600)',
        700: 'var(--palette-gray-700)',
        800: 'var(--palette-gray-800)',
        900: 'var(--palette-gray-900)',
      },
      red: {
        50: 'var(--palette-red-50)',
        100: 'var(--palette-red-100)',
        200: 'var(--palette-red-200)',
        300: 'var(--palette-red-300)',
        400: 'var(--palette-red-400)',
        500: 'var(--palette-red-500)',
        600: 'var(--palette-red-600)',
        700: 'var(--palette-red-700)',
        800: 'var(--palette-red-800)',
        900: 'var(--palette-red-900)',
      },
      orange: {
        50: 'var(--palette-orange-50)',
        100: 'var(--palette-orange-100)',
        200: 'var(--palette-orange-200)',
        300: 'var(--palette-orange-300)',
        400: 'var(--palette-orange-400)',
        500: 'var(--palette-orange-500)',
        600: 'var(--palette-orange-600)',
        700: 'var(--palette-orange-700)',
        800: 'var(--palette-orange-800)',
        900: 'var(--palette-orange-900)',
      },
      yellow: {
        50: 'var(--palette-yellow-50)',
        100: 'var(--palette-yellow-100)',
        200: 'var(--palette-yellow-200)',
        300: 'var(--palette-yellow-300)',
        400: 'var(--palette-yellow-400)',
        500: 'var(--palette-yellow-500)',
        600: 'var(--palette-yellow-600)',
        700: 'var(--palette-yellow-700)',
        800: 'var(--palette-yellow-800)',
        900: 'var(--palette-yellow-900)',
      },
      green: {
        50: 'var(--palette-green-50)',
        100: 'var(--palette-green-100)',
        200: 'var(--palette-green-200)',
        300: 'var(--palette-green-300)',
        400: 'var(--palette-green-400)',
        500: 'var(--palette-green-500)',
        600: 'var(--palette-green-600)',
        700: 'var(--palette-green-700)',
        800: 'var(--palette-green-800)',
        900: 'var(--palette-green-900)',
        950: 'var(--palette-green-950)',
      },
      purple: {
        50: 'var(--palette-purple-50)',
        100: 'var(--palette-purple-100)',
        300: 'var(--palette-purple-300)',
        400: 'var(--palette-purple-400)',
        500: 'var(--palette-purple-500)',
        600: 'var(--palette-purple-600)',
        700: 'var(--palette-purple-700)',
        800: 'var(--palette-purple-800)',
      },
      blue: {
        50: 'var(--palette-blue-50)',
        100: 'var(--palette-blue-100)',
        300: 'var(--palette-blue-300)',
        400: 'var(--palette-blue-400)',
        500: 'var(--palette-blue-500)',
        600: 'var(--palette-blue-600)',
      },
      pink: {
        300: 'var(--palette-pink-300)',
        400: 'var(--palette-pink-400)',
        500: 'var(--palette-pink-500)',
        600: 'var(--palette-pink-600)',
      },
      accent: {
        DEFAULT: 'var(--accent)',
        light: 'var(--accent-light)',
      },
      risk: {
        t4: 'var(--risk-t4)',
        t3: 'var(--risk-t3)',
        t2: 'var(--risk-t2)',
        t1: 'var(--risk-t1)',
        t0: 'var(--risk-t0)',
        unknown: 'var(--risk-unknown)',
      }
    },
    borderRadius: {
      sm: 'var(--radius-sm)',
      md: 'var(--radius-md)',
      lg: 'var(--radius-lg)',
      xl: 'var(--radius-xl)',
      full: 'var(--radius-full)',
    }
  },

  safelist: [
    'risk-critical', 'risk-high', 'risk-medium', 'risk-low', 'risk-safe', 'risk-unknown',
    'icon-bg-blue', 'icon-bg-red', 'icon-bg-purple', 'icon-bg-green', 'icon-bg-orange',
    'chip-func', 'chip-warn', 'chip-neu',
    'list-item-icon', 'icon-x', 'icon-check-green', 'icon-check-yellow',
    'risk-med'
  ],

  shortcuts: {
    'card': 'bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl shadow-[var(--shadow-sm)]',
    'section-title': 'text-[var(--text-primary)] font-semibold text-lg',
    'icon-wrap': 'w-[40rpx] h-[40rpx] rounded-[var(--space-3)] flex items-center justify-center',
  }
})
