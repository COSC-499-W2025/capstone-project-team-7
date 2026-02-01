"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent, CardFooter, CardDescription } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { loadSettings, saveSettings, loadConsents, saveConsents, ConsentRecord, AppSettings } from "@/lib/settings";
import { loadTheme, saveTheme, applyTheme, type Theme } from "@/lib/theme";
import { consent as consentApi, config as configApi } from "@/lib/api";
import { auth as authApi } from "@/lib/auth";
import type { ConfigResponse, ConfigUpdateRequest, ProfileUpsertRequest } from "@/lib/api.types";
import type { AuthSessionInfo } from "@/lib/auth";

function uid() {
  return Math.random().toString(36).slice(2, 9);
}

type ProfileData = {
  description?: string;
  extensions?: string[];
  exclude_dirs?: string[];
};

export default function SettingsPage() {
  // User session
  const [userSession, setUserSession] = useState<AuthSessionInfo | null>(null);
  const [sessionLoading, setSessionLoading] = useState(true);

  // Theme
  const [theme, setTheme] = useState<Theme>("dark");

  // Local preferences
  const [settings, setSettings] = useState<AppSettings>({});
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  // Consent management
  const [consents, setConsents] = useState<ConsentRecord[]>([]);
  const [showRevokeDialog, setShowRevokeDialog] = useState(false);

  // Server config
  const [serverConfig, setServerConfig] = useState<ConfigResponse | null>(null);
  const [profiles, setProfiles] = useState<Record<string, ProfileData> | null>(null);
  const [serverStatus, setServerStatus] = useState<string | null>(null);

  // Profile management
  const [showNewProfileDialog, setShowNewProfileDialog] = useState(false);
  const [newProfile, setNewProfile] = useState({ name: "", description: "", extensions: "", exclude_dirs: "" });

  useEffect(() => {
    let cancelled = false;

    (async () => {
      // Load theme
      const savedTheme = loadTheme();
      if (!cancelled) {
        setTheme(savedTheme);
        applyTheme(savedTheme);
      }

      // Try to load user session
      try {
        const sessionRes = await authApi.getSession();
        if (!cancelled && sessionRes.ok) {
          setUserSession(sessionRes.data);
        }
      } catch {
        // Not logged in or session unavailable
      } finally {
        if (!cancelled) setSessionLoading(false);
      }

      // Load local settings
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

      // Load consents
      if (!cancelled) setConsents(loadConsents());

      // Try to load consent status from backend
      try {
        const res = await consentApi.get();
        if (!cancelled && res.ok) {
          setSettings((s) => ({ ...(s ?? {}), enableAnalytics: !!res.data.external_services }));
        }
      } catch {
        // Use local
      }

      // Try to fetch server config and profiles
      try {
        const cfg = await configApi.get();
        if (!cancelled && cfg.ok) setServerConfig(cfg.data);
      } catch {}

      try {
        const prof = await configApi.listProfiles();
        if (!cancelled && prof.ok) setProfiles(prof.data.profiles || {});
      } catch {}
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

  const handleThemeChange = (newTheme: Theme) => {
    setTheme(newTheme);
    saveTheme(newTheme);
    applyTheme(newTheme);
  };

  const onSave = () => {
    const ok = saveSettings(settings);
    setSaveStatus(ok ? "Saved successfully" : "Failed to save");
    setTimeout(() => setSaveStatus(null), 2500);

    try {
      if ((window as any).desktop?.saveSettings) {
        (window as any).desktop.saveSettings(settings);
      }
    } catch {}

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

  const revokeAllConsents = () => {
    setConsents([]);
    saveConsents([]);
    update({ enableAnalytics: false });
    saveSettings({ ...(settings ?? {}), enableAnalytics: false });
    (async () => {
      try {
        await consentApi.set({ data_access: false, external_services: false });
      } catch {}
    })();
    setShowRevokeDialog(false);
  };

  const revokeConsent = (id: string) => {
    const next = consents.filter((c) => c.id !== id);
    setConsents(next);
    saveConsents(next);
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

  const onSaveServerConfig = async (payload: ConfigUpdateRequest) => {
    setServerStatus("Saving...");
    try {
      const res = await configApi.update(payload);
      if (res.ok) {
        setServerConfig(res.data);
        setServerStatus("Saved successfully");
      } else {
        setServerStatus(res.error ?? "Failed to save");
      }
    } catch (err) {
      setServerStatus("Failed to save");
    }
    setTimeout(() => setServerStatus(null), 2500);
  };

  const createNewProfile = async () => {
    if (!newProfile.name.trim()) return;

    const payload: ProfileUpsertRequest = {
      name: newProfile.name.trim(),
      description: newProfile.description.trim() || undefined,
      extensions: newProfile.extensions.trim() ? newProfile.extensions.split(",").map(e => e.trim()).filter(Boolean) : undefined,
      exclude_dirs: newProfile.exclude_dirs.trim() ? newProfile.exclude_dirs.split(",").map(d => d.trim()).filter(Boolean) : undefined,
    };

    try {
      const res = await configApi.saveProfile(payload);
      if (res.ok) {
        // Refresh profiles
        const prof = await configApi.listProfiles();
        if (prof.ok) setProfiles(prof.data.profiles || {});
        setNewProfile({ name: "", description: "", extensions: "", exclude_dirs: "" });
        setShowNewProfileDialog(false);
      }
    } catch (err) {
      console.error("Failed to create profile", err);
    }
  };

  return (
    <div className="p-8">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-6">
        {/* Header with user status */}
        <div className="p-8">
          <div className="flex items-center justify-between">
            <div>
              <Link href="/" className="text-sm text-gray-600 hover:text-gray-900 mb-2 inline-block">
                ← Back
              </Link>
              <h1 className="text-4xl font-bold text-gray-900 tracking-tight">Settings</h1>
              <p className="text-gray-600 mt-2">Manage your account settings</p>
            </div>
            <div className="bg-gray-50 border border-gray-200 rounded-lg px-4 py-3">
              {sessionLoading ? (
                <p className="text-sm text-gray-600">Loading...</p>
              ) : userSession ? (
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Logged in as</p>
                  <p className="text-sm font-semibold text-gray-900 mt-1">{userSession.email || userSession.user_id.slice(0, 8)}</p>
                </div>
              ) : (
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Status</p>
                  <p className="text-sm text-gray-600 mt-1">Guest mode</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Settings Cards Container */}
      <div className="space-y-6">
        {/* Theme & Appearance */}
        <Card className="bg-white rounded-xl shadow-sm border border-gray-200">
          <CardHeader className="border-b border-gray-200">
            <CardTitle className="text-xl font-bold text-gray-900">Appearance</CardTitle>
            <CardDescription className="text-gray-600">Customize the look and feel of the application</CardDescription>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            <div className="space-y-2">
              <Label htmlFor="theme-select" className="text-sm font-medium text-gray-900">Theme</Label>
              <Select value={theme} onValueChange={(value) => handleThemeChange(value as Theme)}>
                <SelectTrigger id="theme-select" className="border-gray-300">
                  <SelectValue placeholder="Select theme" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="light">Light</SelectItem>
                  <SelectItem value="dark">Dark</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-gray-500 mt-1">Choose between light and dark theme</p>
            </div>

            <div className="flex items-center justify-between py-3 border-t border-gray-200">
              <div className="space-y-0.5">
                <Label htmlFor="high-contrast" className="text-sm font-medium text-gray-900">High Contrast Mode</Label>
                <p className="text-xs text-gray-500">Increase contrast for better visibility</p>
              </div>
              <Switch
                id="high-contrast"
                checked={!!settings.enableHighContrast}
                onCheckedChange={(checked) => update({ enableHighContrast: checked })}
              />
            </div>
          </CardContent>
        </Card>

        {/* Preferences */}
        <Card className="bg-white rounded-xl shadow-sm border border-gray-200">
          <CardHeader className="border-b border-gray-200">
            <CardTitle className="text-xl font-bold text-gray-900">Preferences</CardTitle>
            <CardDescription className="text-gray-600">Application configuration and default settings</CardDescription>
          </CardHeader>
          <CardContent className="p-6 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="save-path" className="text-sm font-medium text-gray-900">Default save directory</Label>
              <div className="flex gap-2">
                <Input
                  id="save-path"
                  className="border-gray-300"
                  value={settings.defaultSavePath ?? ""}
                  onChange={(e) => update({ defaultSavePath: e.target.value })}
                  placeholder="/path/to/directory"
                />
                <Button variant="outline" onClick={selectDirectory} className="border-gray-300 hover:bg-gray-50">
                  Browse
                </Button>
              </div>
              <p className="text-xs text-gray-500 mt-1">Where files will be saved by default</p>
            </div>
          </CardContent>
          <CardFooter className="bg-gray-50 border-t border-gray-200 p-6">
            <div className="flex items-center gap-3">
              <Button onClick={onSave} className="bg-gray-900 text-white hover:bg-gray-800 shadow-sm">
                Save Changes
              </Button>
              {saveStatus && (
                <span className={`text-sm font-medium ${saveStatus.includes("success") ? "text-green-600" : "text-red-600"}`}>
                  {saveStatus}
                </span>
              )}
            </div>
          </CardFooter>
        </Card>

        {/* Privacy & Consent */}
        <Card className="bg-white rounded-xl shadow-sm border border-gray-200">
          <CardHeader className="border-b border-gray-200">
            <CardTitle className="text-xl font-bold text-gray-900">Privacy & Consent</CardTitle>
            <CardDescription className="text-gray-600">Manage your data sharing preferences and consent history</CardDescription>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between py-3">
                <div className="space-y-0.5">
                  <Label className="text-sm font-medium text-gray-900">Analytics & Usage Data</Label>
                  <p className="text-xs text-gray-500">Allow anonymous usage metrics to help improve the app</p>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant={settings.enableAnalytics ? "outline" : "default"}
                    onClick={grantAnalytics}
                    disabled={settings.enableAnalytics}
                    className={settings.enableAnalytics ? "border-gray-300" : "bg-gray-900 text-white hover:bg-gray-800"}
                  >
                    {settings.enableAnalytics ? "✓ Granted" : "Grant"}
                  </Button>
                </div>
              </div>

              <div className="border-t border-gray-200 pt-4">
                <div className="flex items-center justify-between mb-4">
                  <Label className="text-sm font-medium text-gray-900">Consent History</Label>
                  {consents.length > 0 && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowRevokeDialog(true)}
                      className="border-red-300 text-red-600 hover:bg-red-50"
                    >
                      Revoke All
                    </Button>
                  )}
                </div>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {consents.length === 0 ? (
                    <div className="border-2 border-dashed border-gray-200 rounded-lg p-8 text-center">
                      <p className="text-sm text-gray-500">No consent records found</p>
                    </div>
                  ) : (
                    consents.map((c) => (
                      <div
                        key={c.id}
                        className="flex items-start justify-between border border-gray-200 rounded-lg p-4 bg-gray-50"
                      >
                        <div className="space-y-1">
                          <p className="font-medium text-gray-900 capitalize">{c.purpose}</p>
                          <p className="text-xs text-gray-500">{new Date(c.timestamp).toLocaleString()}</p>
                          <span className={`inline-block text-xs px-2 py-1 rounded-full ${c.granted ? "bg-green-100 text-green-700 border border-green-300" : "bg-red-100 text-red-700 border border-red-300"}`}>
                            {c.granted ? "Granted" : "Revoked"}
                          </span>
                        </div>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => revokeConsent(c.id)}
                          className="border-gray-300 hover:bg-gray-50"
                        >
                          Remove
                        </Button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Scan Configuration */}
        <Card className="bg-white rounded-xl shadow-sm border border-gray-200">
          <CardHeader className="border-b border-gray-200">
            <CardTitle className="text-xl font-bold text-gray-900">Scan Configuration</CardTitle>
            <CardDescription className="text-gray-600">Backend settings for file scanning and profiles</CardDescription>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="active-profile" className="text-sm font-medium text-gray-900">Active Scan Profile</Label>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowNewProfileDialog(true)}
                  className="border-gray-300 hover:bg-gray-50"
                >
                  + New Profile
                </Button>
              </div>
              <Select
                value={serverConfig?.current_profile ?? ""}
                onValueChange={(value) => setServerConfig((c) => ({ ...(c ?? {}), current_profile: value }))}
              >
                <SelectTrigger id="active-profile" className="border-gray-300">
                  <SelectValue placeholder="Select profile" />
                </SelectTrigger>
                <SelectContent>
                  {profiles && Object.keys(profiles).length > 0 ? (
                    Object.entries(profiles).map(([name, data]) => (
                      <SelectItem key={name} value={name}>
                        {name} {data.description && `- ${data.description}`}
                      </SelectItem>
                    ))
                  ) : (
                    <SelectItem value="none" disabled>
                      No profiles available
                    </SelectItem>
                  )}
                </SelectContent>
              </Select>
              {serverConfig?.current_profile && profiles?.[serverConfig.current_profile] && (
                <div className="border border-gray-200 rounded-lg p-3 bg-gray-50 text-xs space-y-1">
                  <p className="text-gray-700">
                    <strong>Extensions:</strong>{" "}
                    {profiles[serverConfig.current_profile].extensions?.join(", ") || "All"}
                  </p>
                  <p className="text-gray-700">
                    <strong>Excluded:</strong>{" "}
                    {profiles[serverConfig.current_profile].exclude_dirs?.join(", ") || "None"}
                  </p>
                </div>
              )}
            </div>

            <div className="border-t border-gray-200 pt-4" />

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="max-file-size" className="text-sm font-medium text-gray-900">Max File Size (MB)</Label>
                <Input
                  id="max-file-size"
                  type="number"
                  className="border-gray-300"
                  value={(serverConfig?.max_file_size_mb ?? "") as any}
                  onChange={(e) =>
                    setServerConfig((c) => ({
                      ...(c ?? {}),
                      max_file_size_mb: e.target.value ? Number(e.target.value) : undefined,
                    }))
                  }
                  placeholder="10"
                />
              </div>

              <div className="flex items-center justify-between border border-gray-200 rounded-lg p-3 bg-gray-50">
                <div className="space-y-0.5">
                  <Label htmlFor="follow-symlinks" className="text-sm font-medium text-gray-900">Follow Symlinks</Label>
                  <p className="text-xs text-gray-500">Scan files referenced by symbolic links</p>
                </div>
                <Switch
                  id="follow-symlinks"
                  checked={!!serverConfig?.follow_symlinks}
                  onCheckedChange={(checked) => setServerConfig((c) => ({ ...(c ?? {}), follow_symlinks: checked }))}
                />
              </div>
            </div>
          </CardContent>
          <CardFooter className="bg-gray-50 border-t border-gray-200 p-6">
            <div className="flex items-center gap-3">
              <Button
                onClick={() =>
                  onSaveServerConfig({
                    current_profile: serverConfig?.current_profile ?? undefined,
                    max_file_size_mb: serverConfig?.max_file_size_mb ?? undefined,
                    follow_symlinks: serverConfig?.follow_symlinks ?? undefined,
                  })
                }
                className="bg-gray-900 text-white hover:bg-gray-800 shadow-sm"
              >
                Save Configuration
              </Button>
              {serverStatus && (
                <span className={`text-sm font-medium ${serverStatus.includes("success") ? "text-green-600" : "text-red-600"}`}>
                  {serverStatus}
                </span>
              )}
            </div>
          </CardFooter>
        </Card>
      </div>

      {/* Dialogs */}
      <Dialog open={showRevokeDialog} onOpenChange={setShowRevokeDialog}>
        <DialogContent className="bg-white">
          <DialogHeader>
            <DialogTitle className="text-gray-900">Revoke All Consents?</DialogTitle>
            <DialogDescription className="text-gray-600">
              This will revoke all consent records and disable analytics. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRevokeDialog(false)} className="border-gray-300">
              Cancel
            </Button>
            <Button onClick={revokeAllConsents} className="bg-red-600 text-white hover:bg-red-700">
              Revoke All
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showNewProfileDialog} onOpenChange={setShowNewProfileDialog}>
        <DialogContent className="bg-white">
          <DialogHeader>
            <DialogTitle className="text-gray-900">Create New Scan Profile</DialogTitle>
            <DialogDescription className="text-gray-600">Define a custom profile for file scanning preferences</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="profile-name" className="text-sm font-medium text-gray-900">Profile Name *</Label>
              <Input
                id="profile-name"
                className="border-gray-300"
                value={newProfile.name}
                onChange={(e) => setNewProfile({ ...newProfile, name: e.target.value })}
                placeholder="e.g., my_custom_profile"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="profile-desc" className="text-sm font-medium text-gray-900">Description</Label>
              <Input
                id="profile-desc"
                className="border-gray-300"
                value={newProfile.description}
                onChange={(e) => setNewProfile({ ...newProfile, description: e.target.value })}
                placeholder="Brief description"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="profile-ext" className="text-sm font-medium text-gray-900">File Extensions (comma-separated)</Label>
              <Input
                id="profile-ext"
                className="border-gray-300"
                value={newProfile.extensions}
                onChange={(e) => setNewProfile({ ...newProfile, extensions: e.target.value })}
                placeholder=".py, .js, .ts"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="profile-exclude" className="text-sm font-medium text-gray-900">Exclude Directories (comma-separated)</Label>
              <Input
                id="profile-exclude"
                className="border-gray-300"
                value={newProfile.exclude_dirs}
                onChange={(e) => setNewProfile({ ...newProfile, exclude_dirs: e.target.value })}
                placeholder="node_modules, .git, venv"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowNewProfileDialog(false);
                setNewProfile({ name: "", description: "", extensions: "", exclude_dirs: "" });
              }}
              className="border-gray-300"
            >
              Cancel
            </Button>
            <Button onClick={createNewProfile} disabled={!newProfile.name.trim()} className="bg-gray-900 text-white hover:bg-gray-800">
              Create Profile
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
