"use client";

import { type ChangeEvent, useEffect, useRef, useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Section,
  SectionActions,
  SectionBody,
  SectionDescription,
  SectionHeader,
  SectionHeading,
  SectionInset,
  SectionTitle,
} from "@/components/ui/section";
import { StatCard } from "@/components/ui/stat-card";
import { updateProjectOverrides } from "@/lib/api/projects";
import { api } from "@/lib/api";
import { getStoredToken } from "@/lib/auth";
import { formatBytes } from "@/lib/format-utils";
import type { ProjectDetail, ProjectScanData } from "@/types/project";
import { Spinner } from "@/components/ui/spinner";
import { Image as ImageIcon, Upload, X } from "lucide-react";

interface ProjectDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  project: ProjectDetail | null;
  onProjectUpdate?: () => void;
  token?: string | null;
  onRoleUpdate?: (projectId: string, newRole: string) => void;
}

const ALLOWED_ROLES = ["author", "contributor", "lead", "maintainer", "reviewer"] as const;

function extractLanguageNames(rawLanguages: ProjectScanData["languages"], fallback: string[] = []): string[] {
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

function formatRoleLabel(role: string) {
  return role.charAt(0).toUpperCase() + role.slice(1);
}

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1.5">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </p>
      <p className="break-words text-sm text-foreground">{value}</p>
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
  const primaryContributor = project.primary_contributor || "Scanned project evidence";
  const contributionScore =
    project.contribution_score == null ? "Unranked" : project.contribution_score.toFixed(1);
  const userShare =
    project.user_commit_share == null ? null : `${Math.round(project.user_commit_share * 100)}% yours`;
  const scanTimestamp = project.scan_timestamp
    ? new Date(project.scan_timestamp).toLocaleString()
    : "Unavailable";

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-h-[88vh] max-w-6xl gap-0 overflow-hidden p-0">
        <div className="flex max-h-[88vh] flex-col">
          <DialogHeader className="px-6 pb-0 pt-6 text-left sm:px-7">
            <DialogTitle className="text-[1.75rem] font-semibold tracking-[-0.04em] text-foreground">
              {project.project_name}
            </DialogTitle>
            <DialogDescription className="break-all text-sm leading-6">
              {project.project_path}
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto px-6 pb-6 pt-5 sm:px-7 sm:pb-7">
            <div className="grid gap-5 xl:grid-cols-[minmax(0,1.18fr)_minmax(300px,0.82fr)]">
              <div className="space-y-5">
                <Section>
                  <SectionHeader>
                    <SectionHeading>
                      <SectionTitle>Overview</SectionTitle>
                      <SectionDescription>
                        Project metadata and contribution context without the nested detail boxes.
                      </SectionDescription>
                    </SectionHeading>
                  </SectionHeader>
                  <SectionBody className="space-y-5 pt-0">
                    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                      <StatCard variant="plain" label="Total Files" value={totalFiles.toLocaleString()} />
                      <StatCard variant="plain" label="Total Lines" value={totalLines.toLocaleString()} />
                      <StatCard variant="plain" label="Languages" value={languages.length} />
                      <StatCard variant="plain" label="Size" value={formatBytes(bytesProcessed)} />
                    </div>

                    <div className="grid gap-4 sm:grid-cols-2">
                      <DetailField label="Primary Contributor" value={primaryContributor} />
                      <DetailField
                        label="Contribution Score"
                        value={userShare ? `${contributionScore} · ${userShare}` : contributionScore}
                      />
                    </div>
                  </SectionBody>
                </Section>

                <RoleSection project={project} token={token} onRoleUpdate={onRoleUpdate} />

                <EvidenceSection project={project} token={token} />
              </div>

              <div className="space-y-5">
                <Section>
                  <SectionHeader>
                    <SectionHeading>
                      <SectionTitle>Thumbnail</SectionTitle>
                      <SectionDescription>
                        Upload or replace the visual used for this project.
                      </SectionDescription>
                    </SectionHeading>
                  </SectionHeader>
                  <SectionBody className="pt-0">
                    <ThumbnailSection project={project} onProjectUpdate={onProjectUpdate} />
                  </SectionBody>
                </Section>

                {languages.length > 0 && (
                  <Section>
                    <SectionHeader>
                      <SectionHeading>
                        <SectionTitle>Languages</SectionTitle>
                        <SectionDescription>Detected across the scanned project files.</SectionDescription>
                      </SectionHeading>
                    </SectionHeader>
                    <SectionBody className="pt-0">
                      <div className="flex flex-wrap gap-2">
                        {languages.map((lang) => (
                          <span
                            key={lang}
                            className="inline-flex items-center rounded-full bg-muted px-3 py-1 text-sm font-medium text-foreground"
                          >
                            {lang}
                          </span>
                        ))}
                      </div>
                    </SectionBody>
                  </Section>
                )}

                <Section>
                  <SectionHeader>
                    <SectionHeading>
                      <SectionTitle>Scan Metadata</SectionTitle>
                      <SectionDescription>Supporting metadata for the current scan record.</SectionDescription>
                    </SectionHeading>
                  </SectionHeader>
                  <SectionBody className="pt-0">
                    <div className="grid gap-4">
                      <SectionInset className="space-y-4">
                        <DetailField label="Scanned" value={scanTimestamp} />
                        <DetailField label="Path" value={project.project_path} />
                      </SectionInset>
                    </div>
                  </SectionBody>
                </Section>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function ThumbnailSection({
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

  const handleFileSelect = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setError("Please select an image file (JPG, PNG)");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setError("Image must be less than 5MB");
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
        setError(result.error || "Failed to upload thumbnail");
        return;
      }

      onProjectUpdate?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
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
        setError(result.error || "Failed to remove thumbnail");
        return;
      }

      onProjectUpdate?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove thumbnail");
    } finally {
      setUploading(false);
    }
  };

  const thumbnailUrl = project.thumbnail_url || project.user_overrides?.thumbnail_url;

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        <div className="relative flex h-36 w-36 shrink-0 items-center justify-center overflow-hidden rounded-[20px] bg-muted/75">
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
                className="absolute right-2 top-2 rounded-full bg-black/70 p-1.5 text-white transition-colors hover:bg-black/85 disabled:opacity-50"
                title="Remove thumbnail"
              >
                <X size={14} />
              </button>
            </>
          ) : (
            <div className="text-center text-muted-foreground">
              <ImageIcon size={30} className="mx-auto mb-2" />
              <span className="text-xs">No thumbnail</span>
            </div>
          )}

          {uploading && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/85">
              <Spinner size={24} className="text-primary" />
            </div>
          )}
        </div>

        <div className="min-w-0 flex-1 space-y-3">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp"
            onChange={handleFileSelect}
            className="hidden"
            disabled={uploading}
          />

          <div className="flex flex-wrap gap-2">
            <Button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              size="sm"
            >
              <Upload size={16} />
              {thumbnailUrl ? "Replace" : "Set Thumbnail"}
            </Button>
            {thumbnailUrl && !confirmingRemoval && (
              <Button
                onClick={() => setConfirmingRemoval(true)}
                disabled={uploading}
                variant="outline"
                size="sm"
              >
                Remove
              </Button>
            )}
          </div>

          <p className="text-xs text-muted-foreground">JPG, PNG, GIF, or WebP. Max 5MB.</p>

          {confirmingRemoval && thumbnailUrl && (
            <SectionInset className="space-y-3">
              <p className="text-sm text-foreground">Remove this project thumbnail?</p>
              <div className="flex flex-wrap gap-2">
                <Button onClick={handleRemoveThumbnail} disabled={uploading} variant="destructive" size="sm">
                  Yes, remove
                </Button>
                <Button
                  onClick={() => setConfirmingRemoval(false)}
                  disabled={uploading}
                  variant="outline"
                  size="sm"
                >
                  Cancel
                </Button>
              </div>
            </SectionInset>
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
      </div>
    </div>
  );
}

