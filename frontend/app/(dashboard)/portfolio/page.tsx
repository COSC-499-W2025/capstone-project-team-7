"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Briefcase,
  Calendar,
  Lightbulb,
  Plus,
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
import { Spinner } from "@/components/ui/spinner";
import { ResourceSuggestions } from "@/components/portfolio/resource-suggestions";
import { LinkedInShareDialog } from "@/components/portfolio/linkedin-share-dialog";

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

function formatDateForDisplay(dateStr: string | null | undefined): string {
  if (!dateStr) return "";
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    return date.toLocaleDateString(undefined, {
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
  const formattedStart = formatDateForDisplay(start);
  const formattedEnd = formatDateForDisplay(end);

  if (formattedStart && formattedEnd) return `${formattedStart} – ${formattedEnd}`;
  if (formattedStart) return `From ${formattedStart}`;
  if (formattedEnd) return `Until ${formattedEnd}`;
  return "Dates unknown";
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
  const [activeTab, setActiveTab] = useState("overview");
  const [stableTabHeight, setStableTabHeight] = useState(0);
  const activePanelRef = useRef<HTMLDivElement | null>(null);
  const [linkedInOpen, setLinkedInOpen] = useState(false);

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

      if (settingsData.status === "fulfilled") {
        setPortfolioSettings(settingsData.value);
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

  useEffect(() => {
    const node = activePanelRef.current;
    if (!node) return;

    const measure = () => {
      const nextHeight = node.offsetHeight;
      if (nextHeight > 0) {
        setStableTabHeight((current) => Math.max(current, nextHeight));
      }
    };

    measure();
    const frame = window.requestAnimationFrame(measure);
    return () => window.cancelAnimationFrame(frame);
  }, [
    activeTab,
    items.length,
    timeline.length,
    skills.length,
    projects.length,
    chronology,
    portfolioSettings,
    profile,
  ]);

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
      <div className="page-container">
        <div className="mx-auto w-full max-w-[1500px]">
          <LoadingState message="Loading portfolio..." />
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="mx-auto max-w-[1500px] space-y-4">
        <div className="portfolio-shell page-hero overflow-hidden">
          <div className="page-header">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="page-kicker">Career Snapshot</p>
                <h1 className="mt-1 text-foreground">Portfolio</h1>
                <p className="page-summary mt-3">
                  {items.length === 0
                    ? "No portfolio items yet"
                    : `${items.length} item${items.length === 1 ? "" : "s"}`}
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <span className="portfolio-chip">{items.length} curated item{items.length === 1 ? "" : "s"}</span>
                  <span className="portfolio-chip">{timeline.length} timeline entr{timeline.length === 1 ? "y" : "ies"}</span>
                  <span className="portfolio-chip">{skills.length} extracted skill{skills.length === 1 ? "" : "s"}</span>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  variant="outline"
                >
                  {refreshing ? <Spinner size={18} /> : <RefreshCw size={18} />}
                  <span>{refreshing ? "Refreshing…" : "Refresh"}</span>
                </Button>
                <Button
                  onClick={openCreateDialog}
                >
                  <Plus size={18} />
                  <span>New Item</span>
                </Button>
              </div>
            </div>
          </div>

          {error && (
            <div className="mx-5 mt-5 alert alert-error text-sm sm:mx-6">
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
            <div className="mx-5 mt-5 alert alert-success text-sm sm:mx-6">
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
                  className="flex-shrink-0 rounded-full border border-emerald-200 bg-white/70 p-1 text-emerald-500 transition-colors hover:text-emerald-700"
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
            <Tabs
              defaultValue="overview"
              onValueChange={setActiveTab}
              className="space-y-4"
            >
              <TabsList className="mb-0 h-auto w-full justify-start gap-2 overflow-x-auto">
                <TabsTrigger value="overview">
                  Overview
                </TabsTrigger>
                <TabsTrigger value="items">
                  Portfolio Items
                </TabsTrigger>
                <TabsTrigger value="timeline">
                  Project Timeline
                </TabsTrigger>
                <TabsTrigger value="resources" className="rounded-xl">
                  <Lightbulb size={14} className="mr-1.5" />
                  Resources
                </TabsTrigger>
              </TabsList>

              <div
                className="transition-[min-height] duration-200 ease-out"
                style={{ minHeight: stableTabHeight > 0 ? `${stableTabHeight}px` : undefined }}
              >
                <TabsContent value="overview" className="mt-0 border-0 bg-transparent p-0">
                  <div ref={activeTab === "overview" ? activePanelRef : null}>
                    <PortfolioOverview
                      profile={profile}
                      chronology={chronology}
                      projects={projects}
                      skills={skills}
                      initialSettings={portfolioSettings}
                      onShareLinkedIn={() => setLinkedInOpen(true)}
                    />
                  </div>
                </TabsContent>

                <TabsContent value="items" className="mt-0 border-0 bg-transparent p-0">
                  <div ref={activeTab === "items" ? activePanelRef : null} className="space-y-4">
                    <div className="split-callout">
                      <div className="split-callout-card">
                        <p className="page-kicker mb-2">Curated Highlights</p>
                        <p className="text-sm text-muted-foreground">
                          Portfolio items should read like concise proof points: clear role, measurable impact, and strong summary copy.
                        </p>
                      </div>
                    </div>
                    {items.length === 0 ? (
                      <div className="rounded-[24px] border border-dashed border-border bg-background/80 py-16 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.65)]">
                        <div className="mb-4 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-card shadow-[0_14px_30px_rgba(15,23,42,0.08)]">
                          <Briefcase className="h-6 w-6 text-muted-foreground" />
                        </div>
                        <p className="mb-2 text-base font-medium text-foreground">No portfolio items yet</p>
                        <p className="mb-6 text-sm text-muted-foreground">
                          Create your first portfolio item or generate one from a project.
                        </p>
                        <Button
                          onClick={openCreateDialog}
                        >
                          <Plus size={18} />
                          New Item
                        </Button>
                      </div>
                    ) : (
                      <div className="grid gap-4 xl:grid-cols-2">
                        {items.map((item) => (
                          <div
                            key={item.id}
                            className="rounded-[22px] border border-border bg-card/92 p-5 shadow-[0_18px_38px_rgba(15,23,42,0.06)] transition-[transform,border-color,background-color] hover:-translate-y-0.5 hover:border-primary/20 hover:bg-background"
                          >
                            <div className="flex items-start gap-4">
                              <div className="flex h-16 w-16 flex-shrink-0 items-center justify-center overflow-hidden rounded-[14px] border-2 border-border bg-muted">
                                {item.thumbnail ? (
                                  // eslint-disable-next-line @next/next/no-img-element
                                  <img
                                    src={item.thumbnail}
                                    alt={item.title}
                                    className="h-full w-full object-cover"
                                    onError={(e) => {
                                      (e.currentTarget as HTMLImageElement).style.display = "none";
                                    }}
                                  />
                                ) : (
                                  <Briefcase className="h-6 w-6 text-muted-foreground" />
                                )}
                              </div>
                              <div className="min-w-0 flex-1 space-y-3">
                                <div className="space-y-1">
                                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                                    Portfolio Item
                                  </p>
                                  <p className="text-base font-semibold text-foreground">{item.title}</p>
                                </div>
                                {item.role && <p className="mt-0.5 text-xs text-muted-foreground">{item.role}</p>}
                                {item.summary && (
                                  <p className="text-sm leading-6 text-muted-foreground">{item.summary}</p>
                                )}
                                {item.evidence && (
                                  <p className="rounded-[12px] border border-border bg-muted/70 px-3 py-2 text-xs leading-5 text-muted-foreground">
                                    {item.evidence}
                                  </p>
                                )}
                                <p className="text-xs text-muted-foreground">
                                  Added {formatDate(item.created_at)}
                                </p>
                                <div className="flex flex-wrap items-center gap-2 pt-1">
                                  <Button
                                    onClick={() => openEditDialog(item)}
                                    variant="outline"
                                    size="sm"
                                  >
                                    <Edit2 size={14} />
                                    Edit
                                  </Button>
                                  <Button
                                    onClick={() => handleDelete(item.id)}
                                    disabled={deletingId === item.id}
                                    variant="destructive"
                                    size="sm"
                                  >
                                    <Trash2 size={14} />
                                    {deletingId === item.id ? "Deleting…" : "Delete"}
                                  </Button>
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </TabsContent>

                <TabsContent value="timeline" className="mt-0 border-0 bg-transparent p-0">
                  <div ref={activeTab === "timeline" ? activePanelRef : null} className="space-y-4">
                    <div className="split-callout">
                      <div className="split-callout-card">
                        <p className="page-kicker mb-2">Chronology</p>
                        <p className="text-sm text-muted-foreground">
                          Timeline entries should feel sequential and scannable, with dates and evidence separated cleanly from the project title.
                        </p>
                      </div>
                    </div>
                    {timeline.length === 0 ? (
                      <div className="rounded-[24px] border border-dashed border-border bg-background/80 py-16 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.65)]">
                        <div className="mb-4 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-card shadow-[0_14px_30px_rgba(15,23,42,0.08)]">
                          <Calendar className="h-6 w-6 text-muted-foreground" />
                        </div>
                        <p className="mb-2 text-base font-medium text-foreground">No project timeline data</p>
                        <p className="text-sm text-muted-foreground">
                          Scan projects to see them here in chronological order.
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {timeline.map((project, index) => (
                          <div
                            key={project.project_id}
                            className="relative rounded-[22px] border border-border bg-card/92 p-5 shadow-[0_18px_38px_rgba(15,23,42,0.06)] transition-[transform,border-color,background-color] hover:-translate-y-0.5 hover:border-primary/20 hover:bg-background"
                          >
                            <div className="flex items-start gap-4">
                              <div className="flex w-16 flex-shrink-0 flex-col items-center">
                                <div className="flex h-11 w-11 items-center justify-center rounded-full border-2 border-border bg-muted text-sm font-semibold text-foreground">
                                  {index + 1}
                                </div>
                                <div className="mt-2 h-full min-h-[2rem] w-px bg-border" />
                              </div>
                              <div className="min-w-0 flex-1 space-y-3">
                                <div className="flex flex-wrap items-start justify-between gap-3">
                                  <div className="space-y-1">
                                    <p className="text-sm font-semibold text-foreground">{project.name}</p>
                                    {project.role && (
                                      <p className="text-xs text-muted-foreground">{project.role}</p>
                                    )}
                                  </div>
                                  <div className="rounded-[12px] border border-border bg-muted/70 px-3 py-2 text-right">
                                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                      Timeline
                                    </p>
                                    <p className="mt-1 text-xs text-foreground">
                                      {formatDateRange(project.start_date, project.end_date)}
                                    </p>
                                  </div>
                                </div>
                                {project.duration_days != null && (
                                  <p className="text-xs text-muted-foreground">
                                    Duration: {project.duration_days} day{project.duration_days === 1 ? "" : "s"}
                                  </p>
                                )}
                                {project.evidence.length > 0 ? (
                                  <ul className="space-y-2">
                                    {project.evidence.slice(0, 3).map((point, index) => (
                                      <li
                                        key={`${project.project_id}-e${index}`}
                                        className="flex gap-2 rounded-[12px] border border-border bg-muted/55 px-3 py-2 text-xs leading-5 text-muted-foreground"
                                      >
                                        <span className="flex-shrink-0 text-muted-foreground">•</span>
                                        <span>{point}</span>
                                      </li>
                                    ))}
                                    {project.evidence.length > 3 && (
                                      <li className="text-xs text-muted-foreground">
                                        +{project.evidence.length - 3} more
                                      </li>
                                    )}
                                  </ul>
                                ) : (
                                  <p className="text-xs text-muted-foreground">No evidence attached yet.</p>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </TabsContent>

                <TabsContent value="resources" className="mt-0 border-0 bg-transparent p-0">
                  <div ref={activeTab === "resources" ? activePanelRef : null}>
                    <ResourceSuggestions />
                  </div>
                </TabsContent>
              </div>
            </Tabs>
          </div>
        </div>

        <LinkedInShareDialog open={linkedInOpen} onOpenChange={setLinkedInOpen} />

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
                <p className="rounded-[16px] border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {formError}
                </p>
              )}

              {!editing && projects.length > 0 && (
                <div className="space-y-3 rounded-[18px] border border-border bg-muted/70 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-foreground">
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
                        <Spinner size={14} />
                      ) : (
                        <Sparkles size={14} />
                      )}
                      <span className="ml-1.5">
                        {generating ? "Generating..." : "Fill from Project"}
                      </span>
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
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
