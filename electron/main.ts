import { app, BrowserWindow, dialog, ipcMain, shell } from "electron";
import path from "node:path";
import url from "node:url";
import { IPC_CHANNELS } from "./ipc/channels";

const isDev = process.env.NODE_ENV === "development";

const resolveRendererUrl = () => {
  const envUrl = process.env.ELECTRON_START_URL;
  if (envUrl) {
    return envUrl;
  }

  if (isDev) {
    return "http://localhost:3000";
  }

  const filePath = path.join(__dirname, "..", "frontend", "out", "index.html");
  return url.pathToFileURL(filePath).toString();
};

const createWindow = () => {
  const mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    backgroundColor: "#0f172a",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });

  const startUrl = resolveRendererUrl();
  if (startUrl.startsWith("http")) {
    mainWindow.loadURL(startUrl);
  } else {
    mainWindow.loadURL(startUrl);
  }

  mainWindow.webContents.setWindowOpenHandler(({ url: targetUrl }) => {
    shell.openExternal(targetUrl);
    return { action: "deny" };
  });
};

app.whenReady().then(() => {
  createWindow();

  ipcMain.handle(IPC_CHANNELS.PING, async () => "pong");
  ipcMain.handle(IPC_CHANNELS.OPEN_FILE, async (_event, options: Electron.OpenDialogOptions | undefined) => {
    const result = await dialog.showOpenDialog({
      properties: ["openFile"],
      ...options
    });
    if (result.canceled) return [];
    return result.filePaths;
  });

  ipcMain.handle(IPC_CHANNELS.SELECT_DIRECTORY, async (_event, options: Electron.OpenDialogOptions | undefined) => {
    const result = await dialog.showOpenDialog({
      properties: ["openDirectory"],
      ...options
    });
    if (result.canceled) return [];
    return result.filePaths;
  });

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