function RoleSection({
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

  useEffect(() => {
    setSelectedRole(project.role || project.user_overrides?.role || "");
  }, [project.role, project.user_overrides?.role]);

  const handleSaveRole = async () => {
    if (!token || !selectedRole) return;

    setSavingRole(true);
    setRoleError(null);
    try {
      await updateProjectOverrides(token, project.id, { role: selectedRole });
      onRoleUpdate?.(project.id, selectedRole);
      setIsEditingRole(false);
    } catch (err) {
      setRoleError(err instanceof Error ? err.message : "Failed to update role");
    } finally {
      setSavingRole(false);
    }
  };

  const handleCancelEdit = () => {
    setIsEditingRole(false);
    setSelectedRole(project.role || project.user_overrides?.role || "");
    setRoleError(null);
  };

  return (
    <Section>
      <SectionHeader>
        <SectionHeading>
          <SectionTitle>Your Role</SectionTitle>
          <SectionDescription>
            Record the role that best reflects how you contributed to this project.
          </SectionDescription>
        </SectionHeading>
        {!isEditingRole && token && (
          <SectionActions>
            <Button onClick={() => setIsEditingRole(true)} variant="outline" size="sm">
              Edit Role
            </Button>
          </SectionActions>
        )}
      </SectionHeader>
      <SectionBody className="space-y-4 pt-0">
        {isEditingRole ? (
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedRole}
              onChange={(event) => setSelectedRole(event.target.value)}
              className="h-10 min-w-[14rem] rounded-[14px] border border-border/70 bg-background/80 px-3 text-sm text-foreground focus:border-primary/40 focus:outline-none focus:ring-2 focus:ring-ring/35"
            >
              <option value="">Select a role...</option>
              {ALLOWED_ROLES.map((role) => (
                <option key={role} value={role}>
                  {formatRoleLabel(role)}
                </option>
              ))}
            </select>
            <Button onClick={handleSaveRole} disabled={savingRole || !selectedRole} size="sm">
              {savingRole ? "Saving..." : "Save"}
            </Button>
            <Button onClick={handleCancelEdit} variant="outline" size="sm">
              Cancel
            </Button>
          </div>
        ) : currentRole ? (
          <span className="inline-flex items-center rounded-full bg-muted px-3 py-1 text-sm font-medium text-foreground">
            {currentRole}
          </span>
        ) : (
          <p className="text-sm text-muted-foreground">No role set yet.</p>
        )}
        {roleError && <p className="text-sm text-destructive">{roleError}</p>}
      </SectionBody>
    </Section>
  );
}

