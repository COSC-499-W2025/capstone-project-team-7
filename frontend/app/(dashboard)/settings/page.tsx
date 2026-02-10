"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
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
import { auth as authApi, getStoredToken, getStoredRefreshToken } from "@/lib/auth";
import { useAuth } from "@/hooks/use-auth";
import type { AuthSessionInfo } from "@/lib/auth";
import type { ConfigResponse, ProfilesResponse } from "@/lib/api.types";

export default function SettingsPage() {
  const router = useRouter();
  const { logout } = useAuth();
  
  // User session
  const [userSession, setUserSession] = useState<AuthSessionInfo | null>(null);
  const [sessionLoading, setSessionLoading] = useState(true);

  // Theme
  const [theme, setTheme] = useState<Theme>("dark");

  // Local preferences
  const [settings, setSettings] = useState<AppSettings>({});
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  // Consent management
  const [consentData, setConsentData] = useState<{ data_access: boolean; external_services: boolean }>({ data_access: false, external_services: false });

  // Scan configuration
  const [serverConfig, setServerConfig] = useState<ConfigResponse | null>(null);
  const [profiles, setProfiles] = useState<Record<string, any>>({});
  const [configLoading, setConfigLoading] = useState(false);
  const [configStatus, setConfigStatus] = useState<string | null>(null);

  // Profile creation/editing
  const [showProfileDialog, setShowProfileDialog] = useState(false);
  const [editingProfile, setEditingProfile] = useState<string | null>(null);
  const [profileForm, setProfileForm] = useState({
    name: "",
    description: "",
    extensions: [] as string[],
    exclude_dirs: [] as string[]
  });
  const [extensionsInput, setExtensionsInput] = useState("");
  const [excludeDirsInput, setExcludeDirsInput] = useState("");

  useEffect(() => {
    let cancelled = false;

    (async () => {
      // Load theme
      const savedTheme = loadTheme();
      if (!cancelled) {
        setTheme(savedTheme);
        applyTheme(savedTheme);
      }

      // Try to load user session (check if token exists and is valid)
      const hasSessionCredential = Boolean(getStoredToken() || getStoredRefreshToken());
      if (hasSessionCredential) {
        try {
          const sessionRes = await authApi.getSession();
          if (!cancelled) {
            if (sessionRes.ok) {
              setUserSession(sessionRes.data);
            } else {
              // Token invalid, clear it using logout hook
              logout();
              setUserSession(null);
            }
          }
        } catch {
          if (!cancelled) {
            logout();
            setUserSession(null);
          }
        } finally {
          if (!cancelled) setSessionLoading(false);
        }
      } else {
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

      // Try to load consent status from backend (only if authenticated)
      const storedToken = getStoredToken();
      if (storedToken) {
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
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  // Load config and profiles when user session changes
  useEffect(() => {
    if (!userSession) return;

    let cancelled = false;
    (async () => {
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
    })();

    return () => {
      cancelled = true;
    };
  }, [userSession]);

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
  };

  const handleLogout = () => {
    // Use the logout hook to clear authentication state
    logout();
    
    // Clear local settings state
    setUserSession(null);
    setConsentData({ data_access: false, external_services: false });
    setServerConfig(null);
    setProfiles({});
    
    // Redirect to login page
    router.push('/auth/login');
  };

  const handleProfileSwitch = async (profileName: string) => {
    if (!serverConfig) return;
    
    // Optimistically update UI
    setServerConfig({ ...serverConfig, current_profile: profileName });
    
    // Save the profile switch to backend
    setConfigLoading(true);
    try {
      const res = await configApi.update({
        current_profile: profileName,
        max_file_size_mb: serverConfig.max_file_size_mb,
        follow_symlinks: serverConfig.follow_symlinks,
      });
      
      if (res.ok) {
        setServerConfig(res.data);
        setConfigStatus(`Switched to profile: ${profileName}`);
        setTimeout(() => setConfigStatus(null), 2500);
      } else {
        // Revert on failure
        setServerConfig(serverConfig);
        setConfigStatus("Failed to switch profile");
        setTimeout(() => setConfigStatus(null), 2500);
      }
    } catch (err) {
      console.error("Failed to switch profile:", err);
      // Revert on failure
      setServerConfig(serverConfig);
      setConfigStatus("Failed to switch profile");
      setTimeout(() => setConfigStatus(null), 2500);
    } finally {
      setConfigLoading(false);
    }
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
      setTimeout(() => setConfigStatus(null), 2500);
    }
  };

  const openCreateProfileDialog = () => {
    setEditingProfile(null);
    setProfileForm({
      name: "",
      description: "",
      extensions: [],
      exclude_dirs: []
    });
    setExtensionsInput("");
    setExcludeDirsInput("");
    setShowProfileDialog(true);
  };

  const openEditProfileDialog = (profileName: string) => {
    const profile = profiles[profileName];
    if (!profile) return;

    setEditingProfile(profileName);
    setProfileForm({
      name: profileName,
      description: profile.description || "",
      extensions: profile.extensions || [],
      exclude_dirs: profile.exclude_dirs || []
    });
    setExtensionsInput((profile.extensions || []).join(", "));
    setExcludeDirsInput((profile.exclude_dirs || []).join(", "));
    setShowProfileDialog(true);
  };

  const handleSaveProfile = async () => {
    if (!profileForm.name.trim()) {
      alert("Profile name is required");
      return;
    }

    setConfigLoading(true);
    try {
      // Parse comma-separated inputs
      const extensions = extensionsInput
        .split(",")
        .map(e => e.trim())
        .filter(e => e.length > 0);
      
      const exclude_dirs = excludeDirsInput
        .split(",")
        .map(d => d.trim())
        .filter(d => d.length > 0);

      const res = await configApi.saveProfile({
        name: profileForm.name,
        description: profileForm.description || undefined,
        extensions: extensions.length > 0 ? extensions : undefined,
        exclude_dirs: exclude_dirs.length > 0 ? exclude_dirs : undefined
      });

      if (res.ok) {
        // Refresh profiles list
        const profilesRes = await configApi.listProfiles();
        if (profilesRes.ok) {
          setProfiles(profilesRes.data.profiles || {});
        }
        setShowProfileDialog(false);
        setConfigStatus(editingProfile ? "Profile updated successfully" : "Profile created successfully");
        setTimeout(() => setConfigStatus(null), 2500);
      } else {
        alert("Failed to save profile");
      }
    } catch (err) {
      console.error("Failed to save profile:", err);
      alert("Failed to save profile");
    } finally {
      setConfigLoading(false);
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
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleLogout}
                    className="mt-2 border-red-300 text-red-600 hover:bg-red-50"
                  >
                    Logout
                  </Button>
                </div>
               ) : (
                 <div>
                   <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Status</p>
                   <p className="text-sm text-gray-600 mt-1">Guest mode</p>
                   <p className="text-xs text-gray-500 mt-2">
                     <Link href="/auth/login" className="text-blue-600 hover:text-blue-700 underline">
                       Go to login page
                     </Link>
                   </p>
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
                  className="border-gray-300 text-gray-900"
                  value={settings.defaultSavePath ?? ""}
                  onChange={(e) => update({ defaultSavePath: e.target.value })}
                  placeholder="/path/to/directory"
                />
                <Button variant="outline" onClick={selectDirectory} className="border-gray-300 hover:bg-gray-50 text-gray-900">
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
                    <div className="flex items-center justify-between">
                      <Label htmlFor="profile-select" className="text-sm font-medium text-gray-900">Scan Profile</Label>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={openCreateProfileDialog}
                        className="border-gray-300 hover:bg-gray-50 text-gray-900"
                      >
                        Create Profile
                      </Button>
                    </div>
                    {Object.keys(profiles).length > 0 ? (
                      <>
                        <Select 
                          value={serverConfig.current_profile || "all"} 
                          onValueChange={handleProfileSwitch}
                          disabled={configLoading}
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
                        <p className="text-xs text-gray-500 mt-1">
                          {configLoading ? "Switching profile..." : "Changes are saved automatically when you switch profiles"}
                        </p>
                        {serverConfig.current_profile && profiles[serverConfig.current_profile] && (
                          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 space-y-2">
                            <div className="flex items-center justify-between">
                              <p className="text-xs font-medium text-gray-700">Profile Details</p>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => openEditProfileDialog(serverConfig.current_profile!)}
                                className="h-6 px-2 text-xs"
                              >
                                Edit
                              </Button>
                            </div>
                            {profiles[serverConfig.current_profile].extensions && profiles[serverConfig.current_profile].extensions.length > 0 && (
                              <div>
                                <p className="text-xs text-gray-600">Extensions:</p>
                                <p className="text-xs text-gray-900 font-mono">{profiles[serverConfig.current_profile].extensions.join(", ")}</p>
                              </div>
                            )}
                            {profiles[serverConfig.current_profile].exclude_dirs && profiles[serverConfig.current_profile].exclude_dirs.length > 0 && (
                              <div>
                                <p className="text-xs text-gray-600">Excluded Directories:</p>
                                <p className="text-xs text-gray-900 font-mono">{profiles[serverConfig.current_profile].exclude_dirs.join(", ")}</p>
                              </div>
                            )}
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                        <p className="text-sm text-yellow-800">No profiles found. Create your first scan profile to get started.</p>
                      </div>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="max-file-size" className="text-sm font-medium text-gray-900">Max File Size (MB)</Label>
                    <Input
                      id="max-file-size"
                      type="number"
                      className="border-gray-300 text-gray-900"
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
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-3">
                  <Button 
                    onClick={onSaveConfig} 
                    disabled={!serverConfig || configLoading}
                    className="bg-gray-900 text-white hover:bg-gray-800 shadow-sm"
                  >
                    {configLoading ? "Saving..." : "Save Settings"}
                  </Button>
                  {configStatus && (
                    <span className={`text-sm font-medium ${configStatus.includes("success") || configStatus.includes("Switched") ? "text-green-600" : "text-red-600"}`}>
                      {configStatus}
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500">Profile selection is saved automatically. This button saves file size and symlink settings.</p>
              </div>
            </CardFooter>
          </Card>
        )}

        {/* Privacy & Consent */}
        <Card className="bg-white rounded-xl shadow-sm border border-gray-200">
          <CardHeader className="border-b border-gray-200">
            <div className="flex items-center justify-between gap-3">
              <div>
                <CardTitle className="text-xl font-bold text-gray-900">Privacy & Consent</CardTitle>
                <CardDescription className="text-gray-600">Manage your data sharing preferences and consent history</CardDescription>
              </div>
              <Link href="/settings/consent">
                <Button variant="outline" className="border-gray-300 hover:bg-gray-50 text-gray-900">
                  Open consent page
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent className="p-6 space-y-4">
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-700">Data Access:</span>
                <span className={`text-sm font-medium ${consentData.data_access ? "text-green-600" : "text-gray-400"}`}>
                  {consentData.data_access ? "Granted" : "Not granted"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-700">External AI Services:</span>
                <span className={`text-sm font-medium ${consentData.external_services ? "text-green-600" : "text-gray-400"}`}>
                  {consentData.external_services ? "Granted" : "Not granted"}
                </span>
              </div>
            </div>
            <p className="text-xs text-gray-500">
              Use the dedicated consent page to update, withdraw, or review consent notices.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Dialogs */}
      <Dialog open={showProfileDialog} onOpenChange={setShowProfileDialog}>
        <DialogContent className="bg-white max-w-2xl">
          <DialogHeader>
            <DialogTitle className="text-gray-900">
              {editingProfile ? `Edit Profile: ${editingProfile}` : "Create New Scan Profile"}
            </DialogTitle>
            <DialogDescription className="text-gray-600">
              Configure file extensions and directories for this scan profile
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="profile-name" className="text-sm font-medium text-gray-900">Profile Name</Label>
              <Input
                id="profile-name"
                className="border-gray-300 text-gray-900"
                value={profileForm.name}
                onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })}
                placeholder="e.g., python_only, web_only"
                disabled={!!editingProfile}
              />
              <p className="text-xs text-gray-500">Unique identifier for this profile</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="profile-description" className="text-sm font-medium text-gray-900">Description</Label>
              <Input
                id="profile-description"
                className="border-gray-300 text-gray-900"
                value={profileForm.description}
                onChange={(e) => setProfileForm({ ...profileForm, description: e.target.value })}
                placeholder="e.g., Python projects only"
              />
              <p className="text-xs text-gray-500">Brief description of what this profile includes</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="profile-extensions" className="text-sm font-medium text-gray-900">File Extensions</Label>
              <Input
                id="profile-extensions"
                className="border-gray-300 text-gray-900"
                value={extensionsInput}
                onChange={(e) => setExtensionsInput(e.target.value)}
                placeholder=".py, .pyx, .pyi"
              />
              <p className="text-xs text-gray-500">Comma-separated list of file extensions to include</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="profile-exclude" className="text-sm font-medium text-gray-900">Excluded Directories</Label>
              <Input
                id="profile-exclude"
                className="border-gray-300 text-gray-900"
                value={excludeDirsInput}
                onChange={(e) => setExcludeDirsInput(e.target.value)}
                placeholder="node_modules, .git, __pycache__"
              />
              <p className="text-xs text-gray-500">Comma-separated list of directories to exclude</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowProfileDialog(false)} className="border-gray-300 text-gray-900">
              Cancel
            </Button>
            <Button 
              onClick={handleSaveProfile} 
              disabled={!profileForm.name.trim() || configLoading}
              className="bg-gray-900 text-white hover:bg-gray-800"
            >
              {configLoading ? "Saving..." : editingProfile ? "Update Profile" : "Create Profile"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
