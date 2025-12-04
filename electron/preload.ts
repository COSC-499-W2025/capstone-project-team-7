import { contextBridge, ipcRenderer } from "electron";
import { IPC_CHANNELS } from "./ipc/channels";

contextBridge.exposeInMainWorld("desktop", {
  ping: () => ipcRenderer.invoke(IPC_CHANNELS.PING)
});
