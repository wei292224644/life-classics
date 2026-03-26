// process.env.UNI_PLATFORM 由 Vite 在编译时静态替换，不会进入运行时
export const isMp = (process.env.UNI_PLATFORM as string)?.startsWith("mp");
export const isH5 = process.env.UNI_PLATFORM === "h5";
export const isApp = process.env.UNI_PLATFORM === "app";

console.log(process.env.UNI_PLATFORM, isMp, isH5, isApp);
