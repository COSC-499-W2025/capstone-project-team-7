"use client";

import { useState, useEffect, useCallback } from "react";
import { Plus, Loader2, FileText, Edit2, Trash2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
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

function formatDateRange(
  start?: string | null,
  end?: string | null
): string {
  if (!start && !end) return "No dates set";
  if (start && end) return `${start} – ${end}`;
  if (start) return `From ${start}`;
  return `Until ${end}`;
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
      <div className="p-8">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
            <span className="ml-3 text-gray-500">Loading resume items...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        {/* Header */}
        <div className="px-8 py-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
                Resume Items
              </h1>
              <p className="mt-2 text-sm text-gray-600">
                {items.length === 0
                  ? "No resume items yet"
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

        {/* Content */}
        <div className="p-8">
          {items.length === 0 ? (
            <div className="text-center py-16">
              <div className="inline-flex items-center justify-center w-12 h-12 bg-gray-100 rounded-full mb-4">
                <FileText className="h-6 w-6 text-gray-400" />
              </div>
              <p className="text-gray-600 mb-2">No resume items yet</p>
              <p className="text-sm text-gray-500 mb-6">
                Create your first resume item to get started.
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
                  className="flex items-start justify-between gap-4 p-5 border border-gray-200 rounded-xl hover:border-gray-300 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-gray-900 truncate">
                      {item.project_name}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {formatDateRange(item.start_date, item.end_date)}
                    </p>
                    {item.created_at && (
                      <p className="text-xs text-gray-400 mt-1">
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
                    <button
                      onClick={() => openEditDialog(item.id)}
                      disabled={loadingDetail}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {loadingDetail ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <Edit2 size={14} />
                      )}
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(item.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
                    >
                      <Trash2 size={14} />
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Loading overlay when fetching item detail for edit */}
      {loadingDetail && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4 flex items-center gap-3 shadow-xl">
            <Loader2 className="h-5 w-5 animate-spin text-gray-600" />
            <span className="text-sm text-gray-700">Loading item...</span>
          </div>
        </div>
      )}

      {/* Create / Edit dialog */}
      <Dialog open={dialogOpen} onOpenChange={handleDialogClose}>
        <DialogContent className="sm:max-w-[560px]">
          <DialogHeader>
            <DialogTitle>
              {editing ? "Edit Resume Item" : "New Resume Item"}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {formError && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
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
              <p className="text-xs text-gray-400">
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
