import { contextBridge, ipcRenderer } from "electron";
import { IPC_CHANNELS } from "./ipc/channels";

contextBridge.exposeInMainWorld("desktop", {
  ping: () => ipcRenderer.invoke(IPC_CHANNELS.PING),
  openFile: (options?: Electron.OpenDialogOptions) => ipcRenderer.invoke(IPC_CHANNELS.OPEN_FILE, options),
  selectDirectory: (options?: Electron.OpenDialogOptions) => ipcRenderer.invoke(IPC_CHANNELS.SELECT_DIRECTORY, options)
});
