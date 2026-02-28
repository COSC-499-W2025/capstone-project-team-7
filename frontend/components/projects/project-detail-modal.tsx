"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ProjectDetail } from "@/types/project";
import { useEffect, useRef, useState } from "react";
import { updateProjectOverrides, updateProjectRole } from "@/lib/api/projects";
import { api } from "@/lib/api";
import { getStoredToken } from "@/lib/auth";
import { 
  FileCode, 
  Code2, 
  GitBranch, 
  Sparkles, 
  FileText, 
  Image as ImageIcon,
  Loader2,
  Upload,
  Video,
  X
} from "lucide-react";

interface ProjectDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  project: ProjectDetail | null;
  onProjectUpdate?: () => void;
  token?: string | null;
  onRoleUpdate?: (projectId: string, newRole: string) => void;
}

type TabId = "overview" | "files" | "languages" | "git" | "skills" | "documents" | "media";

export function ProjectDetailModal({
  isOpen,
  onClose,
  project,
  onProjectUpdate,
  token,
  onRoleUpdate,
}: ProjectDetailModalProps) {
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  if (!project) return null;

  const scanData = project.scan_data || {};
  const files = scanData.files || [];
  
  // Handle languages as either array or object
  let languagesData: Record<string, any> = {};
  const rawLanguages = scanData.languages;
  if (rawLanguages && typeof rawLanguages === 'object') {
    if (Array.isArray(rawLanguages)) {
      // Convert array of language names to object format
      rawLanguages.forEach((lang: string) => {
        languagesData[lang] = { files: 0, lines: 0 };
      });
    } else {
      languagesData = rawLanguages;
    }
  }
  
  const gitAnalysis = scanData.git_analysis || {};
  const skillsAnalysis = scanData.skills_analysis || {};
  const documentsAnalysis = scanData.documents_analysis || [];
  const mediaAnalysis = scanData.media_analysis || [];

  // Simplified view - just overview
  const tabs = [
    { id: "overview" as TabId, label: "Project Details", icon: FileCode },
  ];

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-5xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold">{project.project_name}</DialogTitle>
          <p className="text-sm text-gray-500">{project.project_path}</p>
        </DialogHeader>

        {/* Simplified header - no tabs */}
        <div className="border-b border-gray-200 px-6 py-3">
          <h3 className="text-lg font-semibold text-gray-900">Project Overview</h3>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === "overview" && (
            <OverviewTab
              project={project}
              onProjectUpdate={onProjectUpdate}
              token={token}
              onRoleUpdate={onRoleUpdate}
            />
          )}
          {activeTab === "files" && <FilesTab files={files} />}
          {activeTab === "languages" && <LanguagesTab languages={languagesData} />}
          {activeTab === "git" && <GitTab gitAnalysis={gitAnalysis} />}
          {activeTab === "skills" && <SkillsTab skillsAnalysis={skillsAnalysis} />}
          {activeTab === "documents" && <DocumentsTab documents={documentsAnalysis} />}
          {activeTab === "media" && <MediaTab media={mediaAnalysis} />}
        </div>
      </DialogContent>
    </Dialog>
  );
}

const ALLOWED_ROLES = ["author", "contributor", "lead", "maintainer", "reviewer"] as const;

