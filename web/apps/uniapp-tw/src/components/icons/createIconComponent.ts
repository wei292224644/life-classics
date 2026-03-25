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
    setup(props: IconProps, { slots }: any) {
      const strokeWidth = () => {
        if (props.absoluteStrokeWidth) {
          return Number(props.strokeWidth) * (24 / Number(props.size));
        }
        return props.strokeWidth;
      };

      const renderedContent = () => {
        let content = entry.contents;
        // If filled icon, ensure fill="currentColor" is set
        if (content.includes('fill="currentColor"')) {
          return content;
        }
        // For stroke icons, add stroke attributes
        return content;
      };

      return () => ({
        type: 'svg',
        props: {
          xmlns: defaultAttributes.xmlns,
          viewBox: defaultAttributes.viewBox,
          width: props.size,
          height: props.size,
          fill: content.includes('fill="currentColor"') ? 'currentColor' : 'none',
          stroke: content.includes('fill="currentColor"') ? undefined : 'currentColor',
          strokeWidth: content.includes('fill="currentColor"') ? undefined : strokeWidth(),
          strokeLinecap: content.includes('fill="currentColor"') ? undefined : defaultAttributes.strokeLinecap,
          strokeLinejoin: content.includes('fill="currentColor"') ? undefined : defaultAttributes.strokeLinejoin,
          class: ['icon', { 'icon--spin': props.spin }],
          'aria-hidden': true,
        },
        children: content,
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