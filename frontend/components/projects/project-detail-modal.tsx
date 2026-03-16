"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { StatCard } from "@/components/ui/stat-card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { ProjectDetail, ProjectScanData } from "@/types/project";
import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { updateProjectOverrides } from "@/lib/api/projects";
import { api } from "@/lib/api";
import { getStoredToken } from "@/lib/auth";
import { formatBytes } from "@/lib/format-utils";
import {
  ArrowUpRight,
  Braces,
  Check,
  Clock3,
  FileText,
  FolderTree,
  GitBranch,
  Image as ImageIcon,
  Loader2,
  Sparkles,
  PencilLine,
  Upload,
  X,
} from "lucide-react";

interface ProjectDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  project: ProjectDetail | null;
  onProjectUpdate?: () => void;
  token?: string | null;
  onRoleUpdate?: (projectId: string, newRole: string) => void;
}

const ALLOWED_ROLES = ["author", "contributor", "lead", "maintainer", "reviewer"] as const;
type ProjectModalTab = "overview" | "files" | "languages" | "git" | "skills" | "documents" | "media";

function extractLanguageNames(
  rawLanguages: ProjectScanData["languages"],
  fallback: string[] = [],
): string[] {
  if (Array.isArray(rawLanguages)) {
    return rawLanguages
      .map((lang) => {
        if (typeof lang === "string") return lang;
        if (lang && typeof lang === "object") {
          if (typeof lang.language === "string") return lang.language;
          if (typeof lang.name === "string") return lang.name;
        }
        return null;
      })
      .filter((lang): lang is string => Boolean(lang));
  }

  if (rawLanguages && typeof rawLanguages === "object") {
    return Object.keys(rawLanguages);
  }

  return fallback;
}

function formatContributionScore(score?: number) {
  if (score === undefined || score === null) return "Unranked";
  return score.toFixed(1);
}

