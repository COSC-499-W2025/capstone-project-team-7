"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { UserProfile, UpdateProfileRequest } from "@/lib/api.types";

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
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);

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

  // ---- avatar ----
  const pickAvatar = async () => {
    if (isElectron()) {
      try {
        const result = await window.desktop!.openFile({
          filters: [{ name: "Images", extensions: ["png", "jpg", "jpeg", "gif", "webp"] }],
        });
        if (result && result.length > 0) {
          // result is an array of file path strings; use the first one as local preview
          // TODO: upload to Supabase storage and use the returned URL
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
    const url = URL.createObjectURL(file);
    setAvatarPreview(url);
    // TODO: upload file to backend / Supabase storage
  };

  const removeAvatar = () => {
    setAvatarPreview(null);
  };

  // ---- save ----
  const handleSave = async () => {
    const token = getToken();
    if (!token) {
      setMessage({ type: "err", text: "Not authenticated. Please log in." });
      return;
    }

    setSaving(true);
    setMessage(null);

    const payload: UpdateProfileRequest = {};
    if (draft.display_name !== profile.display_name) payload.display_name = draft.display_name ?? undefined;
    if (draft.education !== profile.education) payload.education = draft.education ?? undefined;
    if (draft.career_title !== profile.career_title) payload.career_title = draft.career_title ?? undefined;
    if (draft.schema_url !== profile.schema_url) payload.schema_url = draft.schema_url ?? undefined;
    if (draft.drive_url !== profile.drive_url) payload.drive_url = draft.drive_url ?? undefined;
    // TODO: avatar_url should be the uploaded URL, not a local path
    if (avatarPreview !== (profile.avatar_url || null)) payload.avatar_url = avatarPreview ?? undefined;

    const res = await api.profile.update(token, payload);
    setSaving(false);

    if (res.ok) {
      setProfile(res.data);
      setDraft(res.data);
      if (res.data.avatar_url) setAvatarPreview(res.data.avatar_url);
      setMessage({ type: "ok", text: "Profile saved." });
    } else {
      setMessage({ type: "err", text: res.error ?? "Save failed." });
    }
  };

  // ---- cancel ----
  const handleCancel = () => {
    setDraft(profile);
    setAvatarPreview(profile.avatar_url || null);
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setMessage(null);
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
    if (!newPassword || !confirmPassword) {
      setMessage({ type: "err", text: "Please fill in all password fields." });
      return;
    }
    if (newPassword !== confirmPassword) {
      setMessage({ type: "err", text: "New passwords do not match." });
      return;
    }
    // TODO: call backend password-change endpoint when available
    setMessage({ type: "err", text: "Password change is not yet implemented on the backend." });
  };

  // ---- render ----
  if (loading) {
    return (
      <main className="flex items-center justify-center py-24">
        <p className="text-sm text-gray-500">Loading profile...</p>
      </main>
    );
  }

  return (
    <main className="pc-no-shadow space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Profile</h1>
          <p className="mt-1 text-sm text-gray-500">Manage your account settings</p>
        </div>
        <a href="/" className="pc-btn pc-btn-secondary text-sm">
          Back
        </a>
      </div>

      <div className="pc-divider" />

      {/* Feedback banner */}
      {message && (
        <div
          className={`pc-surface px-4 py-2 text-sm ${
            message.type === "ok"
              ? "border-green-600 text-green-400"
              : "border-red-600 text-red-400"
          }`}
        >
          {message.text}
        </div>
      )}

      {/* 2-column layout */}
      <div className="grid gap-8 md:grid-cols-[280px_1fr]">
        {/* -------- LEFT COLUMN -------- */}
        <section className="space-y-6">
          {/* Avatar */}
          <div className="pc-surface pc-dense flex flex-col items-center gap-3 p-6">
            <div className="relative h-28 w-28 overflow-hidden rounded-full border-2 border-current">
              {avatarPreview ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={avatarPreview}
                  alt="Avatar preview"
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center bg-gray-200 text-3xl font-bold text-gray-600">
                  {(draft.display_name ?? draft.email ?? "?").charAt(0).toUpperCase()}
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <button type="button" onClick={pickAvatar} className="pc-btn pc-btn-primary text-xs">
                Change
              </button>
              {avatarPreview && (
                <button type="button" onClick={removeAvatar} className="pc-btn pc-btn-secondary text-xs">
                  Remove
                </button>
              )}
            </div>

            {/* Hidden file input for browser fallback */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileInput}
            />
          </div>

          {/* Identity summary */}
          <div className="pc-surface pc-dense space-y-2 p-4">
            <p className="text-sm font-semibold">{draft.display_name || "No display name"}</p>
            <p className="text-xs text-gray-500">{draft.email || "No email"}</p>
            {draft.career_title && (
              <span className="pc-pill text-xs">{draft.career_title}</span>
            )}
          </div>

          {/* Logout */}
          <button
            type="button"
            onClick={handleLogout}
            className="pc-btn pc-btn-secondary w-full border-red-600 text-red-400 hover:bg-red-950"
          >
            Log out
          </button>
        </section>

        {/* -------- RIGHT COLUMN -------- */}
        <section className="space-y-6">
          {/* Basic info */}
          <fieldset className="pc-surface pc-dense space-y-4 p-5">
            <legend className="px-1 text-sm font-semibold">Basic Information</legend>

            <div>
              <label htmlFor="display_name" className="mb-1 block text-xs font-medium">
                Display Name
              </label>
              <input
                id="display_name"
                className="pc-input"
                value={draft.display_name ?? ""}
                onChange={(e) => set("display_name", e.target.value)}
              />
            </div>

            <div>
              <label htmlFor="email" className="mb-1 block text-xs font-medium">
                Email
              </label>
              <input
                id="email"
                className="pc-input opacity-60"
                value={draft.email ?? ""}
                readOnly
                title="Email is managed by your auth provider"
              />
              <p className="mt-1 text-xs text-gray-500">Managed by your auth provider</p>
            </div>

            <div>
              <label htmlFor="education" className="mb-1 block text-xs font-medium">
                Education
              </label>
              <input
                id="education"
                className="pc-input"
                placeholder="e.g. B.Sc. Computer Science"
                value={draft.education ?? ""}
                onChange={(e) => set("education", e.target.value)}
              />
            </div>

            <div>
              <label htmlFor="career_title" className="mb-1 block text-xs font-medium">
                Career Title
              </label>
              <input
                id="career_title"
                className="pc-input"
                placeholder="e.g. Software Engineer"
                value={draft.career_title ?? ""}
                onChange={(e) => set("career_title", e.target.value)}
              />
            </div>
          </fieldset>

          {/* Links */}
          <fieldset className="pc-surface pc-dense space-y-4 p-5">
            <legend className="px-1 text-sm font-semibold">Links &amp; Resources</legend>

            <div>
              <label htmlFor="schema_url" className="mb-1 block text-xs font-medium">
                Database Schema URL
              </label>
              <input
                id="schema_url"
                className="pc-input"
                type="url"
                placeholder="https://..."
                value={draft.schema_url ?? ""}
                onChange={(e) => set("schema_url", e.target.value)}
              />
            </div>

            <div>
              <label htmlFor="drive_url" className="mb-1 block text-xs font-medium">
                Team Google Drive URL
              </label>
              <input
                id="drive_url"
                className="pc-input"
                type="url"
                placeholder="https://drive.google.com/..."
                value={draft.drive_url ?? ""}
                onChange={(e) => set("drive_url", e.target.value)}
              />
            </div>
          </fieldset>

          {/* Password */}
          <fieldset className="pc-surface pc-dense space-y-4 p-5">
            <legend className="px-1 text-sm font-semibold">Change Password</legend>

            <div>
              <label htmlFor="current_password" className="mb-1 block text-xs font-medium">
                Current Password
              </label>
              <input
                id="current_password"
                className="pc-input"
                type="password"
                autoComplete="current-password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
              />
            </div>

            <div>
              <label htmlFor="new_password" className="mb-1 block text-xs font-medium">
                New Password
              </label>
              <input
                id="new_password"
                className="pc-input"
                type="password"
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </div>

            <div>
              <label htmlFor="confirm_password" className="mb-1 block text-xs font-medium">
                Confirm New Password
              </label>
              <input
                id="confirm_password"
                className="pc-input"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
            </div>

            <button
              type="button"
              className="pc-btn pc-btn-secondary text-sm"
              onClick={handlePasswordChange}
            >
              Update Password
            </button>
          </fieldset>

          {/* Action bar */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleSave}
              disabled={!dirty || saving}
              className="pc-btn pc-btn-primary text-sm"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
            <button
              type="button"
              onClick={handleCancel}
              disabled={!dirty}
              className="pc-btn pc-btn-secondary text-sm"
            >
              Cancel
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}
