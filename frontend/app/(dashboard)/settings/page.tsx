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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { loadSettings, saveSettings, AppSettings } from "@/lib/settings";
import { loadTheme, saveTheme, applyTheme, type Theme } from "@/lib/theme";
import { consent as consentApi, config as configApi, encryption as encryptionApi, secrets as secretsApi } from "@/lib/api";
import { auth as authApi, getStoredToken, getStoredRefreshToken } from "@/lib/auth";
import { useAuth } from "@/hooks/use-auth";
import { formatOperationError } from "@/lib/error-utils";
import type { AuthSessionInfo } from "@/lib/auth";
import type { ConfigResponse, ProfilesResponse, EncryptionStatus, SecretStatusItem } from "@/lib/api.types";
import { AlertTriangle, CheckCircle2, RefreshCw, XCircle } from "lucide-react";

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
  const [consentLoading, setConsentLoading] = useState(true);
  const [consentError, setConsentError] = useState<string | null>(null);

  // Scan configuration
  const [serverConfig, setServerConfig] = useState<ConfigResponse | null>(null);
  const [profiles, setProfiles] = useState<Record<string, any>>({});
  const [configLoading, setConfigLoading] = useState(false);
  const [configStatus, setConfigStatus] = useState<string | null>(null);

  // Encryption status
  const [encryptionStatus, setEncryptionStatus] = useState<EncryptionStatus | null>(null);
  const [encryptionLoading, setEncryptionLoading] = useState(true);
  const [encryptionError, setEncryptionError] = useState<string | null>(null);
  // External services / secrets
  const [secretsStatus, setSecretsStatus] = useState<SecretStatusItem[]>([]);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [apiKeySaving, setApiKeySaving] = useState(false);
  const [apiKeyStatus, setApiKeyStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [apiKeyVerifying, setApiKeyVerifying] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);

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
      const existingToken = getStoredToken();
      const existingRefreshToken = getStoredRefreshToken();
      if (existingToken || existingRefreshToken) {
        try {
          const sessionRes = await authApi.getSession();
          if (!cancelled && sessionRes.ok) {
            setUserSession(sessionRes.data);
          }
          // 401/403 errors are handled automatically by the auth:expired event
        } catch {
          // Network error — don't force logout
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

      // Load encryption status
      try {
        setEncryptionLoading(true);
        setEncryptionError(null);
        const res = await encryptionApi.status();
        if (!cancelled) {
          if (res.ok) {
            setEncryptionStatus(res.data);
          } else {
            setEncryptionError(res.error || "Failed to load encryption status");
          }
        }
      } catch (err) {
        if (!cancelled) {
          setEncryptionError(err instanceof Error ? err.message : "Failed to load encryption status");
        }
      } finally {
        if (!cancelled) setEncryptionLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  // Load config, profiles, and consent when user session changes
  useEffect(() => {
    if (!userSession) return;

    let cancelled = false;
    (async () => {
      try {
        setConsentLoading(true);
        setConsentError(null);

        const [configRes, profilesRes, consentRes, secretsRes] = await Promise.all([
          configApi.get(),
          configApi.listProfiles(),
          consentApi.get(), // ← Now called after session is validated
          secretsApi.getStatus(),
        ]);

        if (!cancelled) {
          if (configRes.ok) setServerConfig(configRes.data);
          if (profilesRes.ok) setProfiles(profilesRes.data.profiles || {});
          if (secretsRes.ok) setSecretsStatus(secretsRes.data.secrets || []);
          if (consentRes.ok) {
            setConsentData({
              data_access: consentRes.data.data_access,
              external_services: consentRes.data.external_services
            });
            setSettings((s) => ({ ...(s ?? {}), enableAnalytics: consentRes.data.external_services }));
          } else {
            setConsentError(
              formatOperationError(
                "load consent data",
                consentRes.error,
                "Failed to load consent data. Please try again.",
              ),
            );
          }
          setConsentLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setConsentLoading(false);
          setConsentError(
            formatOperationError(
              "load settings",
              err,
              "Failed to load settings. Check your connection and retry.",
            ),
          );
          console.error("Failed to load settings:", err);
        }
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
    setSaveStatus(
      ok
        ? "Saved successfully"
        : "Failed to save local preferences. Check file permissions and try again.",
    );
    setTimeout(() => setSaveStatus(null), 2500);

    try {
      if ((window as any).desktop?.saveSettings) {
        (window as any).desktop.saveSettings(settings);
      }
    } catch {}
  };

  const handleRetryLoadSettings = async () => {
    setConsentLoading(true);
    setConsentError(null);

    try {
      const [configRes, profilesRes, consentRes, secretsRes] = await Promise.all([
        configApi.get(),
        configApi.listProfiles(),
        consentApi.get(),
        secretsApi.getStatus(),
      ]);

      if (configRes.ok) setServerConfig(configRes.data);
      if (profilesRes.ok) setProfiles(profilesRes.data.profiles || {});
      if (secretsRes.ok) setSecretsStatus(secretsRes.data.secrets || []);
      if (consentRes.ok) {
        setConsentData({
          data_access: consentRes.data.data_access,
          external_services: consentRes.data.external_services
        });
        setSettings((s) => ({ ...(s ?? {}), enableAnalytics: consentRes.data.external_services }));
      } else {
        setConsentError(
          formatOperationError(
            "load consent data",
            consentRes.error,
            "Failed to load consent data. Please try again.",
          ),
        );
      }
    } catch (err) {
      setConsentError(
        formatOperationError(
          "retry loading settings",
          err,
          "Failed to reload settings. Please try again.",
        ),
      );
      console.error("Failed to retry loading settings:", err);
    } finally {
      setConsentLoading(false);
    }
  };

  const handleRetryEncryptionStatus = async () => {
    setEncryptionLoading(true);
    setEncryptionError(null);
    try {
      const res = await encryptionApi.status();
      if (res.ok) {
        setEncryptionStatus(res.data);
      } else {
        setEncryptionError(res.error || "Failed to load encryption status");
      }
    } catch (err) {
      setEncryptionError(err instanceof Error ? err.message : "Failed to load encryption status");
    } finally {
      setEncryptionLoading(false);
    }
  };

  const handleLogout = () => {
    // Use the logout hook to clear authentication state
    logout();

    // Clear local settings state
    setUserSession(null);
    setConsentData({ data_access: false, external_services: false });
    setServerConfig(null);
    setProfiles({});

    // Redirect is handled by the dashboard layout when isAuthenticated becomes false
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
        setConfigStatus(
          formatOperationError(
            `switch to profile \"${profileName}\"`,
            res.error,
            `Failed to switch to profile \"${profileName}\". Please try again.`,
          ),
        );
        setTimeout(() => setConfigStatus(null), 2500);
      }
    } catch (err) {
      console.error("Failed to switch profile:", err);
      // Revert on failure
      setServerConfig(serverConfig);
      setConfigStatus(
        formatOperationError(
          `switch to profile \"${profileName}\"`,
          err,
          `Failed to switch to profile \"${profileName}\". Please try again.`,
        ),
      );
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
        setConfigStatus(
          formatOperationError(
            "save scan configuration",
            res.error,
            "Failed to save scan configuration. Please try again.",
          ),
        );
      }
    } catch (err) {
      console.error("Failed to update config:", err);
      setConfigStatus(
        formatOperationError(
          "save scan configuration",
          err,
          "Failed to save scan configuration. Please try again.",
        ),
      );
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
      setConfigStatus("Profile name is required before saving.");
      setTimeout(() => setConfigStatus(null), 2500);
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
        setConfigStatus(
          formatOperationError(
            `save profile \"${profileForm.name}\"`,
            res.error,
            `Failed to save profile \"${profileForm.name}\". Please try again.`,
          ),
        );
        setTimeout(() => setConfigStatus(null), 2500);
      }
    } catch (err) {
      console.error("Failed to save profile:", err);
      setConfigStatus(
        formatOperationError(
          `save profile \"${profileForm.name}\"`,
          err,
          `Failed to save profile \"${profileForm.name}\". Please try again.`,
        ),
      );
      setTimeout(() => setConfigStatus(null), 2500);
    } finally {
      setConfigLoading(false);
    }
  };

  const encryptionReady = Boolean(encryptionStatus?.ready);
  const encryptionEnabled = Boolean(encryptionStatus?.enabled);
  const showEncryptionWarning = Boolean(encryptionStatus && !encryptionStatus.ready);
  const encryptionStatusLabel = encryptionReady ? "Encryption ready" : "Encryption needs attention";
  const encryptionStatusDescription = encryptionReady
    ? "Sensitive data stored by the app will be encrypted at rest."
    : encryptionEnabled
      ? "Encryption is configured but failed to initialize."
      : "Encryption is not configured. Secure storage is disabled until a key is provided.";
  const encryptionGuidance = encryptionEnabled
    ? "Verify ENCRYPTION_MASTER_KEY is a valid base64-encoded 32-byte key and restart the backend."
    : "Set ENCRYPTION_MASTER_KEY in the backend environment and restart the backend.";

  const openaiSecret = secretsStatus.find((s) => s.secret_key === "openai_api_key");

  const handleSaveApiKey = async () => {
    if (!apiKeyInput.trim()) return;
    setApiKeySaving(true);
    setApiKeyStatus(null);
    try {
      const res = await secretsApi.save({
        secret_key: "openai_api_key",
        value: apiKeyInput.trim(),
        provider: "openai",
      });
      if (res.ok) {
        setApiKeyInput("");
        setShowApiKey(false);
        setApiKeyStatus({ type: "success", message: "API key saved successfully" });
        const refreshed = await secretsApi.getStatus();
        if (refreshed.ok) setSecretsStatus(refreshed.data.secrets || []);
      } else {
        setApiKeyStatus({ type: "error", message: res.error || "Failed to save API key" });
      }
    } catch {
      setApiKeyStatus({ type: "error", message: "Network error" });
    } finally {
      setApiKeySaving(false);
      setTimeout(() => setApiKeyStatus(null), 4000);
    }
  };

  const handleVerifyApiKey = async () => {
    setApiKeyVerifying(true);
    setApiKeyStatus(null);
    try {
      const res = await secretsApi.verify();
      if (res.ok) {
        setApiKeyStatus({
          type: res.data.valid ? "success" : "error",
          message: res.data.message,
        });
      } else {
        setApiKeyStatus({ type: "error", message: res.error || "Verification failed" });
      }
    } catch {
      setApiKeyStatus({ type: "error", message: "Network error" });
    } finally {
      setApiKeyVerifying(false);
      setTimeout(() => setApiKeyStatus(null), 4000);
    }
  };

  const handleClearApiKey = async () => {
    setShowClearConfirm(false);
    setApiKeyStatus(null);
    try {
      const res = await secretsApi.remove("openai_api_key");
      if (res.ok) {
        setApiKeyStatus({ type: "success", message: "API key removed" });
        const refreshed = await secretsApi.getStatus();
        if (refreshed.ok) setSecretsStatus(refreshed.data.secrets || []);
      } else {
        setApiKeyStatus({ type: "error", message: res.error || "Failed to remove key" });
      }
    } catch {
      setApiKeyStatus({ type: "error", message: "Network error" });
    } finally {
      setTimeout(() => setApiKeyStatus(null), 4000);
    }
  };

  return (
    <div className="p-8 relative">
      {/* Error Banner */}
      {consentError && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-red-900">Failed to load settings</p>
              <p className="text-sm text-red-700 mt-1">{consentError}</p>
            </div>
            <Button 
              onClick={handleRetryLoadSettings}
              disabled={consentLoading}
              variant="outline"
              size="sm"
              className="border-red-300 text-red-600 hover:bg-red-50"
            >
              {consentLoading ? "Retrying..." : "Retry"}
            </Button>
          </div>
        </div>
      )}

      {/* Loading Overlay */}
      {consentLoading && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-2 border-primary border-t-transparent mx-auto mb-4" />
            <p className="text-sm text-muted-foreground">Loading settings...</p>
          </div>
        </div>
      )}

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
        <Tabs defaultValue="general" className="space-y-0">
          <TabsList className="h-auto w-full justify-start gap-2 rounded-xl border border-gray-200 bg-white p-2">
            <TabsTrigger value="general" className="rounded-lg px-4 py-2">General</TabsTrigger>
            <TabsTrigger value="security" className="rounded-lg px-4 py-2">Security & Privacy</TabsTrigger>
            <TabsTrigger value="scanning" className="rounded-lg px-4 py-2">Scanning</TabsTrigger>
          </TabsList>

          <TabsContent value="general" className="mt-6 border-0 bg-transparent p-0 shadow-none">
            <div className="space-y-6">
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

                  <div className="space-y-2 pt-2 border-t border-gray-200">
                    <Label htmlFor="contribution-user-name" className="text-sm font-medium text-gray-900">Contribution display name</Label>
                    <Input
                      id="contribution-user-name"
                      className="border-gray-300 text-gray-900"
                      value={settings.contributionUserName ?? ""}
                      onChange={(e) => update({ contributionUserName: e.target.value })}
                      placeholder="Jane Developer"
                    />
                    <p className="text-xs text-gray-500 mt-1">Optional name used when matching git contributions</p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="contribution-user-email" className="text-sm font-medium text-gray-900">Primary git email</Label>
                    <Input
                      id="contribution-user-email"
                      className="border-gray-300 text-gray-900"
                      value={settings.contributionUserEmail ?? ""}
                      onChange={(e) => update({ contributionUserEmail: e.target.value })}
                      placeholder="you@users.noreply.github.com"
                    />
                    <p className="text-xs text-gray-500 mt-1">Used for contribution ranking when commit emails differ from login email</p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="contribution-email-aliases" className="text-sm font-medium text-gray-900">Git email aliases</Label>
                    <Input
                      id="contribution-email-aliases"
                      className="border-gray-300 text-gray-900"
                      value={settings.contributionEmailAliases ?? ""}
                      onChange={(e) => update({ contributionEmailAliases: e.target.value })}
                      placeholder="work@example.com,personal@example.com"
                    />
                    <p className="text-xs text-gray-500 mt-1">Comma-separated emails to include in contribution matching</p>
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
            </div>
          </TabsContent>

          <TabsContent value="security" className="mt-6 border-0 bg-transparent p-0 shadow-none">
            <div className="space-y-6">
              <Card className="bg-white rounded-xl shadow-sm border border-gray-200">
                <CardHeader className="border-b border-gray-200">
                  <CardTitle className="text-xl font-bold text-gray-900">Security</CardTitle>
                  <CardDescription className="text-gray-600">Encryption status for sensitive data stored at rest</CardDescription>
                </CardHeader>
                <CardContent className="p-6 space-y-4">
                  {encryptionLoading ? (
                    <div className="flex items-center gap-3 text-gray-600">
                      <div className="animate-spin rounded-full h-6 w-6 border-2 border-gray-400 border-t-transparent" />
                      <p className="text-sm">Checking encryption status...</p>
                    </div>
                  ) : encryptionError ? (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <div className="flex items-center gap-2">
                            <XCircle className="h-5 w-5 text-red-600" />
                            <p className="text-sm font-medium text-red-900">Unable to fetch encryption status</p>
                          </div>
                          <p className="text-xs text-red-700 mt-1">{encryptionError}</p>
                        </div>
                        <Button
                          onClick={handleRetryEncryptionStatus}
                          variant="outline"
                          size="sm"
                          className="border-red-300 text-red-600 hover:bg-red-50"
                        >
                          Retry
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-start gap-3">
                          {encryptionReady ? (
                            <CheckCircle2 className="h-6 w-6 text-green-600" />
                          ) : (
                            <AlertTriangle className="h-6 w-6 text-amber-600" />
                          )}
                          <div>
                            <p className="text-sm font-semibold text-gray-900">{encryptionStatusLabel}</p>
                            <p className="text-xs text-gray-500 mt-1">{encryptionStatusDescription}</p>
                          </div>
                        </div>
                        <Button
                          onClick={handleRetryEncryptionStatus}
                          variant="outline"
                          size="sm"
                          className="border-gray-300 text-gray-700 hover:bg-gray-50"
                        >
                          <RefreshCw className="h-4 w-4 mr-2" />
                          Refresh
                        </Button>
                      </div>

                      {encryptionReady ? (
                        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                          <p className="text-sm text-green-900 font-medium">Encryption is active.</p>
                          <p className="text-xs text-green-700 mt-1">Your stored data will be encrypted using the current backend configuration.</p>
                        </div>
                      ) : (
                        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 space-y-2">
                          <p className="text-sm text-yellow-900 font-medium">Action required</p>
                          <p className="text-xs text-yellow-800">{encryptionGuidance}</p>
                          {encryptionStatus?.error && (
                            <p className="text-xs text-yellow-800">Details: {encryptionStatus.error}</p>
                          )}
                          <Link href="/settings/encryption" className="text-xs text-blue-600 hover:text-blue-700 underline">
                            View encryption setup instructions
                          </Link>
                        </div>
                      )}
                    </>
                  )}
                </CardContent>
              </Card>

              {userSession && (
                <Card className="bg-white rounded-xl shadow-sm border border-gray-200">
                  <CardHeader className="border-b border-gray-200">
                    <CardTitle className="text-xl font-bold text-gray-900">External Services</CardTitle>
                    <CardDescription className="text-gray-600">Manage API keys for AI-powered features</CardDescription>
                  </CardHeader>
                  <CardContent className="p-6 space-y-4">
                    {!consentData.external_services ? (
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <p className="text-sm text-blue-800">
                          Enable external services in Privacy & Consent below to configure API keys.
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        <div className="space-y-3">
                          <div className="flex items-center justify-between">
                            <Label className="text-sm font-medium text-gray-900">OpenAI API Key</Label>
                            <div className="flex items-center gap-2">
                              <span
                                className={`inline-block h-2 w-2 rounded-full ${
                                  openaiSecret ? "bg-green-500" : "bg-gray-300"
                                }`}
                              />
                              <span className="text-sm text-gray-600">
                                {openaiSecret ? "Configured" : "Not configured"}
                              </span>
                              {openaiSecret?.updated_at && (
                                <span className="text-xs text-gray-400 ml-2">
                                  Updated {new Date(openaiSecret.updated_at).toLocaleDateString()}
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="flex gap-2">
                            <div className="relative flex-1">
                              <Input
                                type={showApiKey ? "text" : "password"}
                                className="border-gray-300 text-gray-900 pr-10"
                                value={apiKeyInput}
                                onChange={(e) => setApiKeyInput(e.target.value)}
                                placeholder="sk-..."
                              />
                              <button
                                type="button"
                                onClick={() => setShowApiKey(!showApiKey)}
                                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-xs"
                              >
                                {showApiKey ? "Hide" : "Show"}
                              </button>
                            </div>
                            <Button
                              onClick={handleSaveApiKey}
                              disabled={!apiKeyInput.trim() || apiKeySaving}
                              className="bg-gray-900 text-white hover:bg-gray-800 shadow-sm"
                            >
                              {apiKeySaving ? "Saving..." : "Save Key"}
                            </Button>
                          </div>

                          <div className="flex gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={handleVerifyApiKey}
                              disabled={!openaiSecret || apiKeyVerifying}
                              className="border-gray-300 hover:bg-gray-50 text-gray-900"
                            >
                              {apiKeyVerifying ? "Verifying..." : "Verify Key"}
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setShowClearConfirm(true)}
                              disabled={!openaiSecret}
                              className="border-red-300 text-red-600 hover:bg-red-50"
                            >
                              Clear Key
                            </Button>
                          </div>

                          {apiKeyStatus && (
                            <p
                              className={`text-sm font-medium ${
                                apiKeyStatus.type === "success" ? "text-green-600" : "text-red-600"
                              }`}
                            >
                              {apiKeyStatus.message}
                            </p>
                          )}
                        </div>
                      </div>
                    )}
                  </CardContent>
                  <CardFooter className="bg-gray-50 border-t border-gray-200 p-6">
                    <p className="text-xs text-gray-500">
                      API keys are encrypted at rest and never returned after saving.
                    </p>
                  </CardFooter>
                </Card>
              )}

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
          </TabsContent>

          <TabsContent value="scanning" className="mt-6 border-0 bg-transparent p-0 shadow-none">
            <div className="space-y-6">
              {userSession ? (
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
                                      {name} {profile.description ? `- ${profile.description}` : ""}
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
                            onChange={(e) => setServerConfig({ ...serverConfig, max_file_size_mb: parseInt(e.target.value, 10) || 100 })}
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
              ) : (
                <Card className="bg-white rounded-xl shadow-sm border border-gray-200">
                  <CardHeader className="border-b border-gray-200">
                    <CardTitle className="text-xl font-bold text-gray-900">Scan Configuration</CardTitle>
                    <CardDescription className="text-gray-600">Sign in to manage scan profiles and analysis behavior</CardDescription>
                  </CardHeader>
                  <CardContent className="p-6">
                    <p className="text-sm text-gray-600">
                      Scan profile management is available after authentication.
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Clear API Key Confirmation Dialog */}
      <Dialog open={showClearConfirm} onOpenChange={setShowClearConfirm}>
        <DialogContent className="bg-white max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-gray-900">Clear API Key</DialogTitle>
            <DialogDescription className="text-gray-600">
              This will permanently remove your stored OpenAI API key. You will need to re-enter it to use AI features.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowClearConfirm(false)} className="border-gray-300 text-gray-900">
              Cancel
            </Button>
            <Button onClick={handleClearApiKey} className="bg-red-600 text-white hover:bg-red-700">
              Remove Key
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
