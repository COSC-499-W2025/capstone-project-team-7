# Electron shell

Minimal Electron main + preload scaffold to host the Next.js renderer. Security defaults: nodeIntegration disabled, contextIsolation enabled, sandbox on.

## Dev quick start (renderer via dev server)

1) Install deps (once): `npm install --workspaces` from repo root (or `cd electron && npm install` and `cd frontend && npm install`).  
2) Run the Next dev server at `http://localhost:3000`: `cd frontend && npm run dev`.  
3) Launch Electron pointing at the dev server: `cd electron && ELECTRON_START_URL=http://localhost:3000 npm run dev`.

## Prod-ish preview (static export)

1) Build the renderer to static assets: `cd frontend && npm run export` (outputs `frontend/out`).  
2) Build the Electron main/preload bundle: `cd electron && npm run build`.  
3) Run the compiled Electron app loading `frontend/out/index.html`: `cd electron && npm start`.

## Notes

- `preload.ts` exposes a minimal `desktop.ping()` IPC bridge; add more channels under `electron/ipc`.  
- Production fallback loads `frontend/out/index.html`; keep in sync with the renderer build output.  
- Keep renderer file system access behind IPC handlers defined in the main process.