function EvidenceSection({
  project,
  token,
}: {
  project: ProjectDetail;
  token?: string | null;
}) {
  const [evidence, setEvidence] = useState<string[]>(project.user_overrides?.evidence ?? []);
  const [newEvidenceItem, setNewEvidenceItem] = useState("");
  const [savingEvidence, setSavingEvidence] = useState(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);

  useEffect(() => {
    setEvidence(project.user_overrides?.evidence ?? []);
  }, [project.user_overrides?.evidence]);

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
      setEvidenceError(err instanceof Error ? err.message : "Failed to save evidence");
    } finally {
      setSavingEvidence(false);
    }
  };

  const handleRemoveEvidence = async (index: number) => {
    if (!token) return;

    const updated = evidence.filter((_, itemIndex) => itemIndex !== index);
    setSavingEvidence(true);
    setEvidenceError(null);
    try {
      await updateProjectOverrides(token, project.id, { evidence: updated });
      setEvidence(updated);
    } catch (err) {
      setEvidenceError(err instanceof Error ? err.message : "Failed to save evidence");
    } finally {
      setSavingEvidence(false);
    }
  };

  return (
    <Section>
      <SectionHeader>
        <SectionHeading>
          <SectionTitle>Evidence of Success</SectionTitle>
          <SectionDescription>
            Capture outcomes worth surfacing in resumes, portfolios, or interview stories.
          </SectionDescription>
        </SectionHeading>
      </SectionHeader>
      <SectionBody className="space-y-4 pt-0">
        {evidence.length === 0 ? (
          <p className="text-sm text-muted-foreground">No evidence added yet.</p>
        ) : (
          <div className="space-y-3">
            {evidence.map((item, index) => (
              <SectionInset key={`${item}-${index}`} className="flex items-start justify-between gap-3">
                <p className="min-w-0 flex-1 text-sm text-foreground">{item}</p>
                {token && (
                  <button
                    onClick={() => handleRemoveEvidence(index)}
                    disabled={savingEvidence}
                    className="shrink-0 text-sm text-muted-foreground transition-colors hover:text-destructive disabled:opacity-50"
                    aria-label="Remove evidence item"
                  >
                    Remove
                  </button>
                )}
              </SectionInset>
            ))}
          </div>
        )}

        {token && (
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <input
              type="text"
              value={newEvidenceItem}
              onChange={(event) => setNewEvidenceItem(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") handleAddEvidence();
              }}
              placeholder="e.g. Throughput improved 35%"
              className="h-10 flex-1 rounded-[14px] border border-border/70 bg-background/80 px-3 text-sm text-foreground focus:border-primary/40 focus:outline-none focus:ring-2 focus:ring-ring/35"
            />
            <Button onClick={handleAddEvidence} disabled={savingEvidence || !newEvidenceItem.trim()} size="sm">
              {savingEvidence ? "Saving..." : "Add evidence"}
            </Button>
          </div>
        )}

        {evidenceError && <p className="text-sm text-destructive">{evidenceError}</p>}
      </SectionBody>
    </Section>
  );
}
