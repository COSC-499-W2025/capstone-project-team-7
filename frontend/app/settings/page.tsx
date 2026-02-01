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
import { loadSettings, saveSettings, AppSettings } from "@/lib/settings";
import { loadTheme, saveTheme, applyTheme, type Theme } from "@/lib/theme";
import { consent as consentApi, config as configApi } from "@/lib/api";
import { auth as authApi } from "@/lib/auth";
import type { AuthSessionInfo } from "@/lib/auth";
import type { ConfigResponse, ProfilesResponse } from "@/lib/api.types";

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
  const [showRevokeDialog, setShowRevokeDialog] = useState(false);
  const [consentData, setConsentData] = useState<{ data_access: boolean; external_services: boolean }>({ data_access: false, external_services: false });

  // Scan configuration
  const [serverConfig, setServerConfig] = useState<ConfigResponse | null>(null);
  const [profiles, setProfiles] = useState<Record<string, any>>({});
  const [configLoading, setConfigLoading] = useState(false);
  const [configStatus, setConfigStatus] = useState<string | null>(null);

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

      // Try to load consent status from backend
      try {
        const res = await consentApi.get();
        if (!cancelled && res.ok) {
          setConsentData({
            data_access: res.data.data_access,
            external_services: res.data.external_services
          });
          setSettings((s) => ({ ...(s ?? {}), enableAnalytics: res.data.external_services }));
        }
      } catch {
        // Backend not available, use local settings
      }

      // Try to load config and profiles if authenticated
      if (userSession) {
        try {
          const [configRes, profilesRes] = await Promise.all([
            configApi.get(),
            configApi.listProfiles()
          ]);
          if (!cancelled) {
            if (configRes.ok) setServerConfig(configRes.data);
            if (profilesRes.ok) setProfiles(profilesRes.data.profiles || {});
          }
        } catch {
          // Backend not available
        }
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

  const handleDataAccessChange = async (granted: boolean) => {
    setConsentData((prev) => ({ ...prev, data_access: granted }));
    try {
      await consentApi.set({ data_access: granted, external_services: consentData.external_services });
    } catch (err) {
      console.error("Failed to update consent:", err);
    }
  };

  const handleExternalServicesChange = async (granted: boolean) => {
    // External services requires data_access
    if (granted && !consentData.data_access) {
      alert("You must grant data access consent before enabling external services.");
      return;
    }
    
    setConsentData((prev) => ({ ...prev, external_services: granted }));
    update({ enableAnalytics: granted });
    saveSettings({ ...(settings ?? {}), enableAnalytics: granted });
    
    try {
      await consentApi.set({ data_access: consentData.data_access, external_services: granted });
    } catch (err) {
      console.error("Failed to update consent:", err);
    }
  };

  const revokeAllConsents = async () => {
    setConsentData({ data_access: false, external_services: false });
    update({ enableAnalytics: false });
    saveSettings({ ...(settings ?? {}), enableAnalytics: false });
    
    try {
      await consentApi.set({ data_access: false, external_services: false });
    } catch (err) {
      console.error("Failed to revoke consent:", err);
    }
    
    setShowRevokeDialog(false);
  };

  const onSaveConfig = async () => {
    if (!serverConfig) return;
    
    setConfigLoading(true);
    setConfigStatus(null);
    
    try {
      const res = await configApi.update({
        current_profile: serverConfig.current_profile,
        max_file_size_mb: serverConfig.max_file_size_mb,
        follow_symlinks: serverConfig.follow_symlinks,
      });
      
      if (res.ok) {
        setServerConfig(res.data);
        setConfigStatus("Configuration saved successfully");
      } else {
        setConfigStatus("Failed to save configuration");
      }
    } catch (err) {
      console.error("Failed to update config:", err);
      setConfigStatus("Failed to save configuration");
    } finally {
      setConfigLoading(false);
      setTimeout(() => setConfigStatus(null), 3000);
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

        {/* Scan Configuration */}
        {userSession && (
          <Card className="bg-white rounded-xl shadow-sm border border-gray-200">
            <CardHeader className="border-b border-gray-200">
              <CardTitle className="text-xl font-bold text-gray-900">Scan Configuration</CardTitle>
              <CardDescription className="text-gray-600">Configure scan profiles and analysis settings</CardDescription>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              {serverConfig ? (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="profile-select" className="text-sm font-medium text-gray-900">Scan Profile</Label>
                    <Select 
                      value={serverConfig.current_profile || "all"} 
                      onValueChange={(value) => setServerConfig({ ...serverConfig, current_profile: value })}
                    >
                      <SelectTrigger id="profile-select" className="border-gray-300">
                        <SelectValue placeholder="Select profile" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(profiles).map(([name, profile]: [string, any]) => (
                          <SelectItem key={name} value={name}>
                            {name} {profile.description ? `- ${profile.description}` : ''}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-gray-500 mt-1">Choose which files to analyze during scans</p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="max-file-size" className="text-sm font-medium text-gray-900">Max File Size (MB)</Label>
                    <Input
                      id="max-file-size"
                      type="number"
                      className="border-gray-300"
                      value={serverConfig.max_file_size_mb || 100}
                      onChange={(e) => setServerConfig({ ...serverConfig, max_file_size_mb: parseInt(e.target.value) || 100 })}
                      min={1}
                      max={1000}
                    />
                    <p className="text-xs text-gray-500 mt-1">Skip files larger than this size</p>
                  </div>

                  <div className="flex items-center justify-between py-3 border-t border-gray-200">
                    <div className="space-y-0.5">
                      <Label htmlFor="follow-symlinks" className="text-sm font-medium text-gray-900">Follow Symlinks</Label>
                      <p className="text-xs text-gray-500">Include symbolic links in file analysis</p>
                    </div>
                    <Switch
                      id="follow-symlinks"
                      checked={!!serverConfig.follow_symlinks}
                      onCheckedChange={(checked) => setServerConfig({ ...serverConfig, follow_symlinks: checked })}
                    />
                  </div>
                </>
              ) : (
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center text-gray-600">
                  Loading configuration...
                </div>
              )}
            </CardContent>
            <CardFooter className="bg-gray-50 border-t border-gray-200 p-6">
              <div className="flex items-center gap-3">
                <Button 
                  onClick={onSaveConfig} 
                  disabled={!serverConfig || configLoading}
                  className="bg-gray-900 text-white hover:bg-gray-800 shadow-sm"
                >
                  {configLoading ? "Saving..." : "Save Configuration"}
                </Button>
                {configStatus && (
                  <span className={`text-sm font-medium ${configStatus.includes("success") ? "text-green-600" : "text-red-600"}`}>
                    {configStatus}
                  </span>
                )}
              </div>
            </CardFooter>
          </Card>
        )}

        {/* Privacy & Consent */}
        <Card className="bg-white rounded-xl shadow-sm border border-gray-200">
          <CardHeader className="border-b border-gray-200">
            <CardTitle className="text-xl font-bold text-gray-900">Privacy & Consent</CardTitle>
            <CardDescription className="text-gray-600">Manage your data sharing preferences and consent history</CardDescription>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between py-3 border-b border-gray-200">
                <div className="space-y-0.5">
                  <Label className="text-sm font-medium text-gray-900">Data Access & File Analysis</Label>
                  <p className="text-xs text-gray-500">Allow file analysis and metadata storage in the database</p>
                </div>
                <Switch
                  checked={consentData.data_access}
                  onCheckedChange={handleDataAccessChange}
                />
              </div>

              <div className="flex items-center justify-between py-3">
                <div className="space-y-0.5">
                  <Label className="text-sm font-medium text-gray-900">External Services (AI/LLM)</Label>
                  <p className="text-xs text-gray-500">Enable AI-powered analysis using external LLM providers</p>
                  {!consentData.data_access && (
                    <p className="text-xs text-amber-600 mt-1">⚠️ Requires data access consent first</p>
                  )}
                </div>
                <Switch
                  checked={consentData.external_services}
                  onCheckedChange={handleExternalServicesChange}
                  disabled={!consentData.data_access}
                />
              </div>

              <div className="border-t border-gray-200 pt-4">
                <div className="flex items-center justify-between mb-3">
                  <Label className="text-sm font-medium text-gray-900">Current Status</Label>
                  {(consentData.data_access || consentData.external_services) && (
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
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-700">Data Access:</span>
                    <span className={`text-sm font-medium ${consentData.data_access ? "text-green-600" : "text-gray-400"}`}>
                      {consentData.data_access ? "✓ Granted" : "Not granted"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-700">External Services:</span>
                    <span className={`text-sm font-medium ${consentData.external_services ? "text-green-600" : "text-gray-400"}`}>
                      {consentData.external_services ? "✓ Granted" : "Not granted"}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Dialogs */}
      <Dialog open={showRevokeDialog} onOpenChange={setShowRevokeDialog}>
        <DialogContent className="bg-white">
          <DialogHeader>
            <DialogTitle className="text-gray-900">Revoke All Consents?</DialogTitle>
            <DialogDescription className="text-gray-600">
              This will revoke both data access and external services consent. This action cannot be undone.
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
    </div>
  );
}
