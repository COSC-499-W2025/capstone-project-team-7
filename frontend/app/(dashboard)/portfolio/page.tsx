"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Plus,
  Loader2,
  Edit2,
  Trash2,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getStoredToken } from "@/lib/auth";
import { api } from "@/lib/api";
import {
  listPortfolioItems,
  createPortfolioItem,
  updatePortfolioItem,
  deletePortfolioItem,
  generatePortfolioItem,
  getPortfolioChronology,
  getPortfolioSettings,
  refreshPortfolio,
} from "@/lib/api/portfolio";
import { getProjects, getSkills } from "@/lib/api/projects";
import type {
  PortfolioItem,
  PortfolioChronology,
  PortfolioRefreshResponse,
  PortfolioSettings,
  TimelineItem,
} from "@/types/portfolio";
import type { ProjectMetadata } from "@/types/project";
import type { UserProfile } from "@/lib/api.types";
import { PortfolioOverview } from "@/components/portfolio/portfolio-overview";
import { LoadingState } from "@/components/ui/loading-state";
import { EmptyState } from "@/components/ui/empty-state";

interface FormState {
  title: string;
  role: string;
  summary: string;
  evidence: string;
  thumbnail: string;
}

const EMPTY_FORM: FormState = {
  title: "",
  role: "",
  summary: "",
  evidence: "",
  thumbnail: "",
};

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "";
  try {
    return new Date(dateStr).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
}

function formatDateRange(start?: string | null, end?: string | null): string {
  if (!start && !end) return "Dates unknown";
  if (start && end) return `${start} – ${end}`;
  if (start) return `From ${start}`;
  return `Until ${end}`;
}

