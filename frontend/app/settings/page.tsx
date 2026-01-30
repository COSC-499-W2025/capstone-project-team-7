"use client";

import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent, CardFooter, CardDescription } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { loadSettings, saveSettings, loadConsents, saveConsents, ConsentRecord, AppSettings } from "@/lib/settings";
import { consent as consentApi, config as configApi } from "@/lib/api";

function uid() {
  return Math.random().toString(36).slice(2, 9);
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings>({});
  const [consents, setConsents] = useState<ConsentRecord[]>([]);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      // try desktop persisted settings first
      try {
        const res = await (window.desktop?.loadSettings?.() as Promise<any> | undefined);
        if (!cancelled && res && res.ok && res.settings) {
          setSettings(res.settings);
        } else {
          const local = loadSettings();
          if (!cancelled) setSettings(local);
        }
      } catch {
        const local = loadSettings();
        if (!cancelled) setSettings(local);
      }

      // load consents from local storage (desktop save currently only persists settings.json)
      if (!cancelled) setConsents(loadConsents());

      // Try to load consent status from backend; fallback to local state
      try {
        const res = await consentApi.get();
        if (!cancelled && res.ok) {
          // Map backend consent to local flags
          setSettings((s) => ({ ...(s ?? {}), enableAnalytics: !!res.data.external_services }));
        }
      } catch {
        // ignore - use local
      }

      // Try to fetch server config (not required) to surface availability
      try {
        await configApi.get();
      } catch {
        // ignore
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const update = (patch: Partial<AppSettings>) => setSettings((s) => ({ ...(s ?? {}), ...(patch ?? {}) }));

  const selectDirectory = async () => {
    try {
      const dirs = await window.desktop?.selectDirectory?.();
      if (dirs && dirs.length > 0) update({ defaultSavePath: dirs[0] });
    } catch (err) {
      // noop
    }
  };

  const onSave = () => {
    const ok = saveSettings(settings);
    setSaveStatus(ok ? "Saved" : "Failed to save");
    setTimeout(() => setSaveStatus(null), 2500);
    // Attempt to call desktop bridge if available for persistence
    try {
      if ((window as any).desktop?.saveSettings) {
        (window as any).desktop.saveSettings(settings);
      }
    } catch {}
    // Try to persist analytics consent to backend if available
    (async () => {
      try {
        await consentApi.set({ data_access: !!settings.enableAnalytics, external_services: !!settings.enableAnalytics });
      } catch {}
    })();
  };

  const grantAnalytics = () => {
    const record: ConsentRecord = { id: uid(), granted: true, purpose: "analytics", timestamp: new Date().toISOString() };
    const next = [record, ...consents];
    setConsents(next);
    saveConsents(next);
    update({ enableAnalytics: true });
    saveSettings({ ...(settings ?? {}), enableAnalytics: true });
    (async () => {
      try {
        await consentApi.set({ data_access: true, external_services: true });
      } catch {}
    })();
  };

  const revokeConsent = (id: string) => {
    const next = consents.filter((c) => c.id !== id);
    setConsents(next);
    saveConsents(next);
    // if analytics consent removed, flip setting
    if (!next.some((c) => c.purpose === "analytics" && c.granted)) {
      update({ enableAnalytics: false });
      saveSettings({ ...(settings ?? {}), enableAnalytics: false });
      (async () => {
        try {
          await consentApi.set({ data_access: false, external_services: false });
        } catch {}
      })();
    }
  };

  return (
    <main className="space-y-6">
      <h1 className="text-3xl font-semibold">Settings</h1>

      <section className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Preferences</CardTitle>
            <CardDescription className="text-sm">Application configuration and UI preferences.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm">Default save directory</label>
                <div className="flex gap-2">
                  <Input value={settings.defaultSavePath ?? ""} onChange={(e) => update({ defaultSavePath: e.target.value })} />
                  <Button variant="outline" onClick={selectDirectory}>Select</Button>
                </div>
              </div>

              <div>
                <label className="mb-1 block text-sm">Enable high contrast UI</label>
                <div className="flex items-center gap-3">
                  <input
                    id="hc"
                    type="checkbox"
                    checked={!!settings.enableHighContrast}
                    onChange={(e) => update({ enableHighContrast: e.target.checked })}
                  />
                  <label htmlFor="hc" className="text-sm text-slate-300">Toggle site-wide high contrast styles</label>
                </div>
              </div>
            </div>
          </CardContent>
          <CardFooter>
            <div className="flex items-center gap-3">
              <Button onClick={onSave}>Save preferences</Button>
              {saveStatus && <span className="text-sm text-slate-300">{saveStatus}</span>}
            </div>
          </CardFooter>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Consent & Privacy</CardTitle>
            <CardDescription className="text-sm">Manage data sharing preferences and view consent history.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="block text-sm">Analytics</label>
                <p className="text-xs text-slate-400">Allow anonymous usage metrics to help improve the app.</p>
                <div className="mt-2 flex items-center gap-3">
                  <Button variant={settings.enableAnalytics ? "destructive" : "default"} onClick={grantAnalytics}>
                    {settings.enableAnalytics ? "Granted" : "Grant analytics consent"}
                  </Button>
                  <Button variant="outline" onClick={() => { setConsents([]); saveConsents([]); update({ enableAnalytics: false }); saveSettings({ ...(settings ?? {}), enableAnalytics: false }); }}>
                    Revoke all consents
                  </Button>
                </div>
              </div>

              <div>
                <label className="block text-sm">Consent history</label>
                <div className="mt-2 space-y-2">
                  {consents.length === 0 && <p className="text-sm text-slate-400">No recorded consents.</p>}
                  {consents.map((c) => (
                    <div key={c.id} className="flex items-start justify-between rounded-md border border-slate-800 p-3">
                      <div>
                        <div className="text-sm font-medium">{c.purpose}</div>
                        <div className="text-xs text-slate-400">{new Date(c.timestamp).toLocaleString()}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-slate-200">{c.granted ? "Granted" : "Revoked"}</span>
                        <Button size="sm" variant="outline" onClick={() => revokeConsent(c.id)}>Remove</Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      <section>
        <Card>
          <CardHeader>
            <CardTitle>Developer notes</CardTitle>
            <CardDescription className="text-sm">How this page works and where to extend persistence.</CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea readOnly value={"This settings page stores preferences and consents in localStorage by default.\n\nTo persist to the desktop, add a method in electron/preload.ts (e.g. saveSettings) and call it from the renderer. The helper \"frontend/lib/settings.ts\" centralizes storage operations."} />
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
