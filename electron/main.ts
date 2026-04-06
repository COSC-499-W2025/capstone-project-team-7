import { app, BrowserWindow, dialog, ipcMain, protocol, shell } from "electron";
import path from "node:path";
import url from "node:url";
import fs from "node:fs";
import { promises as fsPromises } from "node:fs";
import { IPC_CHANNELS } from "./ipc/channels";

const isDev = !app.isPackaged;
const shouldOpenDevTools =
  process.env.ELECTRON_OPEN_DEVTOOLS === "1" ||
  process.env.ELECTRON_OPEN_DEVTOOLS === "true";

const inferMimeType = (filePath: string) => {
  const ext = path.extname(filePath).toLowerCase();
  switch (ext) {
    case ".png":
      return "image/png";
    case ".jpg":
    case ".jpeg":
      return "image/jpeg";
    case ".gif":
      return "image/gif";
    case ".webp":
      return "image/webp";
    default:
      return "application/octet-stream";
  }
};

const resolveRendererUrl = () => {
  const envUrl = process.env.ELECTRON_START_URL;
  if (envUrl) {
    return envUrl;
  }

  if (isDev) {
    return "http://localhost:3000";
  }

  // In packaged builds, the static export lives in resources/renderer/
  const filePath = path.join(process.resourcesPath, "renderer", "index.html");
  return url.pathToFileURL(filePath).toString();
};

const createWindow = () => {
  // In packaged builds, intercept file:// requests so that absolute paths
  // (e.g. /auth/login, /_next/static/...) resolve inside resources/renderer/
  if (!isDev) {
    const rendererDir = path.join(process.resourcesPath, "renderer");
    protocol.interceptFileProtocol("file", (request, callback) => {
      let requestPath = decodeURIComponent(new URL(request.url).pathname);
      // On Windows, strip the leading slash from /C:/... paths
      if (process.platform === "win32" && requestPath.startsWith("/")) {
        requestPath = requestPath.slice(1);
      }
      // Normalize slashes so forward-slash URL paths match backslash OS paths
      requestPath = path.normalize(requestPath);
      // If the path is already inside the renderer dir, serve it directly
      if (requestPath.startsWith(rendererDir)) {
        callback({ path: requestPath });
        return;
      }
      // Strip drive letter to get the relative path (e.g. C:\_next\foo.js → _next\foo.js)
      let relativePath = requestPath;
      if (process.platform === "win32" && /^[A-Za-z]:\\/.test(relativePath)) {
        relativePath = relativePath.slice(3);
      }
      // Map into the renderer directory
      const resolved = path.join(rendererDir, relativePath);
      if (fs.existsSync(resolved) && fs.statSync(resolved).isFile()) {
        callback({ path: resolved });
      } else if (fs.existsSync(resolved + ".html")) {
        callback({ path: resolved + ".html" });
      } else if (fs.existsSync(path.join(resolved, "index.html"))) {
        callback({ path: path.join(resolved, "index.html") });
      } else {
        // Fallback to index.html for SPA client-side routing
        callback({ path: path.join(rendererDir, "index.html") });
      }
    });
  }

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
  mainWindow.loadURL(startUrl);

  // Open DevTools in development or when explicitly requested
  if (shouldOpenDevTools) {
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

  ipcMain.handle(IPC_CHANNELS.READ_FILE, async (_event, filePath: string) => {
    const content = await fsPromises.readFile(filePath);
    return {
      name: path.basename(filePath),
      type: inferMimeType(filePath),
      size: content.byteLength,
      data: content.toString("base64"),
    };
  });

  ipcMain.handle(IPC_CHANNELS.SELECT_DIRECTORY, async (_event, options: Electron.OpenDialogOptions | undefined) => {
    const { properties: _ignoredProperties, filters: _ignoredFilters, ...dialogOptions } = options ?? {};
    const result = await dialog.showOpenDialog({
      ...dialogOptions,
      properties: ["openDirectory"],
    });
    if (result.canceled) return [];
    return result.filePaths;
  });

  ipcMain.handle(IPC_CHANNELS.SELECT_SCAN_SOURCE, async (_event, options: Electron.OpenDialogOptions | undefined) => {
    const { properties: _ignoredProperties, filters: _ignoredFilters, ...dialogOptions } = options ?? {};
    const result = await dialog.showOpenDialog({
      ...dialogOptions,
      properties: ["openDirectory", "openFile"],
      filters: [{ name: "ZIP Archives", extensions: ["zip"] }],
    });
    if (result.canceled) return [];
    if (result.filePaths.length === 0) return [];

    const selectedPath = result.filePaths[0];
    try {
      const stat = await fsPromises.stat(selectedPath);
      if (stat.isDirectory()) return result.filePaths;
      if (stat.isFile() && path.extname(selectedPath).toLowerCase() === ".zip") {
        return result.filePaths;
      }
    } catch {
      return [];
    }

    return [];
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
