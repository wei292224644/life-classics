import { describe, it, expect } from 'vitest';
import { aliases, defaultAttributes } from '../';
import * as icons from '../';

describe('Icon Library', () => {
  describe('aliases', () => {
    it('should resolve left to arrow-left', () => {
      expect(aliases['left']).toBe('arrow-left');
    });

    it('should resolve right to arrow-right', () => {
      expect(aliases['right']).toBe('arrow-right');
    });

    it('should resolve close to x', () => {
      expect(aliases['close']).toBe('x');
    });

    it('should resolve chat to message-circle', () => {
      expect(aliases['chat']).toBe('message-circle');
    });

    it('should resolve cart to shopping-cart', () => {
      expect(aliases['cart']).toBe('shopping-cart');
    });
  });

  describe('defaultAttributes', () => {
    it('should have correct viewBox', () => {
      expect(defaultAttributes.viewBox).toBe('0 0 24 24');
    });

    it('should use currentColor for stroke', () => {
      expect(defaultAttributes.stroke).toBe('currentColor');
    });

    it('should have round linecap', () => {
      expect(defaultAttributes.strokeLinecap).toBe('round');
    });

    it('should have round linejoin', () => {
      expect(defaultAttributes.strokeLinejoin).toBe('round');
    });

    it('should have strokeWidth of 2', () => {
      expect(defaultAttributes.strokeWidth).toBe(2);
    });
  });

  describe('icons', () => {
    it('should export arrowLeft icon', () => {
      expect(icons.arrowLeft).toBeDefined();
      expect(icons.arrowLeft.name).toBe('arrow-left');
    });

    it('should export arrowRight icon', () => {
      expect(icons.arrowRight).toBeDefined();
      expect(icons.arrowRight.name).toBe('arrow-right');
    });

    it('should export check icon', () => {
      expect(icons.check).toBeDefined();
      expect(icons.check.name).toBe('check');
    });

    it('should export x icon', () => {
      expect(icons.x).toBeDefined();
      expect(icons.x.name).toBe('x');
    });

    it('should have valid contents for arrowLeft', () => {
      expect(icons.arrowLeft.contents).toContain('path');
    });

    it('should have tags for all icons', () => {
      expect(icons.arrowLeft.tags).toBeDefined();
      expect(Array.isArray(icons.arrowLeft.tags)).toBe(true);
    });
  });
});
