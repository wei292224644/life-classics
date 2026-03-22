export class ScanCancelledError extends Error {
  constructor() {
    super("Scan cancelled by user");
    this.name = "ScanCancelledError";
  }
}

export async function scanBarcode(): Promise<string> {
  return new Promise((resolve, reject) => {
    uni.scanCode({
      onlyFromCamera: true,
      success: (res) => resolve(res.result),
      fail: () => reject(new ScanCancelledError()),
    });
  });
}
