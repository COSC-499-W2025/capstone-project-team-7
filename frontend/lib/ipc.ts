type DesktopBridge = Window["desktop"];

const getBridge = (): DesktopBridge | undefined => {
  if (typeof window === "undefined") return undefined;
  return window.desktop;
};

export const ipc = {
  ping: async () => {
    const bridge = getBridge();
    if (!bridge?.ping) return { ok: false as const, error: "desktop bridge unavailable" };
    try {
      const result = await bridge.ping();
      return { ok: true as const, data: result };
    } catch (error) {
      const message = error instanceof Error ? error.message : "unknown error";
      return { ok: false as const, error: message };
    }
  }
};
