"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { UserProfile, UpdateProfileRequest } from "@/lib/api.types";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar } from "@/components/ui/avatar";
import { Label } from "@/components/ui/label";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** True when running inside the Electron renderer. */
function isElectron(): boolean {
  return typeof window !== "undefined" && Boolean(window.desktop);
}

/** Read the auth token stored by the login flow. */
function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const EMPTY_PROFILE: UserProfile = {
  user_id: "",
  display_name: "",
  email: "",
  education: "",
  career_title: "",
  avatar_url: "",
  schema_url: "",
  drive_url: "",
  updated_at: null,
};

export default function ProfilePage() {
  // ---- state ----
  const [profile, setProfile] = useState<UserProfile>(EMPTY_PROFILE);
  const [draft, setDraft] = useState<UserProfile>(EMPTY_PROFILE);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [fieldErrors, setFieldErrors] = useState<{ schema_url?: string; drive_url?: string }>({});

  // password fields (handled separately)
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  // ---- fetch profile on mount ----
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    api.profile.get(token).then((res) => {
      if (res.ok) {
        setProfile(res.data);
        setDraft(res.data);
        if (res.data.avatar_url) setAvatarPreview(res.data.avatar_url);
      }
      setLoading(false);
    });
  }, []);

  // ---- field helpers ----
  const set = useCallback(
    (field: keyof UserProfile, value: string) =>
      setDraft((prev) => ({ ...prev, [field]: value })),
    []
  );

  const dirty =
    draft.display_name !== profile.display_name ||
    draft.education !== profile.education ||
    draft.career_title !== profile.career_title ||
    draft.schema_url !== profile.schema_url ||
    draft.drive_url !== profile.drive_url ||
    avatarPreview !== (profile.avatar_url || null);

  // ---- validation helpers ----
  const MAX_AVATAR_BYTES = 5 * 1024 * 1024; // 5 MB

  const validateUrls = (): boolean => {
    const errors: { schema_url?: string; drive_url?: string } = {};
    const ghUrl = draft.schema_url?.trim();
    if (ghUrl) {
      try {
        new URL(ghUrl);
        if (!ghUrl.startsWith("https://github.com/")) {
          errors.schema_url = "GitHub URL must start with https://github.com/";
        }
      } catch {
        errors.schema_url = "Please enter a valid URL.";
      }
    }
    const driveUrl = draft.drive_url?.trim();
    if (driveUrl) {
      try {
        new URL(driveUrl);
        if (!driveUrl.startsWith("https://drive.google.com/")) {
          errors.drive_url = "Drive URL must start with https://drive.google.com/";
        }
      } catch {
        errors.drive_url = "Please enter a valid URL.";
      }
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // ---- avatar ----
  const pickAvatar = async () => {
    if (isElectron()) {
      try {
        const result = await window.desktop!.openFile({
          filters: [{ name: "Images", extensions: ["png", "jpg", "jpeg", "gif", "webp"] }],
        });
        if (result && result.length > 0) {
          setAvatarPreview(result[0]);
        }
      } catch {
        // user cancelled
      }
    } else {
      fileInputRef.current?.click();
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > MAX_AVATAR_BYTES) {
      setMessage({ type: "err", text: "Avatar must be under 5 MB." });
      return;
    }
    if (avatarPreview?.startsWith("blob:")) URL.revokeObjectURL(avatarPreview);
    const url = URL.createObjectURL(file);
    setAvatarPreview(url);
    setAvatarFile(file);
  };

  const removeAvatar = () => {
    if (avatarPreview?.startsWith("blob:")) URL.revokeObjectURL(avatarPreview);
    setAvatarPreview(null);
    setAvatarFile(null);
  };

  // ---- save ----
  const handleSave = async () => {
    const token = getToken();
    if (!token) {
      setMessage({ type: "err", text: "Not authenticated. Please log in." });
      return;
    }

    if (!validateUrls()) return;

    setSaving(true);
    setMessage(null);

    // Upload avatar file if one was selected
    if (avatarFile) {
      const uploadRes = await api.profile.uploadAvatar(token, avatarFile);
      if (!uploadRes.ok) {
        setSaving(false);
        setMessage({ type: "err", text: uploadRes.error ?? "Avatar upload failed." });
        return;
      }
      setAvatarFile(null);
    } else if (avatarPreview === null && profile.avatar_url) {
      // Avatar was removed — delete file from storage and clear URL
      await api.profile.deleteAvatar(token);
    }

    const payload: UpdateProfileRequest = {};
    if (draft.display_name !== profile.display_name) payload.display_name = draft.display_name ?? undefined;
    if (draft.education !== profile.education) payload.education = draft.education ?? undefined;
    if (draft.career_title !== profile.career_title) payload.career_title = draft.career_title ?? undefined;
    if (draft.schema_url !== profile.schema_url) payload.schema_url = draft.schema_url ?? undefined;
    if (draft.drive_url !== profile.drive_url) payload.drive_url = draft.drive_url ?? undefined;

    const res = await api.profile.update(token, payload);
    setSaving(false);

    if (res.ok) {
      setProfile(res.data);
      setDraft(res.data);
      if (res.data.avatar_url) setAvatarPreview(res.data.avatar_url);
      else setAvatarPreview(null);
      setMessage({ type: "ok", text: "Profile saved." });
    } else {
      setMessage({ type: "err", text: res.error ?? "Save failed." });
    }
  };

  // ---- cancel ----
  const handleCancel = () => {
    if (avatarPreview?.startsWith("blob:")) URL.revokeObjectURL(avatarPreview);
    setDraft(profile);
    setAvatarPreview(profile.avatar_url || null);
    setAvatarFile(null);
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setMessage(null);
    setFieldErrors({});
  };

  // ---- logout ----
  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user_id");
    localStorage.removeItem("email");
    window.location.href = "/";
  };

  // ---- password change ----
  const handlePasswordChange = async () => {
    const token = getToken();
    if (!token) {
      setMessage({ type: "err", text: "Not authenticated. Please log in." });
      return;
    }
    if (!currentPassword || !newPassword || !confirmPassword) {
      setMessage({ type: "err", text: "Please fill in all password fields." });
      return;
    }
    if (newPassword.length < 6) {
      setMessage({ type: "err", text: "New password must be at least 6 characters." });
      return;
    }
    if (newPassword !== confirmPassword) {
      setMessage({ type: "err", text: "New passwords do not match." });
      return;
    }

    const res = await api.profile.changePassword(token, currentPassword, newPassword);
    if (res.ok) {
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setMessage({ type: "ok", text: "Password updated successfully." });
    } else {
      setMessage({ type: "err", text: res.error ?? "Password change failed." });
    }
  };

  // ---- render ----
  if (loading) {
    return (
      <main className="flex items-center justify-center py-24">
        <p className="text-sm text-muted-foreground">Loading profile...</p>
      </main>
    );
  }

  return (
    <main className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[30px] leading-[36px] font-bold tracking-tight">Profile</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">Manage your account settings</p>
        </div>
        <Button
          variant="outline"
          className="rounded-full"
          onClick={() => window.history.back()}
        >
          Back
        </Button>
      </div>

      <hr className="border-border" />

      {/* Feedback banner */}
      {message && (
        <div
          role="alert"
          className={`rounded-[4px] border px-3 py-2 text-sm ${
            message.type === "ok"
              ? "border-green-600 text-green-700 bg-green-50"
              : "border-red-600 text-red-700 bg-red-50"
          }`}
        >
          {message.text}
        </div>
      )}

      {/* 2-column layout */}
      <div className="grid gap-6 md:grid-cols-[260px_1fr]">
        {/* -------- LEFT COLUMN -------- */}
        <div className="space-y-4">
          {/* Avatar */}
          <Card className="shadow-none">
            <CardContent className="flex flex-col items-center gap-3 p-4">
              <Avatar
                src={avatarPreview ?? undefined}
                alt="Avatar preview"
                fallback={(draft.display_name ?? draft.email ?? "?").charAt(0).toUpperCase()}
                className="h-28 w-28 border-2 border-border text-3xl font-bold"
              />

              <div className="flex gap-2">
                <Button size="sm" className="rounded-full" onClick={pickAvatar}>
                  Change
                </Button>
                {avatarPreview && (
                  <Button variant="outline" size="sm" className="rounded-full" onClick={removeAvatar}>
                    Remove
                  </Button>
                )}
              </div>

              {/* Hidden file input for browser fallback */}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                data-testid="avatar-file-input"
                onChange={handleFileInput}
              />
            </CardContent>
          </Card>

          {/* Identity summary */}
          <Card className="shadow-none">
            <CardContent className="space-y-1 p-4">
              <p className="text-sm font-semibold">{draft.display_name || "No display name"}</p>
              <p className="text-xs text-muted-foreground">{draft.email || "No email"}</p>
              {draft.career_title && (
                <span className="inline-block rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground">
                  {draft.career_title}
                </span>
              )}
            </CardContent>
          </Card>

          {/* Logout */}
          <Button
            variant="outline"
            className="w-full rounded-full border-red-500 text-red-600 hover:bg-red-50"
            onClick={handleLogout}
          >
            Log out
          </Button>
        </div>

        {/* -------- RIGHT COLUMN -------- */}
        <div className="space-y-4">
          {/* Basic info */}
          <Card className="shadow-none">
            <CardHeader className="p-4 pb-0">
              <CardTitle className="text-sm">Basic Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 p-4">
              <div className="space-y-1">
                <Label htmlFor="display_name">Display Name</Label>
                <Input
                  id="display_name"
                  className="rounded-[4px] shadow-none"
                  value={draft.display_name ?? ""}
                  onChange={(e) => set("display_name", e.target.value)}
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  className="rounded-[4px] shadow-none opacity-60"
                  value={draft.email ?? ""}
                  readOnly
                  title="Email is managed by your auth provider"
                />
                <p className="text-xs text-muted-foreground">Managed by your auth provider</p>
              </div>

              <div className="space-y-1">
                <Label htmlFor="education">Education</Label>
                <Input
                  id="education"
                  className="rounded-[4px] shadow-none"
                  placeholder="e.g. B.Sc. Computer Science"
                  value={draft.education ?? ""}
                  onChange={(e) => set("education", e.target.value)}
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="career_title">Career Title</Label>
                <Input
                  id="career_title"
                  className="rounded-[4px] shadow-none"
                  placeholder="e.g. Software Engineer"
                  value={draft.career_title ?? ""}
                  onChange={(e) => set("career_title", e.target.value)}
                />
              </div>
            </CardContent>
          </Card>

          {/* Links */}
          <Card className="shadow-none">
            <CardHeader className="p-4 pb-0">
              <CardTitle className="text-sm">Links &amp; Resources</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 p-4">
              <div className="space-y-1">
                <Label htmlFor="schema_url">GitHub Profile URL</Label>
                <Input
                  id="schema_url"
                  className="rounded-[4px] shadow-none"
                  type="url"
                  placeholder="https://github.com/username"
                  value={draft.schema_url ?? ""}
                  onChange={(e) => set("schema_url", e.target.value)}
                />
                {fieldErrors.schema_url && (
                  <p className="text-xs text-red-600">{fieldErrors.schema_url}</p>
                )}
              </div>

              <div className="space-y-1">
                <Label htmlFor="drive_url">Team Google Drive URL</Label>
                <Input
                  id="drive_url"
                  className="rounded-[4px] shadow-none"
                  type="url"
                  placeholder="https://drive.google.com/..."
                  value={draft.drive_url ?? ""}
                  onChange={(e) => set("drive_url", e.target.value)}
                />
                {fieldErrors.drive_url && (
                  <p className="text-xs text-red-600">{fieldErrors.drive_url}</p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Password */}
          <Card className="shadow-none">
            <CardHeader className="p-4 pb-0">
              <CardTitle className="text-sm">Change Password</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 p-4">
              <div className="space-y-1">
                <Label htmlFor="current_password">Current Password</Label>
                <Input
                  id="current_password"
                  className="rounded-[4px] shadow-none"
                  type="password"
                  autoComplete="current-password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="new_password">New Password</Label>
                <Input
                  id="new_password"
                  className="rounded-[4px] shadow-none"
                  type="password"
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="confirm_password">Confirm New Password</Label>
                <Input
                  id="confirm_password"
                  className="rounded-[4px] shadow-none"
                  type="password"
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>

              <Button
                variant="outline"
                size="sm"
                className="rounded-full"
                onClick={handlePasswordChange}
              >
                Update Password
              </Button>
            </CardContent>
          </Card>

          {/* Action bar */}
          <div className="flex gap-3">
            <Button
              className="rounded-full"
              onClick={handleSave}
              disabled={!dirty || saving}
            >
              {saving ? "Saving..." : "Save Changes"}
            </Button>
            <Button
              variant="outline"
              className="rounded-full"
              onClick={handleCancel}
              disabled={!dirty}
            >
              Cancel
            </Button>
          </div>
        </div>
      </div>
    </main>
  );
}
