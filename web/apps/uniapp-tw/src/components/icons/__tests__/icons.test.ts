import { describe, it, expect } from 'vitest';
import * as icons from '../';

describe('Icon Library', () => {
  describe('aliases', () => {
    it('should resolve left to arrow-left', () => {
      expect(icons.aliases['left']).toBe('arrow-left');
    });

    it('should resolve right to arrow-right', () => {
      expect(icons.aliases['right']).toBe('arrow-right');
    });

    it('should resolve close to x', () => {
      expect(icons.aliases['close']).toBe('x');
    });

    it('should resolve chat to message-circle', () => {
      expect(icons.aliases['chat']).toBe('message-circle');
    });

    it('should resolve cart to shopping-cart', () => {
      expect(icons.aliases['cart']).toBe('shopping-cart');
    });
  });

  describe('defaultAttributes', () => {
    it('should have correct viewBox', () => {
      expect(icons.defaultAttributes.viewBox).toBe('0 0 24 24');
    });

    it('should use currentColor for stroke', () => {
      expect(icons.defaultAttributes.stroke).toBe('currentColor');
    });

    it('should have round linecap', () => {
      expect(icons.defaultAttributes.strokeLinecap).toBe('round');
    });

    it('should have round linejoin', () => {
      expect(icons.defaultAttributes.strokeLinejoin).toBe('round');
    });

    it('should have strokeWidth of 2', () => {
      expect(icons.defaultAttributes.strokeWidth).toBe(2);
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

    it('arrowLeft should have tags', () => {
      expect(icons.arrowLeft.tags).toBeDefined();
      expect(Array.isArray(icons.arrowLeft.tags)).toBe(true);
    });
  });
});
