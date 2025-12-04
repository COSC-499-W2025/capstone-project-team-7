const setupSteps = [
  {
    title: "Install dependencies",
    detail: "cd frontend && npm install (Node 18+)."
  },
  {
    title: "Run the renderer",
    detail: "npm run dev to serve the Next.js app at http://localhost:3000."
  },
  {
    title: "Start Electron",
    detail: "Run the Electron shell with ELECTRON_START_URL=http://localhost:3000."
  }
];

export default function HomePage() {
  return (
    <main className="space-y-8">
      <div className="space-y-3">
        <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Desktop migration</p>
        <h1 className="text-4xl font-semibold tracking-tight text-slate-50">
          Next.js renderer scaffold is ready
        </h1>
        <p className="max-w-3xl text-lg text-slate-200">
          This page is the landing spot for the new desktop UI. Wire it to the FastAPI backend and Electron IPC as
          you add screens for scans, resumes, and settings.
        </p>
      </div>

      <section className="grid gap-4 sm:grid-cols-3">
        {setupSteps.map((step) => (
          <div key={step.title} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-lg shadow-slate-950/50">
            <h2 className="text-base font-semibold text-slate-50">{step.title}</h2>
            <p className="mt-2 text-sm text-slate-300">{step.detail}</p>
          </div>
        ))}
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 shadow-inner shadow-slate-950/40">
        <h3 className="text-lg font-semibold text-slate-50">Next steps</h3>
        <ul className="mt-3 space-y-2 text-sm text-slate-200">
          <li>• Add FastAPI client helpers under <code>frontend/lib/api.ts</code>.</li>
          <li>• Expose IPC helpers in <code>electron/preload.ts</code> and type them for the renderer.</li>
          <li>• Build the dashboard and resume views with Tailwind + shadcn/ui.</li>
        </ul>
      </section>
    </main>
  );
}
