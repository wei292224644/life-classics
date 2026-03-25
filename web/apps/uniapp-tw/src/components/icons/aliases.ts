/**
 * Icon Aliases — Lucide-style backward compatibility aliases
 */

export const aliases: Record<string, string> = {
  // Direction
  left: 'arrow-left',
  right: 'arrow-right',
  'chevron-up': 'chevron-down', // inverse for some cases
  'chevron-left': 'arrow-left',

  // Close
  close: 'x',
  delete: 'x',
  remove: 'x',

  // Common
  home: 'arrow-left', // mapped to back for now
  back: 'arrow-left',

  // Social
  chat: 'message-circle',
  ai: 'message-circle',

  // Misc
  cart: 'shopping-cart',
  shop: 'shopping-cart',
};
