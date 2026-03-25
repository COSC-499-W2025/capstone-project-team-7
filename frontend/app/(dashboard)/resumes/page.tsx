"use client";

import { useState, useEffect, useCallback } from "react";
import { Plus, FileText, Edit2, Trash2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/ui/loading-state";
import { Spinner } from "@/components/ui/spinner";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { getStoredToken } from "@/lib/auth";
import {
  listResumeItems,
  getResumeItem,
  createResumeItem,
  updateResumeItem,
  deleteResumeItem,
} from "@/lib/api/resume";
import type { ResumeItemSummary, ResumeItemRecord } from "@/types/resume";

interface FormState {
  project_name: string;
  start_date: string;
  end_date: string;
  bulletsText: string; // one bullet per line in the textarea
}

const EMPTY_FORM: FormState = {
  project_name: "",
  start_date: "",
  end_date: "",
  bulletsText: "",
};

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

function formatDateRange(
  start?: string | null,
  end?: string | null
): string {
  if (!start && !end) return "No dates set";
  const formattedStart = formatDateForDisplay(start);
  const formattedEnd = formatDateForDisplay(end);

  if (formattedStart && formattedEnd) return `${formattedStart} – ${formattedEnd}`;
  if (formattedStart) return `From ${formattedStart}`;
  if (formattedEnd) return `Until ${formattedEnd}`;
  return "No dates set";
}

function parseBullets(text: string): string[] {
  return text
    .split("\n")
    .map((line) => line.replace(/^[\s•\-*]+/, "").trim())
    .filter(Boolean);
}

export default function ResumesPage() {
  const [items, setItems] = useState<ResumeItemSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<ResumeItemRecord | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);

  const fetchItems = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setError("Not authenticated. Please log in.");
      setLoading(false);
      setRefreshing(false);
      return;
    }
    try {
      setError(null);
      const res = await listResumeItems(token);
      setItems(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load resume items");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchItems();
  };

  const openCreateDialog = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setFormError(null);
    setDialogOpen(true);
  };

  const openEditDialog = async (id: string) => {
    const token = getStoredToken();
    if (!token) return;
    setLoadingDetail(true);
    try {
      const record = await getResumeItem(token, id);
      setEditing(record);
      setForm({
        project_name: record.project_name,
        start_date: record.start_date ?? "",
        end_date: record.end_date ?? "",
        bulletsText: record.bullets.join("\n"),
      });
      setFormError(null);
      setDialogOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load resume item");
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this resume item? This cannot be undone.")) return;
    const token = getStoredToken();
    if (!token) return;
    try {
      await deleteResumeItem(token, id);
      setItems((prev) => prev.filter((item) => item.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete resume item");
    }
  };

  const handleSave = async () => {
    if (!form.project_name.trim()) {
      setFormError("Project name is required.");
      return;
    }
    const token = getStoredToken();
    if (!token) return;

    setSaving(true);
    setFormError(null);

    const bullets = parseBullets(form.bulletsText);

    try {
      if (editing) {
        const updated = await updateResumeItem(token, editing.id, {
          project_name: form.project_name.trim(),
          start_date: form.start_date.trim() || null,
          end_date: form.end_date.trim() || null,
          bullets,
        });
        setItems((prev) =>
          prev.map((item) =>
            item.id === updated.id
              ? {
                  id: updated.id,
                  project_name: updated.project_name,
                  start_date: updated.start_date,
                  end_date: updated.end_date,
                  created_at: updated.created_at,
                  metadata: updated.metadata,
                }
              : item
          )
        );
      } else {
        const created = await createResumeItem(token, {
          project_name: form.project_name.trim(),
          start_date: form.start_date.trim() || null,
          end_date: form.end_date.trim() || null,
          bullets,
        });
        setItems((prev) => [
          {
            id: created.id,
            project_name: created.project_name,
            start_date: created.start_date,
            end_date: created.end_date,
            created_at: created.created_at,
            metadata: created.metadata,
          },
          ...prev,
        ]);
      }
      setDialogOpen(false);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to save resume item");
    } finally {
      setSaving(false);
    }
  };

  const handleDialogClose = (open: boolean) => {
    if (!saving) setDialogOpen(open);
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="mx-auto w-full max-w-[1500px]">
          <LoadingState message="Loading resume items..." />
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <section className="page-card page-hero">
        <div className="page-header">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="page-kicker">Resume Building Blocks</p>
              <h1 className="text-foreground">Resume Items</h1>
              <p className="page-summary mt-3">
                {items.length === 0
                  ? "No resume items yet"
                  : `${items.length} item${items.length === 1 ? "" : "s"}`}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <span className="dashboard-chip">{items.length} saved item{items.length === 1 ? "" : "s"}</span>
                <span className="dashboard-chip">Reusable bullet library</span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button
                onClick={handleRefresh}
                disabled={refreshing}
                variant="outline"
              >
                {refreshing ? <Spinner size={18} /> : <RefreshCw size={18} />}
                <span className="font-medium">Refresh</span>
              </Button>
              <Button
                onClick={openCreateDialog}
              >
                <Plus size={20} />
                <span className="font-medium">New Item</span>
              </Button>
            </div>
          </div>
        </div>
      </section>

        {error && (
          <div className="alert alert-error">
            <div className="flex">
              <svg
                className="h-5 w-5 text-red-400 flex-shrink-0"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
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

        <section className="page-card page-body">
          {items.length === 0 ? (
            <div className="grid gap-5 py-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(300px,0.85fr)]">
              <div className="rounded-[24px] border border-dashed border-border bg-background/80 px-8 py-12 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]">
                <div className="mb-5 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-card shadow-[0_16px_32px_rgba(15,23,42,0.08)]">
                  <FileText className="h-7 w-7 text-muted-foreground" />
                </div>
                <p className="mb-2 text-lg font-medium text-foreground">No resume items yet</p>
                <p className="mb-2 text-sm font-medium text-foreground">Build your resume evidence library</p>
                <p className="mx-auto mb-6 max-w-md text-sm leading-6 text-muted-foreground">
                  Save project bullets, time ranges, and impact statements here so the strongest material is ready when you assemble a tailored resume.
                </p>
                <Button onClick={openCreateDialog}>
                  <Plus size={18} />
                  New Item
                </Button>
              </div>
              <div className="grid gap-3">
                <div className="info-tile">
                  <p className="info-tile-kicker">Recommended</p>
                  <p className="mt-3 text-base font-semibold text-foreground">One achievement per line</p>
                  <p className="mt-2 text-sm text-muted-foreground">Keep each bullet singular, measurable, and easy to remix.</p>
                </div>
                <div className="info-tile">
                  <p className="info-tile-kicker">Signal</p>
                  <p className="mt-3 text-base font-semibold text-foreground">Capture dates and scope</p>
                  <p className="mt-2 text-sm text-muted-foreground">Add project names and date ranges so entries are ready for export later.</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {items.map((item) => (
                <div
                  key={item.id}
                  className="flex items-start justify-between gap-4 rounded-[22px] border border-border bg-card/85 p-5 shadow-[0_18px_36px_rgba(15,23,42,0.06)] transition-[transform,border-color,background-color] hover:-translate-y-0.5 hover:border-primary/20 hover:bg-background"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-foreground truncate">
                      {item.project_name}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {formatDateRange(item.start_date, item.end_date)}
                    </p>
                    {item.created_at && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Added{" "}
                        {new Date(item.created_at).toLocaleDateString(undefined, {
                          year: "numeric",
                          month: "short",
                          day: "numeric",
                        })}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Button
                      onClick={() => openEditDialog(item.id)}
                      disabled={loadingDetail}
                      variant="outline"
                      size="sm"
                    >
                      {loadingDetail ? (
                        <Spinner size={14} />
                      ) : (
                        <Edit2 size={14} />
                      )}
                      Edit
                    </Button>
                    <Button
                      onClick={() => handleDelete(item.id)}
                      variant="destructive"
                      size="sm"
                    >
                      <Trash2 size={14} />
                      Delete
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

      {loadingDetail && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-[20px] p-4 flex items-center gap-3 shadow-[0_28px_60px_rgba(15,23,42,0.18)]">
            <Spinner size="lg" className="text-gray-600" />
            <span className="text-sm text-gray-700">Loading item...</span>
          </div>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={handleDialogClose}>
        <DialogContent className="sm:max-w-[560px]">
          <DialogHeader>
            <DialogTitle>
              {editing ? "Edit Resume Item" : "New Resume Item"}
            </DialogTitle>
            <DialogDescription>
              Capture reusable resume bullets and project timing details.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {formError && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-[14px] px-3 py-2">
                {formError}
              </p>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="project_name">
                Project Name <span className="text-red-500">*</span>
              </Label>
              <Input
                id="project_name"
                placeholder="e.g. Capstone Project"
                value={form.project_name}
                onChange={(e) =>
                  setForm((f) => ({ ...f, project_name: e.target.value }))
                }
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="start_date">Start Date</Label>
                <Input
                  id="start_date"
                  placeholder="e.g. Sep 2024"
                  value={form.start_date}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, start_date: e.target.value }))
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="end_date">End Date</Label>
                <Input
                  id="end_date"
                  placeholder="e.g. Apr 2025"
                  value={form.end_date}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, end_date: e.target.value }))
                  }
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="bullets">Bullet Points</Label>
              <Textarea
                id="bullets"
                placeholder={
                  "One bullet per line, e.g.:\nBuilt REST API with FastAPI and Supabase\nReduced scan time by 40% via parallel processing"
                }
                rows={5}
                value={form.bulletsText}
                onChange={(e) =>
                  setForm((f) => ({ ...f, bulletsText: e.target.value }))
                }
              />
              <p className="text-xs text-muted-foreground">
                One bullet per line. Leading dashes or bullets are stripped automatically.
              </p>
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
