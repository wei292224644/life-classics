<script setup lang="ts">
import { computed } from "vue";
import { cn } from "@/utils/cn";

defineOptions({
  options: { virtualHost: true, addGlobalClass: true },
});

interface Props {
  name: string;
  type?: "line" | "fill";
  dclass?: string;
}

const props = withDefaults(defineProps<Props>(), {
  dclass: "",
  type: "line",
});

// Risk icons: SVG contents (not in remixicon, rendered via CSS mask)
// const riskIcons: Record<string, string> = {
//   riskT0: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M12 2L4 6v5.5c0 5.5 3.5 10.7 8 12 4.5-1.3 8-6.5 8-12V6L12 2z"/></svg>`,
//   riskT1: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M12 2L4 6v5.5c0 5.5 3.5 10.7 8 12 4.5-1.3 8-6.5 8-12V6L12 2z"/><path d="M6 16h10" stroke-width="2.5" stroke-linecap="round"/></svg>`,
//   riskT2: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M12 2L4 6v5.5c0 5.5 3.5 10.7 8 12 4.5-1.3 8-6.5 8-12V6L12 2z"/><path d="M6 14h10M6 18h10" stroke-width="2.5" stroke-linecap="round"/></svg>`,
//   riskT3: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M12 2L4 6v5.5c0 5.5 3.5 10.7 8 12 4.5-1.3 8-6.5 8-12V6L12 2z"/><path d="M6 12h10M6 15h10M6 18h10" stroke-width="2.5" stroke-linecap="round"/></svg>`,
//   riskT4: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M12 2L4 6v5.5c0 5.5 3.5 10.7 8 12 4.5-1.3 8-6.5 8-12V6L12 2z"/><line x1="12" y1="8" x2="12" y2="16" stroke-width="2.5" stroke-linecap="round"/><circle cx="12" cy="19" r="1.5" fill="currentColor"/></svg>`,
//   riskUnknown: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" stroke-dasharray="6 4"><path d="M12 2L4 6v5.5c0 5.5 3.5 10.7 8 12 4.5-1.3 8-6.5 8-12V6L12 2z"/></svg>`,
// };
// camelCase → kebab-case，e.g. arrowLeft → arrow-left
function toKebabCase(str: string) {
  return str.replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase();
}

const remixClass = computed(
  () => `ri-${toKebabCase(props.name)}-${props.type}`,
);
</script>

<template>
  <!-- Remix Icon: use view with font class -->
  <view
    :class="
      cn(
        'remixicon size-4 text-sm flex items-center justify-center',
        remixClass,
        dclass,
      )
    "
  />
</template>
