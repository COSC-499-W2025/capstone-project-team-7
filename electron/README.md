# Electron shell

Minimal Electron main + preload scaffold to host the Next.js renderer. Security defaults: nodeIntegration disabled, contextIsolation enabled, sandbox on.

## Dev quick start

1) Install deps: `cd electron && npm install`.  
2) Run the Next dev server at `http://localhost:3000` (`cd frontend && npm run dev`).  
3) Launch Electron pointing at the dev server: `ELECTRON_START_URL=http://localhost:3000 npm run dev`.

## Notes

- `preload.ts` exposes a minimal `desktop.ping()` IPC bridge; add more channels under `electron/ipc`.  
- Production fallback loads `frontend/out/index.html`; keep in sync with the renderer build output.  
- Keep renderer file system access behind IPC handlers defined in the main process.
