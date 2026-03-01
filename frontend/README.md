# Frontend (Next.js)

This directory contains the Next.js renderer for the desktop app (app router + Tailwind + shadcn-style primitives).

#mi

## Password reset flow

- The reset email link uses Supabase Auth and redirects back to `http://localhost:3000/auth/reset-password`.
- Ensure Supabase Auth allows this URL under **Authentication → URL Configuration → Redirect URLs**.

## Testing

Frontend tests use [Vitest](https://vitest.dev/) + [Testing Library](https://testing-library.com/):

```bash
npm run test          # single run
npm run test:watch    # watch mode
```

Test files live in `__tests__/`. Config is in `vitest.config.ts` (jsdom environment, `@/` path alias).

## Notes

- Tailwind config lives in `tailwind.config.ts`; shadcn-style primitives are under `components/ui/`.
- The UI uses a "Pro Contrast" light theme (white background, black text, `#CFCFCF` borders, no shadows). Theme variables are in `app/globals.css`.
- IPC access points are typed in `frontend/types/desktop.d.ts`; keep renderer FS access behind IPC (`electron/preload.ts`).
