// Safe system info helper
export function useSystemInfo() {
  const info = uni.getSystemInfoSync();
  return {
    statusBarHeight: info.statusBarHeight ?? 44,
    safeAreaTop: info.safeArea?.top ?? 0,
    safeAreaBottom: info.safeArea?.bottom ?? 0,
    screenWidth: info.screenWidth ?? 375,
    screenHeight: info.screenHeight ?? 812,
    platform: info.platform ?? 'unknown',
  };
}
