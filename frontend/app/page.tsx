/* eslint-disable @next/next/no-img-element */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

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
      <div className="flex items-start justify-between">
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
        <div className="pt-3">
          <Link href="/settings">
            <Button variant="secondary">Settings</Button>
          </Link>
        </div>
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
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-50">Backend / desktop wiring</h3>
            <p className="mt-1 text-sm text-slate-300">Quick checks to confirm FastAPI + IPC are reachable.</p>
          </div>
          <HealthStatus />
        </div>
        <ul className="mt-4 space-y-2 text-sm text-slate-200">
          <li>• Add FastAPI client helpers under <code>frontend/lib/api.ts</code>.</li>
          <li>• Expose IPC helpers in <code>electron/preload.ts</code> and type them for the renderer.</li>
          <li>• Build the dashboard and resume views with Tailwind + shadcn/ui.</li>
        </ul>
      </section>
    </main>
  );
}

function HealthStatus() {
  const [status, setStatus] = useState<"checking" | "ok" | "error">("checking");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.health().then((res) => {
      if (cancelled) return;
      if (res.ok) {
        setStatus("ok");
        setMessage(res.data.message ?? res.data.status ?? "healthy");
      } else {
        setStatus("error");
        setMessage(res.error ?? "unreachable");
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const pillClass =
    status === "ok"
      ? "bg-emerald-500/15 text-emerald-200 border border-emerald-700/40"
      : status === "error"
      ? "bg-rose-500/15 text-rose-200 border border-rose-700/40"
      : "bg-slate-700/40 text-slate-200 border border-slate-700/60";

  const label = status === "ok" ? "Backend healthy" : status === "error" ? "Backend unreachable" : "Checking backend";

  return (
    <div className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm ${pillClass}`}>
      <span className="h-2 w-2 rounded-full bg-current opacity-80" />
      <span>{label}</span>
      {message && <span className="text-xs text-slate-300/80">{message}</span>}
    </div>
  );
}
