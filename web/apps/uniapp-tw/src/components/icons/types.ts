/**
 * Icon Types — Lucide-style type definitions
 */

export interface IconAttributes {
  xmlns?: string;
  viewBox: string;
  fill?: 'none' | 'currentColor' | string;
  stroke?: 'none' | 'currentColor' | string;
  strokeWidth?: number | string;
  strokeLinecap?: 'butt' | 'round' | 'square';
  strokeLinejoin?: 'arcs' | 'bevel' | 'miter' | 'round';
  strokeDasharray?: number | string;
  strokeDashoffset?: number | string;
  strokeMiterlimit?: number | string;
}

export interface IconEntry {
  name: string;
  aliases?: string[];
  tags?: string[];
  contents: string;  // SVG path(s) as string
}

export interface IconProps {
  size?: number | string;
  strokeWidth?: number | string;
  absoluteStrokeWidth?: boolean;
  spin?: boolean;
}
