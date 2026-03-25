/**
 * Icon Registry — for dynamic icon lookup
 */
import * as icons from './index';

export const iconRegistry = {
  arrowLeft: icons.arrowLeft,
  arrowRight: icons.arrowRight,
  x: icons.x,
  check: icons.check,
  chevronDown: icons.chevronDown,
  share: icons.share,
  star: icons.star,
  badgeCheck: icons.badgeCheck,
  leaf: icons.leaf,
  helpCircle: icons.helpCircle,
  alertTriangle: icons.alertTriangle,
  info: icons.info,
  alertCircle: icons.alertCircle,
  shoppingCart: icons.shoppingCart,
  scan: icons.scan,
  user: icons.user,
  menu: icons.menu,
  users: icons.users,
  bookmark: icons.bookmark,
  settings: icons.settings,
  search: icons.search,
  messageCircle: icons.messageCircle,
  loader: icons.loader,
} as const;

export type IconName = keyof typeof iconRegistry;
