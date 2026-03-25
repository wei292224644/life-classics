/**
 * Create Icon Component — Lucide-style factory function
 */

import { defaultAttributes } from './defaultAttributes';
import type { IconEntry, IconProps } from './types';

interface ComponentOptions {
  name: string;
  entry: IconEntry;
}

export function createIconComponent({ name, entry }: ComponentOptions) {
  return {
    name: `Icon${pascalCase(name)}`,
    props: {
      size: {
        type: [Number, String],
        default: 24,
      },
      strokeWidth: {
        type: [Number, String],
        default: 2,
      },
      absoluteStrokeWidth: {
        type: Boolean,
        default: false,
      },
      spin: {
        type: Boolean,
        default: false,
      },
    },
    setup(props: IconProps) {
      const isFilled = entry.contents.includes('fill="currentColor"');

      const effectiveStrokeWidth = () => {
        if (props.absoluteStrokeWidth) {
          return Number(props.strokeWidth) * (24 / Number(props.size));
        }
        return props.strokeWidth;
      };

      return () => ({
        type: 'svg',
        props: {
          xmlns: defaultAttributes.xmlns,
          viewBox: defaultAttributes.viewBox,
          width: props.size,
          height: props.size,
          fill: isFilled ? 'currentColor' : 'none',
          stroke: isFilled ? undefined : 'currentColor',
          strokeWidth: isFilled ? undefined : effectiveStrokeWidth(),
          strokeLinecap: isFilled ? undefined : defaultAttributes.strokeLinecap,
          strokeLinejoin: isFilled ? undefined : defaultAttributes.strokeLinejoin,
          class: ['icon', { 'icon--spin': props.spin }],
          'aria-hidden': true,
        },
        children: entry.contents,
      });
    },
  };
}

function pascalCase(str: string): string {
  return str
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join('');
}