function ThumbnailSection({ project, onProjectUpdate }: { project: ProjectDetail; onProjectUpdate?: () => void }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmingRemoval, setConfirmingRemoval] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
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
    <div>
      <h3 className="text-sm font-semibold mb-2">Project Thumbnail</h3>
      <div className="flex items-start gap-4">
        <div className="relative w-32 h-32 bg-gray-100 rounded-lg border border-gray-200 overflow-hidden flex items-center justify-center">
          {thumbnailUrl ? (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={thumbnailUrl}
                alt={`${project.project_name} thumbnail`}
                className="w-full h-full object-cover"
              />
              <button
                onClick={() => setConfirmingRemoval(true)}
                disabled={uploading}
                className="absolute top-1 right-1 p-1 bg-black/60 text-white rounded-full hover:bg-black/80 transition-colors disabled:opacity-50"
                title="Remove thumbnail"
              >
                <X size={14} />
              </button>
            </>
          ) : (
            <div className="text-center text-gray-400">
              <ImageIcon size={32} className="mx-auto mb-1" />
              <span className="text-xs">No thumbnail</span>
            </div>
          )}

          {uploading && (
            <div className="absolute inset-0 bg-white/80 flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            </div>
          )}
        </div>

        <div className="flex flex-col gap-2">
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
            className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Upload size={16} />
            {thumbnailUrl ? "Replace" : "Set Thumbnail"}
          </button>

          <p className="text-xs text-gray-500">JPG, PNG, GIF, or WebP. Max 5MB.</p>

          {confirmingRemoval && thumbnailUrl && (
            <div className="rounded-md border border-red-200 bg-red-50 p-2">
              <p className="text-xs text-red-700">Remove this project thumbnail?</p>
              <div className="mt-2 flex gap-2">
                <button
                  onClick={handleRemoveThumbnail}
                  disabled={uploading}
                  className="rounded-md bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
                >
                  Yes, remove
                </button>
                <button
                  onClick={() => setConfirmingRemoval(false)}
                  disabled={uploading}
                  className="rounded-md border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {error && <p className="text-xs text-red-600">{error}</p>}
        </div>
      </div>
    </div>
  );
}

// Overview Tab
function OverviewTab({
  project,
  onProjectUpdate,
  token,
  onRoleUpdate,
}: {
  project: ProjectDetail;
  onProjectUpdate?: () => void;
  token?: string | null;
  onRoleUpdate?: (projectId: string, newRole: string) => void;
}) {
  const currentRole = project.role || project.user_overrides?.role || "";
  const [isEditingRole, setIsEditingRole] = useState(false);
  const [selectedRole, setSelectedRole] = useState(currentRole);
  const [savingRole, setSavingRole] = useState(false);
  const [roleError, setRoleError] = useState<string | null>(null);

  // Evidence state
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
      await updateProjectRole(token, project.id, selectedRole);
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
    const updated = evidence.filter((_, i) => i !== index);
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

  const scanData = project.scan_data || {};
  const summary = scanData.summary || {};
  const rawLanguages = scanData.languages;
  
  // Extract language names from various formats
  let languages: string[] = [];
  if (Array.isArray(rawLanguages)) {
    if (rawLanguages.length > 0 && typeof rawLanguages[0] === 'object') {
      // Array of objects with 'language' field
      languages = rawLanguages.map((lang: any) => lang.language || lang.name).filter(Boolean);
    } else {
      // Array of strings
      languages = rawLanguages;
    }
  } else if (typeof rawLanguages === 'object' && rawLanguages !== null) {
    // Object keyed by language name
    languages = Object.keys(rawLanguages);
  } else if (project.languages) {
    languages = project.languages;
  }
  
  const totalFiles = summary.total_files || project.total_files || 0;
  const totalLines = summary.total_lines || project.total_lines || 0;
  const bytesProcessed = summary.bytes_processed || 0;
  
  return (
    <div className="space-y-6">
      <ThumbnailSection project={project} onProjectUpdate={onProjectUpdate} />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total Files" value={totalFiles.toLocaleString()} />
        <StatCard label="Total Lines" value={totalLines.toLocaleString()} />
        <StatCard label="Languages" value={languages.length} />
        <StatCard label="Size" value={formatBytes(bytesProcessed)} />
      </div>

      {/* Role section */}
      <div>
        <h3 className="text-sm font-semibold mb-2">Your Role</h3>
        {isEditingRole ? (
          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
              className="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a role...</option>
              {ALLOWED_ROLES.map((r) => (
                <option key={r} value={r}>
                  {r.charAt(0).toUpperCase() + r.slice(1)}
                </option>
              ))}
            </select>
            <button
              onClick={handleSaveRole}
              disabled={savingRole || !selectedRole}
              className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {savingRole ? "Saving..." : "Save"}
            </button>
            <button
              onClick={handleCancelEdit}
              className="px-3 py-1 bg-gray-100 text-gray-700 text-sm rounded hover:bg-gray-200"
            >
              Cancel
            </button>
            {roleError && <p className="text-xs text-red-600 w-full mt-1">{roleError}</p>}
          </div>
        ) : (
          <div className="flex items-center gap-2">
            {currentRole ? (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                {currentRole}
              </span>
            ) : (
              <span className="text-sm text-gray-400">No role set</span>
            )}
            {token && (
              <button
                onClick={() => setIsEditingRole(true)}
                className="text-xs text-blue-600 hover:text-blue-800 underline"
              >
                Edit Role
              </button>
            )}
          </div>
        )}
      </div>

      {/* Evidence of Success section */}
      <div>
        <h3 className="text-sm font-semibold mb-2">Evidence of Success</h3>
        <ul className="space-y-1 mb-2">
          {evidence.map((item, idx) => (
            <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
              <span className="mt-0.5 text-gray-400">•</span>
              <span className="flex-1">{item}</span>
              {token && (
                <button
                  onClick={() => handleRemoveEvidence(idx)}
                  disabled={savingEvidence}
                  className="text-xs text-red-500 hover:text-red-700 disabled:opacity-50"
                  aria-label="Remove evidence item"
                >
                  ×
                </button>
              )}
            </li>
          ))}
          {evidence.length === 0 && (
            <li className="text-sm text-gray-400">No evidence added yet.</li>
          )}
        </ul>
        {token && (
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={newEvidenceItem}
              onChange={(e) => setNewEvidenceItem(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleAddEvidence(); }}
              placeholder="e.g. Throughput improved 35%"
              className="flex-1 text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleAddEvidence}
              disabled={savingEvidence || !newEvidenceItem.trim()}
              className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {savingEvidence ? "Saving…" : "Add"}
            </button>
          </div>
        )}
        {evidenceError && <p className="text-xs text-red-600 mt-1">{evidenceError}</p>}
      </div>

      {languages.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold mb-2">Languages Detected</h3>
          <div className="flex flex-wrap gap-2">
            {languages.map((lang) => (
              <span
                key={lang}
                className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
              >
                {lang}
              </span>
            ))}
          </div>
        </div>
      )}

      <div>
        <h3 className="text-sm font-semibold mb-2">Project Path</h3>
        <p className="text-sm text-gray-600 font-mono bg-gray-50 p-2 rounded">{project.project_path}</p>
      </div>
      
      {project.scan_timestamp && (
        <div>
          <h3 className="text-sm font-semibold mb-2">Scanned</h3>
          <p className="text-sm text-gray-600">{new Date(project.scan_timestamp).toLocaleString()}</p>
        </div>
      )}
    </div>
  );
}

