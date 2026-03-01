"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Plus,
  Loader2,
  Briefcase,
  Edit2,
  Trash2,
  RefreshCw,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Calendar,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
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
import {
  listPortfolioItems,
  createPortfolioItem,
  updatePortfolioItem,
  deletePortfolioItem,
  generatePortfolioItem,
  getPortfolioChronology,
} from "@/lib/api/portfolio";
import { getProjects, getSkills } from "@/lib/api/projects";
import type { PortfolioItem, TimelineItem } from "@/types/portfolio";
import type { ProjectMetadata } from "@/types/project";

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
  const [items, setItems] = useState<PortfolioItem[]>([]);
  const [skills, setSkills] = useState<string[]>([]);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [projects, setProjects] = useState<ProjectMetadata[]>([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<PortfolioItem | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);

  // Generate from project
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [generating, setGenerating] = useState(false);

  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Skills section toggle
  const [skillsExpanded, setSkillsExpanded] = useState(true);

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
      const [itemsData, skillsData, chronologyData] = await Promise.allSettled([
        listPortfolioItems(token),
        getSkills(token),
        getPortfolioChronology(token),
      ]);

      if (itemsData.status === "fulfilled") {
        setItems(itemsData.value);
      } else {
        const reason = itemsData.reason;
        setError(reason instanceof Error ? reason.message : "Failed to load portfolio items");
      }
      if (skillsData.status === "fulfilled") setSkills(skillsData.value.skills);
      if (chronologyData.status === "fulfilled") setTimeline(chronologyData.value.projects);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load portfolio data");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const fetchProjects = useCallback(async () => {
    const token = getStoredToken();
    if (!token) return;
    try {
      const res = await getProjects(token);
      setProjects(res.projects);
    } catch {
      // projects list is optional; don't surface errors
    }
  }, []);

  useEffect(() => {
    fetchAll();
    fetchProjects();
  }, [fetchAll, fetchProjects]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchAll();
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
      setForm((f) => ({
        ...f,
        title: result.title || f.title,
        role: result.role || f.role,
        summary: result.summary || f.summary,
        evidence: result.evidence || f.evidence,
      }));
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : "Failed to generate from project"
      );
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
      setItems((prev) => prev.filter((item) => item.id !== id));
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
        setItems((prev) =>
          prev.map((item) => (item.id === updated.id ? updated : item))
        );
      } else {
        const created = await createPortfolioItem(token, payload);
        setItems((prev) => [created, ...prev]);
      }
      setDialogOpen(false);
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : "Failed to save portfolio item"
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDialogClose = (open: boolean) => {
    if (!saving) setDialogOpen(open);
  };

  if (loading) {
    return (
      <div className="p-8">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
            <span className="ml-3 text-gray-500">Loading portfolio...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="px-8 py-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
                Portfolio
              </h1>
              <p className="mt-2 text-sm text-gray-600">
                {items.length === 0
                  ? "No portfolio items yet"
                  : `${items.length} item${items.length === 1 ? "" : "s"}`}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RefreshCw size={18} className={refreshing ? "animate-spin" : ""} />
                <span className="font-medium">Refresh</span>
              </button>
              <button
                onClick={openCreateDialog}
                className="flex items-center gap-2 px-5 py-2.5 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors shadow-sm"
              >
                <Plus size={20} />
                <span className="font-medium">New Item</span>
              </button>
            </div>
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div className="mx-8 mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex">
              <svg className="h-5 w-5 text-red-400 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
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

        {/* Skills summary */}
        <div className="px-8 py-5 border-b border-gray-200">
          <button
            onClick={() => setSkillsExpanded((v) => !v)}
            className="flex items-center gap-2 text-sm font-semibold text-gray-700 hover:text-gray-900 transition-colors mb-3"
          >
            {skillsExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            Skills Summary
            {skills.length > 0 && (
              <span className="text-xs font-normal text-gray-500 ml-1">
                ({skills.length} skills across all projects)
              </span>
            )}
          </button>
          {skillsExpanded && (
            <>
              {skills.length === 0 ? (
                <p className="text-sm text-gray-500">
                  No skills found. Scan a project to populate skills.
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {skills.map((skill) => (
                    <Badge key={skill} variant="secondary" className="text-xs">
                      {skill}
                    </Badge>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        {/* Tabs */}
        <div className="p-8">
          <Tabs defaultValue="items">
            <TabsList className="mb-6">
              <TabsTrigger value="items">Portfolio Items</TabsTrigger>
              <TabsTrigger value="timeline">Project Timeline</TabsTrigger>
            </TabsList>

            {/* Portfolio Items tab */}
            <TabsContent value="items">
              {items.length === 0 ? (
                <div className="text-center py-16">
                  <div className="inline-flex items-center justify-center w-12 h-12 bg-gray-100 rounded-full mb-4">
                    <Briefcase className="h-6 w-6 text-gray-400" />
                  </div>
                  <p className="text-gray-600 mb-2">No portfolio items yet</p>
                  <p className="text-sm text-gray-500 mb-6">
                    Create your first portfolio item or generate one from a project.
                  </p>
                  <button
                    onClick={openCreateDialog}
                    className="inline-flex items-center gap-2 px-5 py-2.5 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
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
                      className="p-5 border border-gray-200 rounded-xl hover:border-gray-300 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-4">
                        {item.thumbnail && (
                          <img
                            src={item.thumbnail}
                            alt={item.title}
                            className="w-16 h-16 rounded-lg object-cover flex-shrink-0 border border-gray-200"
                            onError={(e) => {
                              (e.currentTarget as HTMLImageElement).style.display = "none";
                            }}
                          />
                        )}
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold text-gray-900">
                            {item.title}
                          </p>
                          {item.role && (
                            <p className="text-xs text-gray-500 mt-0.5">{item.role}</p>
                          )}
                          {item.summary && (
                            <p className="text-sm text-gray-600 mt-2 line-clamp-2">
                              {item.summary}
                            </p>
                          )}
                          {item.evidence && (
                            <p className="text-xs text-gray-500 mt-1.5 line-clamp-1">
                              {item.evidence}
                            </p>
                          )}
                          <p className="text-xs text-gray-400 mt-2">
                            Added {formatDate(item.created_at)}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <button
                            onClick={() => openEditDialog(item)}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                          >
                            <Edit2 size={14} />
                            Edit
                          </button>
                          <button
                            onClick={() => handleDelete(item.id)}
                            disabled={deletingId === item.id}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
            </TabsContent>

            {/* Project Timeline tab */}
            <TabsContent value="timeline">
              {timeline.length === 0 ? (
                <div className="text-center py-16">
                  <div className="inline-flex items-center justify-center w-12 h-12 bg-gray-100 rounded-full mb-4">
                    <Calendar className="h-6 w-6 text-gray-400" />
                  </div>
                  <p className="text-gray-600 mb-2">No project timeline data</p>
                  <p className="text-sm text-gray-500">
                    Scan projects to see them here in chronological order.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {timeline.map((project) => (
                    <div
                      key={project.project_id}
                      className="p-5 border border-gray-200 rounded-xl hover:border-gray-300 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold text-gray-900">
                            {project.name}
                          </p>
                          {project.role && (
                            <p className="text-xs text-gray-500 mt-0.5">{project.role}</p>
                          )}
                          <p className="text-xs text-gray-400 mt-1">
                            {formatDateRange(project.start_date, project.end_date)}
                            {project.duration_days != null && (
                              <span className="ml-2">
                                ({project.duration_days} days)
                              </span>
                            )}
                          </p>
                          {project.evidence.length > 0 && (
                            <ul className="mt-2 space-y-0.5">
                              {project.evidence.slice(0, 3).map((point, i) => (
                                <li key={`${project.project_id}-e${i}`} className="text-xs text-gray-600 flex gap-1.5">
                                  <span className="text-gray-400 flex-shrink-0">•</span>
                                  <span>{point}</span>
                                </li>
                              ))}
                              {project.evidence.length > 3 && (
                                <li className="text-xs text-gray-400">
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
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={handleDialogClose}>
        <DialogContent className="sm:max-w-[580px] flex flex-col max-h-[90vh]">
          <DialogHeader>
            <DialogTitle>
              {editing ? "Edit Portfolio Item" : "New Portfolio Item"}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2 overflow-y-auto flex-1 pr-1">
            {formError && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {formError}
              </p>
            )}

            {/* Generate from project (create mode only) */}
            {!editing && projects.length > 0 && (
              <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg space-y-3">
                <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                  Generate from Project
                </p>
                <div className="flex gap-2">
                  <Select
                    value={selectedProjectId}
                    onValueChange={setSelectedProjectId}
                  >
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder="Select a project..." />
                    </SelectTrigger>
                    <SelectContent>
                      {projects.map((p) => (
                        <SelectItem key={p.id} value={p.id}>
                          {p.project_name}
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
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="role">Role</Label>
              <Input
                id="role"
                placeholder="e.g. Lead Developer"
                maxLength={255}
                value={form.role}
                onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
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
                onChange={(e) => setForm((f) => ({ ...f, summary: e.target.value }))}
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
                onChange={(e) => setForm((f) => ({ ...f, evidence: e.target.value }))}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="thumbnail">Thumbnail URL</Label>
              <Input
                id="thumbnail"
                placeholder="https://example.com/image.png"
                maxLength={1024}
                value={form.thumbnail}
                onChange={(e) => setForm((f) => ({ ...f, thumbnail: e.target.value }))}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDialogOpen(false)}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving
                ? "Saving..."
                : editing
                ? "Save Changes"
                : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
