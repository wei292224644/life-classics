/**
 * 全局前端错误捕获与上报。
 * 仅捕获真实运行时错误，不做行为埋点。
 * 通过 sendBeacon（降级 fetch）向后端 POST /api/logs 上报。
 */

const LOG_ENDPOINT = "/api/logs";
const SERVICE_NAME = "console-web";

interface FrontendLogEntry {
  level: "error";
  service: string;
  message: string;
  stack: string;
  url: string;
  user_agent: string;
  timestamp: string;
}

function sendLog(entry: FrontendLogEntry): void {
  const payload = JSON.stringify(entry);
  // sendBeacon 在页面关闭时也能发送
  if (navigator.sendBeacon) {
    navigator.sendBeacon(LOG_ENDPOINT, new Blob([payload], { type: "application/json" }));
  } else {
    fetch(LOG_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload,
      keepalive: true,
    }).catch(() => {
      // 静默处理：日志上报失败不影响用户
    });
  }
}

function buildEntry(message: string, stack: string): FrontendLogEntry {
  return {
    level: "error",
    service: SERVICE_NAME,
    message,
    stack: stack.slice(0, 2000), // 前端也截断，双重保险
    url: window.location.pathname,
    user_agent: navigator.userAgent,
    timestamp: new Date().toISOString(),
  };
}

export function initErrorReporter(): void {
  // 捕获同步 JS 错误
  window.onerror = (message, _source, _lineno, _colno, error) => {
    const msg = typeof message === "string" ? message : String(message);
    const stack = error?.stack ?? msg;
    sendLog(buildEntry(msg, stack));
    return false; // 不阻止默认行为
  };

  // 捕获未处理的 Promise rejection
  window.addEventListener("unhandledrejection", (event) => {
    const reason = event.reason;
    const message = reason instanceof Error ? reason.message : String(reason);
    const stack = reason instanceof Error ? (reason.stack ?? message) : message;
    sendLog(buildEntry(message, stack));
  });
}
