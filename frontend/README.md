# Frontend (Next.js)

This directory contains the Next.js renderer for the desktop app (app router + Tailwind + shadcn-style primitives).

## Developer setup

1) Install deps: `cd frontend && npm install` (Node 18+).  
2) Start dev server: `npm run dev` → http://localhost:3000.  
3) Electron dev: `cd electron && ELECTRON_START_URL=http://localhost:3000 npm run dev` (or from root: `npm run dev:desktop`).
4) Static export for Electron prod: `npm run export` (outputs to `frontend/out`, which Electron loads).

## API base URL

- Default is `http://localhost:8000`. Override with `NEXT_PUBLIC_API_BASE_URL` if FastAPI runs elsewhere. The landing page pings `/health`.

## Notes

- Tailwind config lives in `tailwind.config.ts`; shadcn-style primitives are under `components/ui/`.
- IPC access points are typed in `frontend/types/desktop.d.ts`; keep renderer FS access behind IPC (`electron/preload.ts`).
