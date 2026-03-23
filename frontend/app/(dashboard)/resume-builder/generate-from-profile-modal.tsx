"use client";

import { useState, useEffect } from "react";
import { Loader2, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getStoredToken } from "@/lib/auth";
import { listResumeItems, getResumeItem } from "@/lib/api/resume";
import {
  createUserResume,
  addResumeItemsToResume,
  updateUserResume,
} from "@/lib/api/user-resume";
import { generateLatexFromStructuredData } from "@/lib/latex-templates";
import { TEMPLATES } from "./template-options";
import type { ResumeTemplate, ResumeStructuredData } from "@/types/user-resume";
import type { ResumeItemSummary, ResumeItemRecord } from "@/types/resume";

// ── Types ────────────────────────────────────────────────────────────────────

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** The user's saved profile structured data (pre-fills the resume). */
  profile: ResumeStructuredData;
  /** Called after the generated resume has been created; receives the new resume ID. */
  onGenerated: (resumeId: string) => void;
}

type Step =
  | { kind: "idle" }
  | { kind: "creating" }
  | { kind: "adding_items" }
  | { kind: "done" };

// ── Component ────────────────────────────────────────────────────────────────

export function GenerateFromProfileModal({ open, onOpenChange, profile, onGenerated }: Props) {
  // Form state
  const [name, setName] = useState("My Resume");
  const [template, setTemplate] = useState<ResumeTemplate>("jake");

  // Items state
  const [resumeItems, setResumeItems] = useState<ResumeItemSummary[]>([]);
  const [loadingItems, setLoadingItems] = useState(false);
  const [selectedItemIds, setSelectedItemIds] = useState<string[]>([]);
  const [expandedItemIds, setExpandedItemIds] = useState<string[]>([]);
  const [itemDetailsById, setItemDetailsById] = useState<Record<string, ResumeItemRecord>>({});
  const [loadingItemDetails, setLoadingItemDetails] = useState<Record<string, boolean>>({});

  // Generation progress state
  const [step, setStep] = useState<Step>({ kind: "idle" });
  const [error, setError] = useState<string | null>(null);

  const isGenerating = step.kind === "creating" || step.kind === "adding_items";

  // ── Load resume items when modal opens ──────────────────────────────────
  useEffect(() => {
    if (!open) return;

    // Reset form state on open
    setName("My Resume");
    setTemplate("jake");
    setSelectedItemIds([]);
    setExpandedItemIds([]);
    setItemDetailsById({});
    setStep({ kind: "idle" });
    setError(null);

    const loadItems = async () => {
      const token = getStoredToken();
      if (!token) return;
      setLoadingItems(true);
      try {
        const response = await listResumeItems(token, 100, 0);
        setResumeItems(response.items ?? []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load project items");
      } finally {
        setLoadingItems(false);
      }
    };

    loadItems();
  }, [open]);

  // ── Item interaction ─────────────────────────────────────────────────────
  const toggleItemSelection = (id: string) => {
    setSelectedItemIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const toggleItemPreview = async (id: string) => {
    if (expandedItemIds.includes(id)) {
      setExpandedItemIds((prev) => prev.filter((x) => x !== id));
      return;
    }
    setExpandedItemIds((prev) => [...prev, id]);

    if (itemDetailsById[id]) return;

    const token = getStoredToken();
    if (!token) return;

    setLoadingItemDetails((prev) => ({ ...prev, [id]: true }));
    try {
      const detail = await getResumeItem(token, id);
      setItemDetailsById((prev) => ({ ...prev, [id]: detail }));
    } catch {
      // preview failure is non-blocking
    } finally {
      setLoadingItemDetails((prev) => ({ ...prev, [id]: false }));
    }
  };

  // ── Generate ─────────────────────────────────────────────────────────────
  const handleGenerate = async () => {
    if (!name.trim()) {
      setError("Resume name is required");
      return;
    }

    const token = getStoredToken();
    if (!token) {
      setError("Not authenticated — please log in");
      return;
    }

    setError(null);

    try {
      // Step 1: Create the resume pre-filled with the profile and generated LaTeX
      setStep({ kind: "creating" });
      const latexFromProfile = generateLatexFromStructuredData(profile);
      const created = await createUserResume(token, {
        name: name.trim(),
        template,
        is_latex_mode: false,
        structured_data: profile,
        latex_content: latexFromProfile,
      });

      // Step 2: Attach selected scan items (projects)
      if (selectedItemIds.length > 0) {
        setStep({ kind: "adding_items" });
        const updated = await addResumeItemsToResume(token, created.id, { item_ids: selectedItemIds });

        // Regenerate LaTeX with the added projects
        const finalLatex = generateLatexFromStructuredData(updated.structured_data || {});
        await updateUserResume(token, created.id, { latex_content: finalLatex });
      }

      // Step 3: Done
      setStep({ kind: "done" });

      // Brief pause so user sees the success state before navigation
      setTimeout(() => {
        onOpenChange(false);
        onGenerated(created.id);
      }, 800);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate resume");
      setStep({ kind: "idle" });
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <Dialog open={open} onOpenChange={(v) => !isGenerating && onOpenChange(v)}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col gap-0 p-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-gray-200 flex-shrink-0">
          <DialogTitle>Generate Resume from Profile</DialogTitle>
          <DialogDescription>
            Your saved profile will pre-fill the resume. Optionally add projects from your scans.
          </DialogDescription>
        </DialogHeader>

        {/* ── Generating overlay ────────────────────────────────────────── */}
        {isGenerating || step.kind === "done" ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-6 py-16 px-6">
            {step.kind === "done" ? (
              <>
                <CheckCircle2 className="h-14 w-14 text-green-500" />
                <div className="text-center">
                  <p className="text-lg font-semibold text-gray-900">Resume generated!</p>
                  <p className="text-sm text-gray-500 mt-1">Opening the editor…</p>
                </div>
              </>
            ) : (
              <>
                <Loader2 className="h-14 w-14 text-indigo-500 animate-spin" />
                <div className="text-center space-y-1">
                  <p className="text-lg font-semibold text-gray-900">
                    {step.kind === "creating" ? "Creating your resume…" : "Adding project items…"}
                  </p>
                  <p className="text-sm text-gray-500">This will only take a moment</p>
                </div>

                {/* Progress steps */}
                <ol className="space-y-2 text-sm w-64">
                  <ProgressStep
                    label="Create resume from profile"
                    done={step.kind === "adding_items"}
                    active={step.kind === "creating"}
                  />
                  {selectedItemIds.length > 0 && (
                    <ProgressStep
                      label={`Attach ${selectedItemIds.length} project${selectedItemIds.length === 1 ? "" : "s"}`}
                      done={false}
                      active={step.kind === "adding_items"}
                    />
                  )}
                </ol>
              </>
            )}
          </div>
        ) : (
          /* ── Idle form ─────────────────────────────────────────────────── */
          <>
            <div className="flex-1 overflow-auto px-6 py-4 space-y-6">
              {/* Error */}
              {error && (
                <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  {error}
                </p>
              )}

              {/* Resume name + template */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="gen-resume-name">Resume Name</Label>
                  <Input
                    id="gen-resume-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Software Engineer Resume"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Template</Label>
                  <Select value={template} onValueChange={(v) => setTemplate(v as ResumeTemplate)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TEMPLATES.map((t) => (
                        <SelectItem key={t.id} value={t.id}>
                          <div className="flex flex-col">
                            <span>{t.name}</span>
                            <span className="text-xs text-gray-500">{t.description}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Project items */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>
                    Project Items from Scans{" "}
                    <span className="font-normal text-gray-500">(optional)</span>
                  </Label>
                  {resumeItems.length > 0 && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setSelectedItemIds(resumeItems.map((i) => i.id))}
                        className="text-xs text-indigo-600 hover:underline"
                      >
                        Select all
                      </button>
                      <span className="text-gray-300">|</span>
                      <button
                        onClick={() => setSelectedItemIds([])}
                        className="text-xs text-gray-500 hover:underline"
                      >
                        Deselect all
                      </button>
                    </div>
                  )}
                </div>

                {loadingItems ? (
                  <div className="flex items-center gap-2 py-6 text-sm text-gray-500">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading project items…
                  </div>
                ) : resumeItems.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-gray-300 py-8 text-center">
                    <p className="text-sm text-gray-500">
                      No scan items found. Upload and analyze a project to generate resume bullets.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2 rounded-lg border border-gray-200 divide-y divide-gray-100 overflow-hidden">
                    {resumeItems.map((item) => {
                      const selected = selectedItemIds.includes(item.id);
                      const expanded = expandedItemIds.includes(item.id);
                      const detail = itemDetailsById[item.id];

                      return (
                        <div key={item.id} className="p-3 space-y-2">
                          <div className="flex items-start justify-between gap-3">
                            <label className="flex items-start gap-2.5 cursor-pointer flex-1 min-w-0">
                              <Checkbox
                                checked={selected}
                                onCheckedChange={() => toggleItemSelection(item.id)}
                                className="mt-0.5"
                              />
                              <div className="min-w-0">
                                <p className="text-sm font-medium text-gray-900 truncate">
                                  {item.project_name}
                                </p>
                                <p className="text-xs text-gray-500">
                                  {item.start_date ?? "Unknown start"}
                                  {item.end_date ? ` – ${item.end_date}` : ""}
                                </p>
                              </div>
                            </label>
                            <Button
                              variant="outline"
                              size="sm"
                              className="flex-shrink-0"
                              onClick={() => toggleItemPreview(item.id)}
                            >
                              {expanded ? "Hide" : "Preview"}
                            </Button>
                          </div>

                          {expanded && (
                            <div className="ml-7 bg-gray-50 border border-gray-200 rounded-md p-3 text-sm">
                              {loadingItemDetails[item.id] ? (
                                <div className="flex items-center gap-2 text-gray-500">
                                  <Loader2 className="h-3 w-3 animate-spin" />
                                  Loading preview…
                                </div>
                              ) : detail ? (
                                detail.bullets.length > 0 ? (
                                  <ul className="list-disc list-inside space-y-1 text-gray-700">
                                    {detail.bullets.map((b, i) => (
                                      <li key={i}>{b}</li>
                                    ))}
                                  </ul>
                                ) : (
                                  <p className="text-gray-500">No bullets for this item.</p>
                                )
                              ) : (
                                <p className="text-gray-500">Preview unavailable.</p>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {selectedItemIds.length > 0 && (
                  <p className="text-xs text-indigo-600">
                    {selectedItemIds.length} project{selectedItemIds.length === 1 ? "" : "s"} will be
                    added
                  </p>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 flex-shrink-0 bg-gray-50">
              <p className="text-xs text-gray-500">
                Your saved profile will pre-fill contact, education, experience, skills &amp; awards.
              </p>
              <div className="flex items-center gap-3">
                <Button variant="outline" onClick={() => onOpenChange(false)}>
                  Cancel
                </Button>
                <Button onClick={handleGenerate} disabled={!name.trim()}>
                  Generate Resume
                </Button>
              </div>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ── Progress step indicator ──────────────────────────────────────────────────

function ProgressStep({
  label,
  done,
  active,
}: {
  label: string;
  done: boolean;
  active: boolean;
}) {
  return (
    <li className="flex items-center gap-3">
      {done ? (
        <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" />
      ) : active ? (
        <Loader2 className="h-4 w-4 text-indigo-500 animate-spin flex-shrink-0" />
      ) : (
        <div className="h-4 w-4 rounded-full border-2 border-gray-300 flex-shrink-0" />
      )}
      <span
        className={
          done ? "text-green-700" : active ? "text-gray-900 font-medium" : "text-gray-400"
        }
      >
        {label}
      </span>
    </li>
  );
}
