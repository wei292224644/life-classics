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
  riskT0: icons.riskT0,
  riskT1: icons.riskT1,
  riskT2: icons.riskT2,
  riskT3: icons.riskT3,
  riskT4: icons.riskT4,
  riskUnknown: icons.riskUnknown,
  checkCircle: icons.checkCircle,
  xCircle: icons.xCircle,
} as const;

export type IconName = keyof typeof iconRegistry;
