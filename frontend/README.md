# Frontend (Next.js)

This is the renderer for the desktop migration (Next.js app router + Tailwind). It is intentionally minimal so you can layer in API clients, shadcn/ui components, and IPC wiring.

## Getting started

1) Install deps: `cd frontend && npm install` (Node 18+).  
2) Start dev server: `npm run dev` → http://localhost:3000.  
3) Point Electron at the dev server: `ELECTRON_START_URL=http://localhost:3000 npm run dev --workspace electron` (or your chosen Electron start command).

## Notes

- Tailwind is configured via `tailwind.config.ts`; extend as components are added.  
- Keep renderer FS access behind IPC (see `electron/preload.ts`).  
- Add shared types for `window.desktop` APIs in `frontend/types`.