// Files Tab
function FilesTab({ files }: { files: any[] }) {
  if (files.length === 0) {
    return <EmptyState message="No files found" />;
  }

  return (
    <div className="space-y-2">
      {files.slice(0, 100).map((file, idx) => (
        <div
          key={idx}
          className="p-3 bg-gray-50 rounded border border-gray-200 hover:bg-gray-100 transition-colors"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{file.path || file.file_path}</p>
              {file.language && (
                <span className="text-xs text-gray-500">{file.language}</span>
              )}
            </div>
            <div className="text-right ml-4">
              {file.lines && <p className="text-xs text-gray-500">{file.lines} lines</p>}
              {file.size_bytes && (
                <p className="text-xs text-gray-500">{formatBytes(file.size_bytes)}</p>
              )}
            </div>
          </div>
        </div>
      ))}
      {files.length > 100 && (
        <p className="text-sm text-gray-500 text-center py-2">
          Showing first 100 of {files.length} files
        </p>
      )}
    </div>
  );
}

// Languages Tab
function LanguagesTab({ languages }: { languages: Record<string, any> }) {
  const entries = Object.entries(languages);
  
  if (entries.length === 0) {
    return <EmptyState message="No language data available" />;
  }

  return (
    <div className="space-y-4">
      {entries.map(([lang, data]) => (
        <div key={lang} className="p-4 bg-gray-50 rounded border border-gray-200">
          <h3 className="font-semibold text-lg mb-2">{lang}</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {data.files && <StatCard label="Files" value={data.files} />}
            {data.lines && <StatCard label="Lines" value={data.lines.toLocaleString()} />}
            {data.bytes && <StatCard label="Size" value={formatBytes(data.bytes)} />}
            {data.percentage && <StatCard label="Percentage" value={`${data.percentage.toFixed(1)}%`} />}
          </div>
        </div>
      ))}
    </div>
  );
}

