import { app, BrowserWindow, dialog, ipcMain, shell } from "electron";
import path from "node:path";
import url from "node:url";
import { promises as fsPromises } from "node:fs";
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
    backgroundColor: "#ffffff",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });

  const startUrl = resolveRendererUrl();
  console.log("Loading URL:", startUrl);
  
  if (startUrl.startsWith("http")) {
    mainWindow.loadURL(startUrl);
  } else {
    mainWindow.loadURL(startUrl);
  }

  // Open DevTools in development
  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.webContents.setWindowOpenHandler(({ url: targetUrl }) => {
    shell.openExternal(targetUrl);
    return { action: "deny" };
  });

  // Log any load failures
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
    console.error('Failed to load:', validatedURL, 'Error:', errorDescription);
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

  // Persist settings to a file under the user's application data directory
  ipcMain.handle(IPC_CHANNELS.SAVE_SETTINGS, async (_event, settings: any) => {
    try {
      const userData = app.getPath("userData");
      const file = path.join(userData, "settings.json");
      await fsPromises.mkdir(userData, { recursive: true });
      await fsPromises.writeFile(file, JSON.stringify(settings ?? {}, null, 2), "utf8");
      return { ok: true, path: file };
    } catch (err: any) {
      return { ok: false, error: err?.message ?? String(err) };
    }
  });

  // Load persisted settings from disk (if present)
  ipcMain.handle(IPC_CHANNELS.LOAD_SETTINGS, async () => {
    try {
      const userData = app.getPath("userData");
      const file = path.join(userData, "settings.json");
      try {
        const content = await fsPromises.readFile(file, "utf8");
        const parsed = JSON.parse(content);
        return { ok: true, settings: parsed, path: file };
      } catch (readErr: any) {
        // If file not found, return ok:false but no error to indicate empty state
        if (readErr.code === "ENOENT") return { ok: false, error: "not_found" };
        return { ok: false, error: readErr?.message ?? String(readErr) };
      }
    } catch (err: any) {
      return { ok: false, error: err?.message ?? String(err) };
    }
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