export default function PortfolioPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [chronology, setChronology] = useState<PortfolioChronology | null>(null);
  const [items, setItems] = useState<PortfolioItem[]>([]);
  const [skills, setSkills] = useState<string[]>([]);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [projects, setProjects] = useState<ProjectMetadata[]>([]);
  const [portfolioSettings, setPortfolioSettings] = useState<PortfolioSettings | null>(null);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<PortfolioItem | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [generating, setGenerating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [refreshResult, setRefreshResult] =
    useState<PortfolioRefreshResponse | null>(null);

  const fetchAll = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setError("Not authenticated. Please log in.");
      setLoading(false);
      setRefreshing(false);
      return;
    }

    try {
      setError(null);
      const [profileRes, itemsData, skillsData, chronologyData, projectsData, settingsData] =
        await Promise.allSettled([
          api.profile.get(token),
          listPortfolioItems(token),
          getSkills(token),
          getPortfolioChronology(token),
          getProjects(token),
          getPortfolioSettings(token),
        ]);

      if (profileRes.status === "fulfilled" && profileRes.value.ok) {
        setProfile(profileRes.value.data);
      }

      if (itemsData.status === "fulfilled") {
        setItems(itemsData.value);
      } else {
        const reason = itemsData.reason;
        setError(reason instanceof Error ? reason.message : "Failed to load portfolio items");
      }

      if (skillsData.status === "fulfilled") {
        setSkills(skillsData.value.skills);
      }

      if (chronologyData.status === "fulfilled") {
        setChronology(chronologyData.value);
        setTimeline(chronologyData.value.projects);
      }

      if (projectsData.status === "fulfilled") {
        setProjects(projectsData.value.projects);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load portfolio data");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleRefresh = async () => {
    const token = getStoredToken();
    if (!token) return;

    setRefreshing(true);
    setRefreshResult(null);
    setError(null);

    let refreshErr: string | null = null;

    try {
      const result = await refreshPortfolio(token);
      setRefreshResult(result);
    } catch (err) {
      refreshErr = err instanceof Error ? err.message : "Portfolio refresh failed";
    }

    await fetchAll();

    if (refreshErr) {
      setError(refreshErr);
    }
  };

  const openCreateDialog = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setSelectedProjectId("");
    setFormError(null);
    setDialogOpen(true);
  };

  const openEditDialog = (item: PortfolioItem) => {
    setEditing(item);
    setForm({
      title: item.title,
      role: item.role ?? "",
      summary: item.summary ?? "",
      evidence: item.evidence ?? "",
      thumbnail: item.thumbnail ?? "",
    });
    setSelectedProjectId("");
    setFormError(null);
    setDialogOpen(true);
  };

  const handleGenerateFromProject = async () => {
    if (!selectedProjectId) return;

    const token = getStoredToken();
    if (!token) return;

    setGenerating(true);
    setFormError(null);

    try {
      const result = await generatePortfolioItem(token, {
        project_id: selectedProjectId,
        persist: false,
      });
      setForm((current) => ({
        ...current,
        title: result.title || current.title,
        role: result.role || current.role,
        summary: result.summary || current.summary,
        evidence: result.evidence || current.evidence,
      }));
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to generate from project");
    } finally {
      setGenerating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this portfolio item? This cannot be undone.")) return;

    const token = getStoredToken();
    if (!token) return;

    setDeletingId(id);

    try {
      await deletePortfolioItem(token, id);
      setItems((current) => current.filter((item) => item.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete portfolio item");
    } finally {
      setDeletingId(null);
    }
  };

  const handleSave = async () => {
    if (!form.title.trim()) {
      setFormError("Title is required.");
      return;
    }

    const token = getStoredToken();
    if (!token) return;

    setSaving(true);
    setFormError(null);

    const payload = {
      title: form.title.trim(),
      role: form.role.trim() || null,
      summary: form.summary.trim() || null,
      evidence: form.evidence.trim() || null,
      thumbnail: form.thumbnail.trim() || null,
    };

    try {
      if (editing) {
        const updated = await updatePortfolioItem(token, editing.id, payload);
        setItems((current) =>
          current.map((item) => (item.id === updated.id ? updated : item)),
        );
      } else {
        const created = await createPortfolioItem(token, payload);
        setItems((current) => [created, ...current]);
      }
      setDialogOpen(false);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to save portfolio item");
    } finally {
      setSaving(false);
    }
  };

  const handleDialogClose = (open: boolean) => {
    if (!saving) {
      setDialogOpen(open);
    }
  };

  if (loading) {
    return (
      <div className="min-h-full bg-slate-50/80 p-4 sm:p-6 lg:p-8">
        <div className="portfolio-shell mx-auto max-w-[1500px] p-8">
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            <span className="ml-3 text-slate-500">Loading portfolio...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-slate-50/80 p-4 sm:p-6 lg:p-8">
      <div className="mx-auto max-w-[1500px] space-y-4">
        <div className="portfolio-shell overflow-hidden">
          <div className="border-b border-slate-200 px-5 py-5 sm:px-6 sm:py-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-700">
                  Career Snapshot
                </p>
                <h1 className="mt-1 text-3xl font-semibold tracking-tight text-slate-950">
                  Portfolio
                </h1>
                <p className="mt-2 text-sm text-slate-600">
                  {items.length === 0
                    ? "No portfolio items yet"
                    : `${items.length} item${items.length === 1 ? "" : "s"}`}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <RefreshCw size={18} className={refreshing ? "animate-spin" : ""} />
                  <span>{refreshing ? "Refreshing…" : "Refresh"}</span>
                </button>
                <button
                  onClick={openCreateDialog}
                  className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-slate-800"
                >
                  <Plus size={18} />
                  <span>New Item</span>
                </button>
              </div>
            </div>
          </div>

          {error && (
            <div className="mx-5 mt-5 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm sm:mx-6">
              <div className="flex">
                <svg className="h-5 w-5 flex-shrink-0 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">Error</h3>
                  <p className="mt-1 text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          {refreshResult && (
            <div className="mx-5 mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm sm:mx-6">
              <div className="flex items-start justify-between gap-3">
                <div className="flex gap-3">
                  <svg className="mt-0.5 h-5 w-5 flex-shrink-0 text-emerald-500" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <div>
                    <h3 className="text-sm font-medium text-emerald-800">Portfolio refreshed</h3>
                    <p className="mt-0.5 text-sm text-emerald-700">
                      {refreshResult.projects_scanned} project{refreshResult.projects_scanned !== 1 ? "s" : ""} scanned
                      {" · "}
                      {refreshResult.total_files} file{refreshResult.total_files !== 1 ? "s" : ""} indexed
                    </p>
                    {refreshResult.dedup_report &&
                      refreshResult.dedup_report.summary.duplicate_groups_count > 0 && (
                        <p className="mt-1 text-sm text-emerald-700">
                          {refreshResult.dedup_report.summary.duplicate_groups_count} duplicate group
                          {refreshResult.dedup_report.summary.duplicate_groups_count !== 1 ? "s" : ""} found across projects
                          {" ("}
                          {(refreshResult.dedup_report.summary.total_wasted_bytes / 1024).toFixed(1)} KB wasted
                          {")"}
                        </p>
                      )}
                    {refreshResult.dedup_report &&
                      refreshResult.dedup_report.summary.duplicate_groups_count === 0 && (
                        <p className="mt-1 text-sm text-emerald-700">
                          No cross-project duplicates detected.
                        </p>
                      )}
                  </div>
                </div>
                <button
                  onClick={() => setRefreshResult(null)}
                  className="flex-shrink-0 text-emerald-500 hover:text-emerald-700"
                  aria-label="Dismiss"
                >
                  <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
              </div>
            </div>
          )}

          <div className="px-5 pb-5 pt-5 sm:px-6 sm:pb-6">
            <Tabs defaultValue="overview" className="space-y-4">
              <TabsList className="mb-0 h-auto w-full justify-start gap-2 overflow-x-auto rounded-2xl border border-slate-200 bg-slate-50/80 p-2 text-slate-500">
                <TabsTrigger value="overview" className="rounded-xl">
                  Overview
                </TabsTrigger>
                <TabsTrigger value="items" className="rounded-xl">
                  Portfolio Items
                </TabsTrigger>
                <TabsTrigger value="timeline" className="rounded-xl">
                  Project Timeline
                </TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="mt-0 border-0 bg-transparent p-0 shadow-none">
                <PortfolioOverview
                  profile={profile}
                  chronology={chronology}
                  projects={projects}
                  skills={skills}
                />
              </TabsContent>

              <TabsContent value="items" className="mt-0 border-0 bg-transparent p-0 shadow-none">
                <div className="portfolio-panel p-4 sm:p-5">
                  {items.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 py-16 text-center">
                      <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-white">
                        <Briefcase className="h-6 w-6 text-slate-400" />
                      </div>
                      <p className="mb-2 text-slate-600">No portfolio items yet</p>
                      <p className="mb-6 text-sm text-slate-500">
                        Create your first portfolio item or generate one from a project.
                      </p>
                      <button
                        onClick={openCreateDialog}
                        className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-slate-800"
                      >
                        <Plus size={18} />
                        New Item
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {items.map((item) => (
                        <div
                          key={item.id}
                          className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 transition-colors hover:border-slate-300 hover:bg-white"
                        >
                          <div className="flex items-start justify-between gap-4">
                            {item.thumbnail && (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img
                                src={item.thumbnail}
                                alt={item.title}
                                className="h-16 w-16 flex-shrink-0 rounded-xl border border-slate-200 object-cover"
                                onError={(e) => {
                                  (e.currentTarget as HTMLImageElement).style.display = "none";
                                }}
                              />
                            )}
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-semibold text-slate-950">{item.title}</p>
                              {item.role && <p className="mt-0.5 text-xs text-slate-500">{item.role}</p>}
                              {item.summary && (
                                <p className="mt-2 line-clamp-2 text-sm text-slate-600">{item.summary}</p>
                              )}
                              {item.evidence && (
                                <p className="mt-1.5 line-clamp-1 text-xs text-slate-500">{item.evidence}</p>
                              )}
                              <p className="mt-2 text-xs text-slate-400">
                                Added {formatDate(item.created_at)}
                              </p>
                            </div>
                            <div className="flex flex-shrink-0 items-center gap-2">
                              <button
                                onClick={() => openEditDialog(item)}
                                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-100"
                              >
                                <Edit2 size={14} />
                                Edit
                              </button>
                              <button
                                onClick={() => handleDelete(item.id)}
                                disabled={deletingId === item.id}
                                className="inline-flex items-center gap-1.5 rounded-xl border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-600 transition-colors hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                <Trash2 size={14} />
                                {deletingId === item.id ? "Deleting…" : "Delete"}
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="timeline" className="mt-0 border-0 bg-transparent p-0 shadow-none">
                <div className="portfolio-panel p-4 sm:p-5">
                  {timeline.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 py-16 text-center">
                      <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-white">
                        <Calendar className="h-6 w-6 text-slate-400" />
                      </div>
                      <p className="mb-2 text-slate-600">No project timeline data</p>
                      <p className="text-sm text-slate-500">
                        Scan projects to see them here in chronological order.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {timeline.map((project) => (
                        <div
                          key={project.project_id}
                          className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 transition-colors hover:border-slate-300 hover:bg-white"
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-semibold text-slate-950">{project.name}</p>
                              {project.role && (
                                <p className="mt-0.5 text-xs text-slate-500">{project.role}</p>
                              )}
                              <p className="mt-1 text-xs text-slate-400">
                                {formatDateRange(project.start_date, project.end_date)}
                                {project.duration_days != null && (
                                  <span className="ml-2">({project.duration_days} days)</span>
                                )}
                              </p>
                              {project.evidence.length > 0 && (
                                <ul className="mt-2 space-y-0.5">
                                  {project.evidence.slice(0, 3).map((point, index) => (
                                    <li
                                      key={`${project.project_id}-e${index}`}
                                      className="flex gap-1.5 text-xs text-slate-600"
                                    >
                                      <span className="flex-shrink-0 text-slate-400">•</span>
                                      <span>{point}</span>
                                    </li>
                                  ))}
                                  {project.evidence.length > 3 && (
                                    <li className="text-xs text-slate-400">
                                      +{project.evidence.length - 3} more
                                    </li>
                                  )}
                                </ul>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </div>

        <Dialog open={dialogOpen} onOpenChange={handleDialogClose}>
          <DialogContent className="sm:max-w-[580px] flex max-h-[90vh] flex-col">
            <DialogHeader>
              <DialogTitle>{editing ? "Edit Portfolio Item" : "New Portfolio Item"}</DialogTitle>
              <DialogDescription>
                Add or refine portfolio entries without leaving the dashboard.
              </DialogDescription>
            </DialogHeader>

            <div className="flex-1 space-y-4 overflow-y-auto py-2 pr-1">
              {formError && (
                <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
                  {formError}
                </p>
              )}

              {!editing && projects.length > 0 && (
                <div className="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-700">
                    Generate from Project
                  </p>
                  <div className="flex gap-2">
                    <Select value={selectedProjectId} onValueChange={setSelectedProjectId}>
                      <SelectTrigger className="flex-1">
                        <SelectValue placeholder="Select a project..." />
                      </SelectTrigger>
                      <SelectContent>
                        {projects.map((project) => (
                          <SelectItem key={project.id} value={project.id}>
                            {project.project_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleGenerateFromProject}
                      disabled={!selectedProjectId || generating}
                      className="flex-shrink-0"
                    >
                      {generating ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <Sparkles size={14} />
                      )}
                      <span className="ml-1.5">
                        {generating ? "Generating..." : "Fill from Project"}
                      </span>
                    </Button>
                  </div>
                  <p className="text-xs text-gray-500">
                    Auto-fill form fields from a scanned project using AI.
                  </p>
                </div>
              )}

              <div className="space-y-1.5">
                <Label htmlFor="title">
                  Title <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="title"
                  placeholder="e.g. Full-Stack E-Commerce Platform"
                  maxLength={255}
                  value={form.title}
                  onChange={(e) => setForm((current) => ({ ...current, title: e.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="role">Role</Label>
                <Input
                  id="role"
                  placeholder="e.g. Lead Developer"
                  maxLength={255}
                  value={form.role}
                  onChange={(e) => setForm((current) => ({ ...current, role: e.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="summary">Summary</Label>
                <Textarea
                  id="summary"
                  placeholder="Brief description of the project and your contribution..."
                  rows={3}
                  maxLength={1000}
                  value={form.summary}
                  onChange={(e) => setForm((current) => ({ ...current, summary: e.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="evidence">Key Achievements / Evidence</Label>
                <Textarea
                  id="evidence"
                  placeholder="Describe measurable outcomes, impact, and evidence of your work..."
                  rows={4}
                  maxLength={2048}
                  value={form.evidence}
                  onChange={(e) => setForm((current) => ({ ...current, evidence: e.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="thumbnail">Thumbnail URL</Label>
                <Input
                  id="thumbnail"
                  placeholder="https://example.com/image.png"
                  maxLength={1024}
                  value={form.thumbnail}
                  onChange={(e) => setForm((current) => ({ ...current, thumbnail: e.target.value }))}
                />
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)} disabled={saving}>
                Cancel
              </Button>
              <Button onClick={handleSave} disabled={saving}>
                {saving ? "Saving..." : editing ? "Save Changes" : "Create"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