// Git Tab
function GitTab({ gitAnalysis }: { gitAnalysis: any }) {
  if (!gitAnalysis || Object.keys(gitAnalysis).length === 0) {
    return <EmptyState message="No git analysis available" />;
  }

  const commits = gitAnalysis.commits || [];
  const contributors = gitAnalysis.contributors || [];

  return (
    <div className="space-y-6">
      {contributors.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold mb-3">Contributors</h3>
          <div className="space-y-2">
            {contributors.map((contributor: any, idx: number) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <span className="font-medium">{contributor.name || contributor.email}</span>
                <span className="text-sm text-gray-600">{contributor.commits} commits</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {commits.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold mb-3">Recent Commits</h3>
          <div className="space-y-2">
            {commits.slice(0, 20).map((commit: any, idx: number) => (
              <div key={idx} className="p-3 bg-gray-50 rounded border border-gray-200">
                <p className="text-sm font-medium">{commit.message || commit.subject}</p>
                <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                  <span>{commit.author || commit.author_name}</span>
                  {commit.date && <span>{new Date(commit.date).toLocaleDateString()}</span>}
                  {commit.hash && <span className="font-mono">{commit.hash.substring(0, 7)}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Skills Tab
function SkillsTab({ skillsAnalysis }: { skillsAnalysis: any }) {
  if (!skillsAnalysis || !skillsAnalysis.skills) {
    return <EmptyState message="No skills analysis available" />;
  }

  const skills = skillsAnalysis.skills;
  const categories = Object.keys(skills);

  return (
    <div className="space-y-4">
      {categories.map((category) => (
        <div key={category} className="p-4 bg-gray-50 rounded border border-gray-200">
          <h3 className="font-semibold text-lg mb-3 capitalize">{category.replace(/_/g, " ")}</h3>
          <div className="flex flex-wrap gap-2">
            {skills[category].map((skill: string, idx: number) => (
              <span
                key={idx}
                className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// Documents Tab
function DocumentsTab({ documents }: { documents: any[] }) {
  if (documents.length === 0) {
    return <EmptyState message="No documents analyzed" />;
  }

  return (
    <div className="space-y-3">
      {documents.map((doc, idx) => (
        <div key={idx} className="p-4 bg-gray-50 rounded border border-gray-200">
          <h4 className="font-medium mb-2">{doc.file_name || doc.path}</h4>
          {doc.summary && <p className="text-sm text-gray-700 mb-2">{doc.summary}</p>}
          {doc.content && (
            <p className="text-xs text-gray-600 line-clamp-3">{doc.content}</p>
          )}
        </div>
      ))}
    </div>
  );
}

// Media Tab
function MediaTab({ media }: { media: any[] }) {
  if (media.length === 0) {
    return <EmptyState message="No media files analyzed" />;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {media.map((item, idx) => (
        <div key={idx} className="p-4 bg-gray-50 rounded border border-gray-200">
          <div className="flex items-start gap-3">
            {item.type === "image" ? <ImageIcon size={20} /> : <Video size={20} />}
            <div className="flex-1">
              <h4 className="font-medium text-sm">{item.file_name || item.path}</h4>
              {item.analysis && <p className="text-xs text-gray-600 mt-1">{item.analysis}</p>}
              {item.metadata && (
                <div className="mt-2 text-xs text-gray-500">
                  {item.metadata.duration && <span>Duration: {item.metadata.duration}s</span>}
                  {item.metadata.resolution && <span className="ml-2">{item.metadata.resolution}</span>}
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// Helper Components
function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="p-3 bg-white border border-gray-200 rounded">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-12">
      <p className="text-gray-500">{message}</p>
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}
