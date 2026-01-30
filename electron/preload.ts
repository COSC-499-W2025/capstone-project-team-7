import { contextBridge, ipcRenderer } from "electron";

// Try to load compiled IPC channels; fall back to a minimal inline map so
// preload doesn't crash if the module can't be resolved at runtime.
let IPC_CHANNELS = {
  PING: "desktop:ping",
  OPEN_FILE: "desktop:openFile",
  SELECT_DIRECTORY: "desktop:selectDirectory",
} as const;

try {
  // Use require so this works in the compiled CommonJS preload script.
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const mod = require("./ipc/channels");
  if (mod && mod.IPC_CHANNELS) {
    IPC_CHANNELS = mod.IPC_CHANNELS;
  }
} catch (err) {
  // If channels module isn't available in dist/, keep the fallback map.
}

contextBridge.exposeInMainWorld("desktop", {
  ping: () => ipcRenderer.invoke(IPC_CHANNELS.PING),
  openFile: (options?: Electron.OpenDialogOptions) => ipcRenderer.invoke(IPC_CHANNELS.OPEN_FILE, options),
  selectDirectory: (options?: Electron.OpenDialogOptions) => ipcRenderer.invoke(IPC_CHANNELS.SELECT_DIRECTORY, options),
  saveSettings: (settings?: any) => ipcRenderer.invoke(IPC_CHANNELS.SAVE_SETTINGS, settings),
  loadSettings: () => ipcRenderer.invoke(IPC_CHANNELS.LOAD_SETTINGS),
});
