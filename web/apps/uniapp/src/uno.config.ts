import { defineConfig, presetIcons } from 'unocss'
import presetUni from 'unocss-preset-uni'

export default defineConfig({
  presets: [
    presetUni(),
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
      // Palette colors (for use as bg-red-500, text-gray-900, etc.)
      gray: { 50:'#f9fafb',100:'#f3f4f6',200:'#e5e7eb',300:'#d1d5db',400:'#9ca3af',500:'#6b7280',600:'#4b5563',700:'#374151',800:'#1f2937',900:'#111827' },
      red: { 50:'#fef2f2',100:'#fee2e2',200:'#fecaca',300:'#fca5a5',400:'#f87171',500:'#dc2626',600:'#b91c1c',700:'#991b1b',800:'#7f1d1d',900:'#450a0a' },
      orange: { 50:'#fff7ed',100:'#ffedd5',200:'#fed7aa',300:'#fdba74',400:'#fb923c',500:'#f97316',600:'#ea580c',700:'#c2410c',800:'#9a3412',900:'#431407' },
      yellow: { 50:'#fefce8',100:'#fef9c3',200:'#fef08a',300:'#fde047',400:'#facc15',500:'#eab308',600:'#ca8a04',700:'#a16207',800:'#713f12',900:'#422006' },
      green: { 50:'#f0fdf4',100:'#dcfce7',200:'#bbf7d0',300:'#86efac',400:'#4ade80',500:'#22c55e',600:'#16a34a',700:'#15803d',800:'#14532d',900:'#052e16',950:'#022c22' },
      purple: { 50:'#f5f3ff',100:'#ede9fe',300:'#c4b5fd',400:'#a78bfa',500:'#8b5cf6',600:'#7c3aed',700:'#6d28d9',800:'#4c1d95' },
      blue: { 50:'#eff6ff',100:'#dbeafe',300:'#93c5fd',400:'#60a5fa',500:'#3b82f6',600:'#2563eb' },
      pink: { 50:'#fdf2f8',100:'#fce7f3',200:'#fbcfe8',300:'#f9a8d4',400:'#f472b6',500:'#ec4899',600:'#db2777' },
    },
  },

  shortcuts: {
    // ── Base components ──────────────────────────────────────
    'card': 'bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl shadow-[var(--shadow-sm)]',
    'section-title': 'text-[var(--text-primary)] font-semibold text-lg',
    'icon-wrap': 'w-[40rpx] h-[40rpx] rounded-[var(--radius-sm)] flex items-center justify-center',

    // ── AI label ─────────────────────────────────────────────
    'ai-label': 'text-[20rpx] font-bold px-[12rpx] py-[4rpx] rounded-[24rpx] bg-[var(--ai-label-bg)] text-white',

    // ── Icon backgrounds (SectionHeader) ────────────────────
    'icon-bg-blue':   'bg-[color-mix(in_oklch,#3b82f6_12%,transparent)] text-[#3b82f6]',
    'icon-bg-red':    'bg-[color-mix(in_oklch,var(--risk-t4)_12%,transparent)] text-[var(--risk-t4)]',
    'icon-bg-purple': 'bg-[color-mix(in_oklch,#8b5cf6_12%,transparent)] text-[#8b5cf6]',
    'icon-bg-green':  'bg-[color-mix(in_oklch,#22c55e_12%,transparent)] text-[#22c55e]',
    'icon-bg-orange': 'bg-[color-mix(in_oklch,var(--risk-t3)_12%,transparent)] text-[var(--risk-t3)]',

    // ── Info chips (InfoChip.vue) ────────────────────────────
    'chip-risk':    'bg-[color-mix(in_oklch,var(--risk-t4)_12%,transparent)] text-[var(--risk-t4)] border border-[color-mix(in_oklch,var(--risk-t4)_20%,transparent)]',
    'chip-warn':    'bg-[color-mix(in_oklch,var(--risk-t2)_10%,transparent)] text-[var(--risk-t2)] border border-[color-mix(in_oklch,var(--risk-t2)_20%,transparent)]',
    'chip-neutral': 'bg-[var(--bg-card-hover)] text-[var(--text-secondary)]',

    // ── Risk tags (RiskTag.vue, AnalysisCard.vue) ────────────
    'risktag-t4':      'bg-[color-mix(in_oklch,var(--risk-t4)_15%,transparent)] text-[var(--risk-t4)]',
    'risktag-t3':      'bg-[color-mix(in_oklch,var(--risk-t3)_15%,transparent)] text-[var(--risk-t3)]',
    'risktag-t2':      'bg-[color-mix(in_oklch,var(--risk-t2)_15%,transparent)] text-[var(--risk-t2)]',
    'risktag-t1':      'bg-[color-mix(in_oklch,var(--risk-t1)_15%,transparent)] text-[var(--risk-t1)]',
    'risktag-t0':      'bg-[color-mix(in_oklch,var(--risk-t0)_15%,transparent)] text-[var(--risk-t0)]',
    'risktag-unknown': 'bg-[color-mix(in_oklch,var(--risk-unknown)_15%,transparent)] text-[var(--risk-unknown)]',

    // ── Risk group containers (IngredientSection.vue) ────────
    'risk-group-t4':      'bg-[color-mix(in_oklch,var(--risk-t4)_8%,transparent)] border border-[color-mix(in_oklch,var(--risk-t4)_25%,transparent)]',
    'risk-group-t3':      'bg-[color-mix(in_oklch,var(--risk-t3)_8%,transparent)] border border-[color-mix(in_oklch,var(--risk-t3)_25%,transparent)]',
    'risk-group-t2':      'bg-[color-mix(in_oklch,var(--risk-t2)_8%,transparent)] border border-[color-mix(in_oklch,var(--risk-t2)_25%,transparent)]',
    'risk-group-t1':      'bg-[color-mix(in_oklch,var(--risk-t1)_8%,transparent)] border border-[color-mix(in_oklch,var(--risk-t1)_25%,transparent)]',
    'risk-group-t0':      'bg-[color-mix(in_oklch,var(--risk-t0)_8%,transparent)] border border-[color-mix(in_oklch,var(--risk-t0)_25%,transparent)]',
    'risk-group-unknown': 'bg-[var(--bg-card-hover)] border border-[var(--border-color)]',

    // ── Risk reason tags (IngredientSection.vue) ─────────────
    'risk-reason-t4':      'text-[var(--risk-t4)] bg-[color-mix(in_oklch,var(--risk-t4)_12%,transparent)]',
    'risk-reason-t3':      'text-[var(--risk-t3)] bg-[color-mix(in_oklch,var(--risk-t3)_12%,transparent)]',
    'risk-reason-t2':      'text-[var(--risk-t2)] bg-[color-mix(in_oklch,var(--risk-t2)_12%,transparent)]',
    'risk-reason-t1':      'text-[var(--risk-t1)] bg-[color-mix(in_oklch,var(--risk-t1)_12%,transparent)]',
    'risk-reason-t0':      'text-[var(--risk-t0)] bg-[color-mix(in_oklch,var(--risk-t0)_12%,transparent)]',
    'risk-reason-unknown': 'text-[var(--risk-unknown)] bg-[color-mix(in_oklch,var(--risk-unknown)_12%,transparent)]',

    // ── List item icons (ListItem.vue) ───────────────────────
    'icon-x':            'bg-[color-mix(in_oklch,var(--risk-t4)_12%,transparent)] text-[var(--risk-t4)]',
    'icon-check-green':  'bg-[color-mix(in_oklch,var(--risk-t0)_12%,transparent)] text-[var(--risk-t0)]',
    'icon-check-yellow': 'bg-[color-mix(in_oklch,var(--risk-t2)_12%,transparent)] text-[var(--risk-t2)]',

    // ── Transitions ──────────────────────────────────────────
    'transition-spring': 'transition-all duration-200 ease-[cubic-bezier(0.34,1.56,0.64,1)]',
    'transition-spring-slow': 'transition-all duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)]',
    'transition-spring-400': 'transition-all duration-400 ease-[cubic-bezier(0.34,1.56,0.64,1)]',

    // ── Buttons ──────────────────────────────────────────────
    'btn-primary':   'bg-gradient-to-br from-[var(--accent-light)] to-[var(--accent)] text-white shadow-[0_4rpx_20rpx_color-mix(in_oklch,var(--accent)_30%,transparent)] active:scale-97 disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-secondary': 'bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)] active:bg-[var(--bg-card-hover)] disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-ghost':     'bg-transparent text-[var(--text-primary)] active:bg-[color-mix(in_oklch,var(--text-primary)_8%,transparent)] disabled:opacity-50 disabled:cursor-not-allowed',

    // ── Risk badge (RiskBadge.vue) ───────────────────────────
    'risk-badge-critical': 'bg-[color-mix(in_oklch,var(--risk-t4)_15%,transparent)] text-[var(--risk-t4)]',
    'risk-badge-high':     'bg-[color-mix(in_oklch,var(--risk-t3)_15%,transparent)] text-[var(--risk-t3)]',
    'risk-badge-medium':   'bg-[color-mix(in_oklch,var(--risk-t2)_15%,transparent)] text-[var(--risk-t2)]',
    'risk-badge-low':      'bg-[color-mix(in_oklch,var(--risk-t1)_15%,transparent)] text-[var(--risk-t1)]',
    'risk-badge-unknown':  'bg-[color-mix(in_oklch,var(--risk-unknown)_15%,transparent)] text-[var(--risk-unknown)]',

    // ── Index page ───────────────────────────────────────────
    'scan-count-badge': 'bg-[color-mix(in_oklch,var(--risk-t4)_10%,transparent)] text-[var(--risk-t4)] text-[20rpx] font-bold px-[12rpx] py-[4rpx] rounded-full',
  },

  safelist: [
    // Dynamic risk classes (used via template string interpolation)
    'risk-group-t4', 'risk-group-t3', 'risk-group-t2', 'risk-group-t1', 'risk-group-t0', 'risk-group-unknown',
    'risk-reason-t4', 'risk-reason-t3', 'risk-reason-t2', 'risk-reason-t1', 'risk-reason-t0', 'risk-reason-unknown',
    'risktag-t4', 'risktag-t3', 'risktag-t2', 'risktag-t1', 'risktag-t0', 'risktag-unknown',
    'icon-x', 'icon-check-green', 'icon-check-yellow',
    'icon-bg-blue', 'icon-bg-red', 'icon-bg-purple', 'icon-bg-green', 'icon-bg-orange',
    'chip-risk', 'chip-warn', 'chip-neutral',
    'risk-badge-critical', 'risk-badge-high', 'risk-badge-medium', 'risk-badge-low', 'risk-badge-unknown',
    'risk-critical', 'risk-high', 'risk-medium', 'risk-low', 'risk-safe', 'risk-unknown',
    // Level-based classes for ingredient detail
    'level-t4', 'level-t3', 'level-t2', 'level-t1', 'level-t0', 'level-unknown',
  ],
})