function ProjectThumbnail({
  project,
  onProjectUpdate,
}: {
  project: ProjectDetail;
  onProjectUpdate?: () => void;
}) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmingRemoval, setConfirmingRemoval] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setError("Please select an image file (JPG, PNG, GIF, or WebP).");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setError("Image must be less than 5MB.");
      return;
    }

    setError(null);
    setConfirmingRemoval(false);
    setUploading(true);

    try {
      const token = getStoredToken();
      if (!token) {
        setError("Not authenticated. Please log in.");
        return;
      }

      const result = await api.projects.uploadThumbnail(token, project.id, file);
      if (!result.ok) {
        setError(result.error || "Failed to upload thumbnail.");
        return;
      }

      onProjectUpdate?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleRemoveThumbnail = async () => {
    setConfirmingRemoval(false);
    setUploading(true);
    setError(null);

    try {
      const token = getStoredToken();
      if (!token) {
        setError("Not authenticated. Please log in.");
        return;
      }

      const result = await api.projects.deleteThumbnail(token, project.id);
      if (!result.ok) {
        setError(result.error || "Failed to remove thumbnail.");
        return;
      }

      onProjectUpdate?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove thumbnail.");
    } finally {
      setUploading(false);
    }
  };

  const thumbnailUrl = project.thumbnail_url || project.user_overrides?.thumbnail_url;

  return (
    <section className="rounded-3xl border border-slate-200 bg-slate-50/70 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Thumbnail</p>
          <h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">Project cover</h3>
        </div>
      </div>

      <div className="mt-4 space-y-4">
        <div className="relative aspect-[4/3] overflow-hidden rounded-2xl border border-slate-200 bg-white">
          {thumbnailUrl ? (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={thumbnailUrl}
                alt={`${project.project_name} thumbnail`}
                className="h-full w-full object-cover"
              />
              <button
                onClick={() => setConfirmingRemoval(true)}
                disabled={uploading}
                className="absolute right-3 top-3 rounded-full bg-slate-950/70 p-1.5 text-white transition-colors hover:bg-slate-950 disabled:opacity-50"
                title="Remove thumbnail"
              >
                <X size={14} />
              </button>
            </>
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-slate-400">
              <ImageIcon size={28} />
              <p className="text-sm">No thumbnail set</p>
            </div>
          )}

          {uploading && (
            <div className="absolute inset-0 flex items-center justify-center bg-white/75">
              <Loader2 className="h-6 w-6 animate-spin text-slate-700" />
            </div>
          )}
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/gif,image/webp"
          onChange={handleFileSelect}
          className="hidden"
          disabled={uploading}
        />

        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-100 disabled:opacity-50"
        >
          <Upload size={16} />
          <span>{thumbnailUrl ? "Replace thumbnail" : "Upload thumbnail"}</span>
        </button>

        <p className="text-xs text-slate-500">Use JPG, PNG, GIF, or WebP. Maximum size: 5MB.</p>

        {confirmingRemoval && thumbnailUrl && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-3">
            <p className="text-sm text-red-700">Remove the current thumbnail?</p>
            <div className="mt-3 flex gap-2">
              <button
                onClick={handleRemoveThumbnail}
                disabled={uploading}
                className="rounded-full bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700 disabled:opacity-50"
              >
                Remove
              </button>
              <button
                onClick={() => setConfirmingRemoval(false)}
                disabled={uploading}
                className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {error && <p className="text-xs text-red-600">{error}</p>}
      </div>
    </section>
  );
}

function RoleAndEvidenceSection({
  project,
  token,
  onRoleUpdate,
}: {
  project: ProjectDetail;
  token?: string | null;
  onRoleUpdate?: (projectId: string, newRole: string) => void;
}) {
  const currentRole = project.role || project.user_overrides?.role || "";
  const [isEditingRole, setIsEditingRole] = useState(false);
  const [selectedRole, setSelectedRole] = useState(currentRole);
  const [savingRole, setSavingRole] = useState(false);
  const [roleError, setRoleError] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<string[]>(project.user_overrides?.evidence ?? []);
  const [newEvidenceItem, setNewEvidenceItem] = useState("");
  const [savingEvidence, setSavingEvidence] = useState(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);

  useEffect(() => {
    setSelectedRole(project.role || project.user_overrides?.role || "");
    setEvidence(project.user_overrides?.evidence ?? []);
  }, [project.role, project.user_overrides?.role, project.user_overrides?.evidence]);

  const handleSaveRole = async () => {
    if (!token || !selectedRole) return;
    setSavingRole(true);
    setRoleError(null);

    try {
      await updateProjectOverrides(token, project.id, { role: selectedRole });
      onRoleUpdate?.(project.id, selectedRole);
      setIsEditingRole(false);
    } catch (err) {
      setRoleError(err instanceof Error ? err.message : "Failed to update role.");
    } finally {
      setSavingRole(false);
    }
  };

  const handleAddEvidence = async () => {
    const trimmed = newEvidenceItem.trim();
    if (!token || !trimmed) return;

    const updated = [...evidence, trimmed];
    setSavingEvidence(true);
    setEvidenceError(null);

    try {
      await updateProjectOverrides(token, project.id, { evidence: updated });
      setEvidence(updated);
      setNewEvidenceItem("");
    } catch (err) {
      setEvidenceError(err instanceof Error ? err.message : "Failed to save evidence.");
    } finally {
      setSavingEvidence(false);
    }
  };

  const handleRemoveEvidence = async (index: number) => {
    if (!token) return;
    const updated = evidence.filter((_, i) => i !== index);
    setSavingEvidence(true);
    setEvidenceError(null);

    try {
      await updateProjectOverrides(token, project.id, { evidence: updated });
      setEvidence(updated);
    } catch (err) {
      setEvidenceError(err instanceof Error ? err.message : "Failed to save evidence.");
    } finally {
      setSavingEvidence(false);
    }
  };

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Context</p>
          <h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">Role and outcomes</h3>
        </div>
        {!isEditingRole && token && (
          <button
            onClick={() => setIsEditingRole(true)}
            className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100"
          >
            <PencilLine size={14} />
            Edit Role
          </button>
        )}
      </div>

      <div className="mt-5 grid gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Current role</p>
          {isEditingRole ? (
            <div className="mt-3 space-y-3">
              <select
                value={selectedRole}
                onChange={(event) => setSelectedRole(event.target.value)}
                className="w-full rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:border-slate-400 focus:outline-none"
              >
                <option value="">Select a role...</option>
                {ALLOWED_ROLES.map((role) => (
                  <option key={role} value={role}>
                    {role.charAt(0).toUpperCase() + role.slice(1)}
                  </option>
                ))}
              </select>
              <div className="flex gap-2">
                <button
                  onClick={handleSaveRole}
                  disabled={savingRole || !selectedRole}
                  className="inline-flex items-center gap-1 rounded-full bg-slate-950 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                >
                  <Check size={13} />
                  {savingRole ? "Saving..." : "Save"}
                </button>
                <button
                  onClick={() => {
                    setIsEditingRole(false);
                    setSelectedRole(currentRole);
                    setRoleError(null);
                  }}
                  className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
              </div>
              {roleError && <p className="text-xs text-red-600">{roleError}</p>}
            </div>
          ) : (
            <div className="mt-3">
              {currentRole ? (
                <span className="inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-700">
                  {currentRole}
                </span>
              ) : (
                <p className="text-sm text-slate-400">No role set</p>
              )}
            </div>
          )}
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Evidence of success</p>
            <span className="text-xs text-slate-400">{evidence.length} item{evidence.length === 1 ? "" : "s"}</span>
          </div>
          <div className="space-y-2">
            {evidence.length > 0 ? (
              evidence.map((item, index) => (
                <div
                  key={`${item}-${index}`}
                  className="flex items-start justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
                >
                  <p className="text-sm leading-6 text-slate-700">{item}</p>
                  {token && (
                    <button
                      onClick={() => handleRemoveEvidence(index)}
                      disabled={savingEvidence}
                      className="rounded-full p-1 text-slate-400 transition-colors hover:bg-white hover:text-red-600 disabled:opacity-50"
                      aria-label="Remove evidence item"
                    >
                      <X size={14} />
                    </button>
                  )}
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-sm text-slate-400">
                No evidence added yet.
              </div>
            )}
          </div>

          {token && (
            <div className="rounded-2xl border border-slate-200 bg-white p-3">
              <div className="flex flex-col gap-3 sm:flex-row">
                <input
                  type="text"
                  value={newEvidenceItem}
                  onChange={(event) => setNewEvidenceItem(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") handleAddEvidence();
                  }}
                  placeholder="Add a concise outcome or proof point"
                  className="flex-1 rounded-2xl border border-slate-200 px-3 py-2 text-sm text-slate-700 focus:border-slate-400 focus:outline-none"
                />
                <button
                  onClick={handleAddEvidence}
                  disabled={savingEvidence || !newEvidenceItem.trim()}
                  className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                >
                  {savingEvidence ? "Saving..." : "Add evidence"}
                </button>
              </div>
              {evidenceError && <p className="mt-2 text-xs text-red-600">{evidenceError}</p>}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function AnalysisEmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50 px-5 py-10 text-center">
      <p className="text-base font-semibold text-slate-900">{title}</p>
      <p className="mt-2 text-sm text-slate-500">{description}</p>
    </div>
  );
}

function FilesAnalysisTab({
  files,
}: {
  files: Array<{ path: string; language?: string; lines?: number; size_bytes?: number }>;
}) {
  if (files.length === 0) {
    return (
      <AnalysisEmptyState
        title="No file inventory"
        description="This project does not include file-level scan details."
      />
    );
  }

  return (
    <div className="space-y-3">
      {files.slice(0, 120).map((file, index) => (
        <div
          key={`${file.path}-${index}`}
          className="rounded-2xl border border-slate-200 bg-white px-4 py-3"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-slate-900">{file.path}</p>
              {file.language && <p className="mt-1 text-xs text-slate-500">{file.language}</p>}
            </div>
            <div className="shrink-0 text-right text-xs text-slate-500">
              {typeof file.lines === "number" && <p>{file.lines.toLocaleString()} lines</p>}
              {typeof file.size_bytes === "number" && file.size_bytes > 0 && (
                <p>{formatBytes(file.size_bytes)}</p>
              )}
            </div>
          </div>
        </div>
      ))}
      {files.length > 120 && (
        <p className="text-center text-xs text-slate-500">Showing the first 120 files.</p>
      )}
    </div>
  );
}

function LanguagesAnalysisTab({
  entries,
}: {
  entries: Array<{ name: string; files?: number; lines?: number; bytes?: number; percentage?: number }>;
}) {
  if (entries.length === 0) {
    return (
      <AnalysisEmptyState
        title="No language breakdown"
        description="Language-level analysis is not available for this project."
      />
    );
  }

  return (
    <div className="grid gap-3 md:grid-cols-2">
      {entries.map((entry) => (
        <div key={entry.name} className="rounded-3xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between gap-4">
            <h3 className="text-lg font-semibold tracking-tight text-slate-950">{entry.name}</h3>
            {typeof entry.percentage === "number" && (
              <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600">
                {entry.percentage.toFixed(1)}%
              </span>
            )}
          </div>
          <div className="mt-4 grid grid-cols-3 gap-3">
            <StatCard variant="plain" label="Files" value={entry.files ?? 0} />
            <StatCard variant="plain" label="Lines" value={(entry.lines ?? 0).toLocaleString()} />
            <StatCard
              variant="plain"
              label="Size"
              value={typeof entry.bytes === "number" && entry.bytes > 0 ? formatBytes(entry.bytes) : "n/a"}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function GitAnalysisTab({ gitAnalysis }: { gitAnalysis: unknown }) {
  const repos = Array.isArray(gitAnalysis)
    ? gitAnalysis.filter((entry): entry is Record<string, unknown> => typeof entry === "object" && entry !== null)
    : [];

  if (repos.length === 0) {
    return (
      <AnalysisEmptyState
        title="No git analysis"
        description="This project does not currently include repository contribution data."
      />
    );
  }

  return (
    <div className="space-y-3">
      {repos.map((repo, index) => {
        const repoName =
          typeof repo.path === "string"
            ? repo.path
            : typeof repo.name === "string"
              ? repo.name
              : `Repository ${index + 1}`;
        const commitCount =
          typeof repo.commit_count === "number"
            ? repo.commit_count.toLocaleString()
            : typeof repo.total_commits === "number"
              ? repo.total_commits.toLocaleString()
              : "n/a";

        return (
          <div key={`${repoName}-${index}`} className="rounded-3xl border border-slate-200 bg-white p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-900">{repoName}</p>
                {typeof repo.primary_author === "string" && (
                  <p className="mt-1 text-xs text-slate-500">Primary author: {repo.primary_author}</p>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                <StatCard variant="plain" label="Commits" value={commitCount} />
                <StatCard
                  variant="plain"
                  label="Contributors"
                  value={typeof repo.contributor_count === "number" ? repo.contributor_count : "n/a"}
                />
                <StatCard
                  variant="plain"
                  label="Your Share"
                  value={
                    typeof repo.user_commit_share === "number"
                      ? `${repo.user_commit_share.toFixed(1)}%`
                      : "n/a"
                  }
                />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SkillsAnalysisTab({ skillsAnalysis }: { skillsAnalysis: unknown }) {
  const skillsByCategory =
    skillsAnalysis && typeof skillsAnalysis === "object" && !Array.isArray(skillsAnalysis)
      ? ((skillsAnalysis as Record<string, unknown>).skills_by_category as Record<string, unknown[]> | undefined) ?? {}
      : {};

  if (Object.keys(skillsByCategory).length === 0) {
    return (
      <AnalysisEmptyState
        title="No skills analysis"
        description="No categorized skills were generated for this project."
      />
    );
  }

  return (
    <div className="space-y-4">
      {Object.entries(skillsByCategory).map(([category, skills]) => (
        <div key={category} className="rounded-3xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between gap-4">
            <h3 className="text-lg font-semibold tracking-tight text-slate-950">{category}</h3>
            <span className="text-xs text-slate-400">{skills.length} skills</span>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {skills.map((skill, index) => {
              const label =
                typeof skill === "string"
                  ? skill
                  : skill && typeof skill === "object" && typeof (skill as { name?: unknown }).name === "string"
                    ? (skill as { name: string }).name
                    : `Skill ${index + 1}`;

              return (
                <span
                  key={`${category}-${label}-${index}`}
                  className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-700"
                >
                  {label}
                </span>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

function DocumentsAnalysisTab({ documents }: { documents: unknown[] }) {
  if (documents.length === 0) {
    return (
      <AnalysisEmptyState
        title="No document analysis"
        description="No document summaries are available for this project."
      />
    );
  }

  return (
    <div className="space-y-3">
      {documents.map((document, index) => {
        const entry = typeof document === "object" && document !== null ? (document as Record<string, unknown>) : {};
        const title =
          typeof entry.file_name === "string"
            ? entry.file_name
            : typeof entry.path === "string"
              ? entry.path
              : `Document ${index + 1}`;
        const summary =
          typeof entry.summary === "string"
            ? entry.summary
            : typeof entry.content === "string"
              ? entry.content
              : "";

        return (
          <div key={`${title}-${index}`} className="rounded-3xl border border-slate-200 bg-white p-5">
            <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
            {summary && <p className="mt-2 text-sm leading-6 text-slate-600">{summary}</p>}
          </div>
        );
      })}
    </div>
  );
}

function MediaAnalysisTab({ media }: { media: unknown[] }) {
  if (media.length === 0) {
    return (
      <AnalysisEmptyState
        title="No media analysis"
        description="No image, video, or audio analysis is available for this project."
      />
    );
  }

  return (
    <div className="grid gap-3 md:grid-cols-2">
      {media.map((item, index) => {
        const entry = typeof item === "object" && item !== null ? (item as Record<string, unknown>) : {};
        const title =
          typeof entry.file_name === "string"
            ? entry.file_name
            : typeof entry.path === "string"
              ? entry.path
              : `Media ${index + 1}`;
        const analysis = typeof entry.analysis === "string" ? entry.analysis : "";
        const metadata =
          entry.metadata && typeof entry.metadata === "object" && !Array.isArray(entry.metadata)
            ? (entry.metadata as Record<string, unknown>)
            : {};

        return (
          <div key={`${title}-${index}`} className="rounded-3xl border border-slate-200 bg-white p-5">
            <div className="flex items-start gap-3">
              <ImageIcon className="mt-0.5 h-4 w-4 text-slate-400" />
              <div className="min-w-0">
                <h3 className="truncate text-sm font-semibold text-slate-900">{title}</h3>
                {analysis && <p className="mt-2 text-sm leading-6 text-slate-600">{analysis}</p>}
                <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
                  {typeof metadata.duration === "number" && <span>Duration: {metadata.duration}s</span>}
                  {typeof metadata.resolution === "string" && <span>{metadata.resolution}</span>}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function ProjectDetailModal({
  isOpen,
  onClose,
  project,
  onProjectUpdate,
  token,
  onRoleUpdate,
}: ProjectDetailModalProps) {
  const [activeTab, setActiveTab] = useState<ProjectModalTab>("overview");
  const projectId = project?.id ?? null;

  useEffect(() => {
    if (isOpen && projectId) {
      setActiveTab("overview");
    }
  }, [isOpen, projectId]);

  if (!project) return null;

  const scanData = (project.scan_data ?? {}) as ProjectScanData;
  const summary =
    scanData.summary && typeof scanData.summary === "object"
      ? scanData.summary
      : {};
  const languages = extractLanguageNames(scanData.languages, project.languages ?? []);
  const totalFiles = summary.total_files || project.total_files || 0;
  const totalLines = summary.total_lines || project.total_lines || 0;
  const bytesProcessed = summary.bytes_processed || 0;
  const files = Array.isArray(scanData.files)
    ? scanData.files
        .map((file) => {
          const entry = file as Record<string, unknown>;
          return {
            path:
              typeof entry.path === "string"
                ? entry.path
                : typeof entry.file_path === "string"
                  ? entry.file_path
                  : "",
            language: typeof entry.language === "string" ? entry.language : undefined,
            lines: typeof entry.lines === "number" ? entry.lines : undefined,
            size_bytes: typeof entry.size_bytes === "number" ? entry.size_bytes : undefined,
          };
        })
        .filter((file) => file.path.length > 0)
    : [];
  const languageEntries =
    Array.isArray(scanData.languages)
      ? scanData.languages
          .map((entry) => {
            if (typeof entry === "string") return { name: entry };
            if (entry && typeof entry === "object") {
              return {
                name:
                  typeof entry.language === "string"
                    ? entry.language
                    : typeof entry.name === "string"
                      ? entry.name
                      : "",
                files:
                  typeof entry.files === "number"
                    ? entry.files
                    : typeof entry.count === "number"
                      ? entry.count
                      : undefined,
                lines: typeof entry.lines === "number" ? entry.lines : undefined,
                bytes: typeof entry.bytes === "number" ? entry.bytes : undefined,
                percentage:
                  typeof entry.percentage === "number" ? entry.percentage : undefined,
              };
            }
            return { name: "" };
          })
          .filter((entry) => entry.name.length > 0)
      : scanData.languages && typeof scanData.languages === "object"
        ? Object.entries(scanData.languages)
            .map(([name, value]) => {
              const record =
                value && typeof value === "object" && !Array.isArray(value)
                  ? (value as Record<string, unknown>)
                  : {};
              return {
                name,
                files: typeof record.files === "number" ? record.files : undefined,
                lines: typeof record.lines === "number" ? record.lines : undefined,
                bytes: typeof record.bytes === "number" ? record.bytes : undefined,
                percentage: typeof record.percentage === "number" ? record.percentage : undefined,
              };
            })
        : [];
  const documentEntries = Array.isArray(scanData.document_analysis) ? scanData.document_analysis : [];
  const mediaEntries = Array.isArray(scanData.media_analysis) ? scanData.media_analysis : [];
  const tabClass = "mt-0 border-0 bg-transparent p-0 shadow-none";
  const analysisTabs = [
    { id: "overview" as const, label: "Overview", icon: Sparkles },
    { id: "files" as const, label: "Files", icon: FolderTree },
    { id: "languages" as const, label: "Languages", icon: Braces },
    { id: "git" as const, label: "Git", icon: GitBranch },
    { id: "skills" as const, label: "Skills", icon: Sparkles },
    { id: "documents" as const, label: "Documents", icon: FileText },
    { id: "media" as const, label: "Media", icon: ImageIcon },
  ];

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-h-[88vh] max-w-6xl overflow-hidden rounded-[32px] border border-slate-200 bg-white p-0">
        <DialogHeader className="border-b border-slate-200 bg-[linear-gradient(135deg,rgba(248,250,252,0.96),rgba(255,255,255,0.98))] px-8 py-6">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Quick View</p>
              <DialogTitle className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
                {project.project_name}
              </DialogTitle>
              <DialogDescription className="sr-only">
                Quick summary for {project.project_name}, including project metrics, role, evidence, and thumbnail controls.
              </DialogDescription>
              <p className="mt-2 truncate text-sm text-slate-500">{project.project_path}</p>
            </div>
            <a
              href={`/project?projectId=${project.id}`}
              className="inline-flex shrink-0 items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50"
            >
              <span>Open full analysis</span>
              <ArrowUpRight size={16} />
            </a>
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <StatCard variant="plain" label="Files" value={totalFiles.toLocaleString()} />
            <StatCard variant="plain" label="Lines" value={totalLines.toLocaleString()} />
            <StatCard variant="plain" label="Languages" value={languages.length} />
            <StatCard
              variant="plain"
              label="Contribution"
              value={formatContributionScore(project.contribution_score)}
            />
          </div>
        </DialogHeader>

        <div className="overflow-y-auto px-8 py-6">
          <Tabs
            defaultValue="overview"
            value={activeTab}
            onValueChange={(value) => setActiveTab(value as ProjectModalTab)}
            className="space-y-6"
          >
            <TabsList className="flex h-auto flex-wrap justify-start gap-2 rounded-3xl border border-slate-200 bg-slate-50 p-2">
              {analysisTabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <TabsTrigger
                    key={tab.id}
                    value={tab.id}
                    className="rounded-full border border-transparent px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500 transition-all hover:text-slate-800 data-[state=active]:border-slate-200 data-[state=active]:bg-white data-[state=active]:text-slate-950"
                  >
                    <Icon size={14} className="mr-1.5 shrink-0" />
                    {tab.label}
                  </TabsTrigger>
                );
              })}
            </TabsList>

            <TabsContent value="overview" className={tabClass}>
              <div className="grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(320px,0.9fr)]">
                <div className="space-y-6">
                  <section className="rounded-3xl border border-slate-200 bg-white p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Summary</p>
                        <h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">Project snapshot</h3>
                      </div>
                      {project.scan_timestamp && (
                        <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600">
                          <Clock3 size={13} />
                          <span>{new Date(project.scan_timestamp).toLocaleString()}</span>
                        </div>
                      )}
                    </div>

                    <div className="mt-5 grid gap-4 md:grid-cols-2">
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Project path</p>
                        <p className="mt-2 break-all text-sm font-medium text-slate-800">{project.project_path}</p>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Bytes processed</p>
                        <p className="mt-2 text-sm font-medium text-slate-800">{formatBytes(bytesProcessed)}</p>
                      </div>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                      {project.role && (
                        <span className="inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                          Role: {project.role}
                        </span>
                      )}
                      {languages.map((language) => (
                        <span
                          key={language}
                          className="inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700"
                        >
                          {language}
                        </span>
                      ))}
                      {languages.length === 0 && (
                        <span className="text-sm text-slate-400">No languages detected</span>
                      )}
                    </div>
                  </section>

                  <RoleAndEvidenceSection project={project} token={token} onRoleUpdate={onRoleUpdate} />
                </div>

                <div className="space-y-6">
                  <ProjectThumbnail project={project} onProjectUpdate={onProjectUpdate} />

                  <section className="rounded-3xl border border-slate-200 bg-white p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">At a glance</p>
                        <h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">Analysis coverage</h3>
                      </div>
                      <Sparkles className="h-4 w-4 text-slate-400" />
                    </div>

                    <div className="mt-5 grid gap-3">
                      <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                        <span className="text-sm text-slate-600">Files</span>
                        <span className="text-sm font-semibold text-slate-900">{files.length}</span>
                      </div>
                      <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                        <span className="text-sm text-slate-600">Documents</span>
                        <span className="text-sm font-semibold text-slate-900">{documentEntries.length}</span>
                      </div>
                      <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                        <span className="text-sm text-slate-600">Media</span>
                        <span className="text-sm font-semibold text-slate-900">{mediaEntries.length}</span>
                      </div>
                      <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                        <span className="inline-flex items-center gap-2 text-sm text-slate-600">
                          <FolderTree size={14} />
                          Git analysis
                        </span>
                        <span className="text-sm font-semibold text-slate-900">
                          {Array.isArray(scanData.git_analysis) ? scanData.git_analysis.length : 0}
                        </span>
                      </div>
                    </div>
                  </section>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="files" className={tabClass}>
              <FilesAnalysisTab files={files} />
            </TabsContent>

            <TabsContent value="languages" className={tabClass}>
              <LanguagesAnalysisTab entries={languageEntries} />
            </TabsContent>

            <TabsContent value="git" className={tabClass}>
              <GitAnalysisTab gitAnalysis={scanData.git_analysis} />
            </TabsContent>

            <TabsContent value="skills" className={tabClass}>
              <SkillsAnalysisTab skillsAnalysis={scanData.skills_analysis} />
            </TabsContent>

            <TabsContent value="documents" className={tabClass}>
              <DocumentsAnalysisTab documents={documentEntries} />
            </TabsContent>

            <TabsContent value="media" className={tabClass}>
              <MediaAnalysisTab media={mediaEntries} />
            </TabsContent>
          </Tabs>
        </div>
      </DialogContent>
    </Dialog>
  );
}
