"use client";

import { useState, useEffect, useCallback, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  Save,
  Download,
  Eye,
  Code,
  FileEdit,
  Settings,
  ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/ui/loading-state";
import { Spinner } from "@/components/ui/spinner";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Switch } from "@/components/ui/switch";
import { getStoredToken } from "@/lib/auth";
import {
  getUserResume,
  updateUserResume,
  addResumeItemsToResume,
  detectResumeSkills,
  downloadResumePdf,
} from "@/lib/api/user-resume";
import { listResumeItems, getResumeItem } from "@/lib/api/resume";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { getTemplateLatex, generateLatexFromStructuredData } from "@/lib/latex-templates";
import type {
  UserResumeRecord,
  ResumeTemplate,
  ResumeStructuredData,
  ResumeContactInfo,
  ResumeEducationEntry,
  ResumeExperienceEntry,
  ResumeProjectEntry,
  ResumeAwardEntry,
} from "@/types/user-resume";
import type { ResumeItemSummary, ResumeItemRecord } from "@/types/resume";

// Debounce helper
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  return debouncedValue;
}

// Generate unique ID
function generateId(): string {
  return Math.random().toString(36).substring(2, 9);
}

function normalizeExternalUrl(url: string): string {
  const value = url.trim();
  if (!value) return "";
  if (/^https?:\/\//i.test(value)) return value;
  return `https://${value}`;
}

function displayUrl(url: string): string {
  return url.replace(/^https?:\/\//i, "").replace(/\/$/, "");
}

// Comma-separated input that preserves typing and only converts to array on blur
function CommaSeparatedInput({
  value,
  onChange,
  placeholder,
}: {
  value: string[];
  onChange: (items: string[]) => void;
  placeholder?: string;
}) {
  const [localValue, setLocalValue] = useState(value.join(", "));

  // Sync from parent when value changes externally
  useEffect(() => {
    setLocalValue(value.join(", "));
  }, [value]);

  const handleBlur = () => {
    const items = localValue
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    onChange(items);
  };

  return (
    <Input
      value={localValue}
      onChange={(e) => setLocalValue(e.target.value)}
      onBlur={handleBlur}
      placeholder={placeholder}
    />
  );
}

function ResumeEditorPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const resumeId = searchParams.get("id") ?? "";

  const [resume, setResume] = useState<UserResumeRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [pdfExporting, setPdfExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);

  // Editor state
  const [latexContent, setLatexContent] = useState("");
  const [structuredData, setStructuredData] = useState<ResumeStructuredData>({});
  const [isLatexMode, setIsLatexMode] = useState(true);
  const [resumeName, setResumeName] = useState("");
  const [template, setTemplate] = useState<ResumeTemplate>("jake");

  // Dirty state for auto-save
  const [isDirty, setIsDirty] = useState(false);
  const debouncedLatex = useDebounce(latexContent, 1500);
  const debouncedStructured = useDebounce(structuredData, 1500);
  const debouncedResumeName = useDebounce(resumeName, 1500);
  const debouncedTemplate = useDebounce(template, 1500);

  // Fetch resume on mount
  useEffect(() => {
    const fetchResume = async () => {
      const token = getStoredToken();
      if (!token) {
        setError("Not authenticated");
        setLoading(false);
        return;
      }

      try {
        const data = await getUserResume(token, resumeId);
        setResume(data);
        // If no saved LaTeX, generate it from structured data (e.g. profile-generated resumes)
        const sd = data.structured_data || {};
        const hasStructuredContent = sd.contact || (sd.education && sd.education.length > 0) || (sd.experience && sd.experience.length > 0) || (sd.projects && sd.projects.length > 0);
        setLatexContent(
          data.latex_content ||
          (hasStructuredContent ? generateLatexFromStructuredData(sd) : getTemplateLatex(data.template))
        );
        setStructuredData(sd);
        setIsLatexMode(data.is_latex_mode);
        setResumeName(data.name);
        setTemplate(data.template);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load resume");
      } finally {
        setLoading(false);
      }
    };

    fetchResume();
  }, [resumeId]);

  // Auto-save when debounced values change
  useEffect(() => {
    if (!resume || !isDirty) return;

    const autoSave = async () => {
      const token = getStoredToken();
      if (!token) return;

      setSaving(true);
      try {
        await updateUserResume(token, resumeId, {
          name: debouncedResumeName,
          template: debouncedTemplate,
          latex_content: isLatexMode ? debouncedLatex : null,
          // Always persist structured_data so form-mode data is preserved
          // even when the user is editing in LaTeX mode.
          structured_data: debouncedStructured,
          is_latex_mode: isLatexMode,
        });
        setLastSaved(new Date());
        setIsDirty(false);
      } catch (err) {
        console.error("Auto-save failed:", err);
      } finally {
        setSaving(false);
      }
    };

    autoSave();
  }, [debouncedLatex, debouncedStructured, debouncedResumeName, debouncedTemplate, resume, resumeId, isLatexMode, isDirty]);

  // Manual save
  const handleSave = async () => {
    const token = getStoredToken();
    if (!token) return;

    setSaving(true);
    try {
      await updateUserResume(token, resumeId, {
        name: resumeName,
        template,
        latex_content: isLatexMode ? latexContent : generateLatexFromStructuredData(structuredData),
        structured_data: structuredData,
        is_latex_mode: isLatexMode,
      });
      setLastSaved(new Date());
      setIsDirty(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  // Handle LaTeX content change
  const handleLatexChange = (value: string) => {
    setLatexContent(value);
    setIsDirty(true);
  };

  // Handle structured data update
  const updateStructuredData = (updates: Partial<ResumeStructuredData>) => {
    setStructuredData((prev) => ({ ...prev, ...updates }));
    setIsDirty(true);
  };

  // Switch between modes
  const handleModeSwitch = (latex: boolean) => {
    if (!latex && isLatexMode) {
      // Switching from LaTeX to form - keep the structured data as-is
      // User will edit via forms
    } else if (latex && !isLatexMode) {
      // Switching from form to LaTeX - generate LaTeX from structured data
      setLatexContent(generateLatexFromStructuredData(structuredData));
    }
    setIsLatexMode(latex);
    setIsDirty(true);
  };

  const handleDownloadTex = () => {
    const content = isLatexMode ? latexContent : generateLatexFromStructuredData(structuredData);
    const blob = new Blob([content], { type: "text/x-tex" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${resumeName.replace(/[^a-z0-9]/gi, "_")}.tex`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadPdf = async () => {
    const token = getStoredToken();
    if (!token) {
      setError("Not authenticated");
      return;
    }

    const latex = isLatexMode ? latexContent : generateLatexFromStructuredData(structuredData);

    setPdfExporting(true);
    try {
      const pdfBlob = await downloadResumePdf(token, resumeId, latex);
      const url = URL.createObjectURL(pdfBlob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${resumeName.replace(/[^a-z0-9]/gi, "_")}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to export PDF");
    } finally {
      setPdfExporting(false);
    }
  };

  const handleAddResumeItems = async (itemIds: string[]) => {
    const token = getStoredToken();
    if (!token || itemIds.length === 0) return;

    setSaving(true);
    try {
      const updated = await addResumeItemsToResume(token, resumeId, { item_ids: itemIds });
      setResume(updated);
      setStructuredData(updated.structured_data || {});
      setLastSaved(new Date());
      setIsDirty(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add items to resume");
      throw err;
    } finally {
      setSaving(false);
    }
  };

  const handleDetectSkills = async () => {
    const token = getStoredToken();
    if (!token) return;

    setSaving(true);
    try {
      const updated = await detectResumeSkills(token, resumeId);
      setResume(updated);
      setStructuredData(updated.structured_data || {});
      setLastSaved(new Date());
      setIsDirty(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to auto-detect skills");
      throw err;
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container py-6">
        <LoadingState message="Loading resume editor..." className="min-h-[calc(100vh-3rem)]" />
      </div>
    );
  }

  if (error || !resume) {
    return (
      <div className="h-screen flex flex-col items-center justify-center gap-4">
        <p className="text-destructive">{error || "Resume not found"}</p>
        <Button variant="outline" onClick={() => router.push("/resume-builder" as Parameters<typeof router.push>[0])}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Resumes
        </Button>
      </div>
    );
  }

  return (
    <div className="flex h-screen min-w-0 flex-col overflow-hidden bg-muted">
      {/* Header */}
      <header className="border-b border-border bg-card px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push("/resume-builder" as Parameters<typeof router.push>[0])}
            >
              <ArrowLeft className="h-4 w-4 mr-1" />
              Back
            </Button>
            <div className="h-6 w-px bg-border" />
            <Input
              value={resumeName}
              onChange={(e) => {
                setResumeName(e.target.value);
                setIsDirty(true);
              }}
              className="h-8 w-full max-w-full text-sm font-medium border-transparent hover:border-border focus:border-border sm:w-64"
            />
          </div>

          <div className="flex flex-wrap items-center justify-end gap-3">
            {/* Save status */}
            <span className="inline-flex min-h-[1.25rem] min-w-[10.5rem] items-center justify-end text-right text-xs tabular-nums text-muted-foreground sm:mr-1">
              {saving ? (
                <span className="flex items-center gap-1">
                  <Spinner size={12} />
                  Saving...
                </span>
              ) : lastSaved ? (
                `Saved ${lastSaved.toLocaleTimeString()}`
              ) : isDirty ? (
                "Unsaved changes"
              ) : (
                "All changes saved"
              )}
            </span>

            {/* Mode toggle */}
            <div className="flex items-center gap-2 rounded-lg bg-gray-100 px-3 py-1.5">
              <button
                onClick={() => handleModeSwitch(true)}
                className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium transition-colors ${
                  isLatexMode
                    ? "bg-white shadow-sm text-gray-900"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                <Code className="h-3.5 w-3.5" />
                LaTeX
              </button>
              <button
                onClick={() => handleModeSwitch(false)}
                className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium transition-colors ${
                  !isLatexMode
                    ? "bg-white shadow-sm text-gray-900"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                <FileEdit className="h-3.5 w-3.5" />
                Form
              </button>
            </div>

            <Button variant="outline" size="sm" onClick={handleDownloadTex}>
              <Download className="h-4 w-4 mr-1" />
              Download .tex
            </Button>

            <Button variant="outline" size="sm" onClick={handleDownloadPdf} disabled={pdfExporting}>
              <Download className="h-4 w-4 mr-1" />
              {pdfExporting ? "Exporting PDF..." : "Download PDF"}
            </Button>

            <Button size="sm" onClick={handleSave} disabled={saving}>
              <Save className="h-4 w-4 mr-1" />
              Save
            </Button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden">
        {isLatexMode ? (
          <LatexEditor
            content={latexContent}
            onChange={handleLatexChange}
          />
        ) : (
          <FormEditor
            data={structuredData}
            onChange={updateStructuredData}
            onAddResumeItems={handleAddResumeItems}
            onDetectSkills={handleDetectSkills}
          />
        )}
      </div>
    </div>
  );
}

// ============================================================================
// LaTeX Editor Component
// ============================================================================

interface LatexEditorProps {
  content: string;
  onChange: (value: string) => void;
}

function LatexEditor({ content, onChange }: LatexEditorProps) {
  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col lg:flex-row">
      {/* Editor pane */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col border-b border-r-0 border-gray-200 bg-white lg:w-1/2 lg:border-b-0 lg:border-r">
        <div className="px-4 py-2 border-b border-gray-100 bg-gray-50">
          <span className="text-xs font-medium text-gray-600">LaTeX Source</span>
        </div>
        <div className="flex-1 overflow-hidden">
          <textarea
            value={content}
            onChange={(e) => onChange(e.target.value)}
            className="w-full h-full p-4 font-mono text-sm resize-none focus:outline-none bg-gray-900 text-gray-100"
            spellCheck={false}
            style={{ tabSize: 2 }}
          />
        </div>
      </div>

      {/* Preview pane */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col bg-gray-100 lg:w-1/2">
        <div className="px-4 py-2 border-b border-gray-200 bg-white">
          <span className="text-xs font-medium text-gray-600">Preview</span>
        </div>
        <div className="flex-1 overflow-auto p-4 sm:p-5 lg:p-6 xl:p-8">
          <div className="bg-white shadow-lg rounded-lg p-8 max-w-[8.5in] mx-auto min-h-[11in]">
            <PreviewPlaceholder latex={content} />
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Form Editor Component
// ============================================================================

interface FormEditorProps {
  data: ResumeStructuredData;
  onChange: (updates: Partial<ResumeStructuredData>) => void;
  onAddResumeItems: (itemIds: string[]) => Promise<void>;
  onDetectSkills: () => Promise<void>;
}

function FormEditor({ data, onChange, onAddResumeItems, onDetectSkills }: FormEditorProps) {
  const [activeTab, setActiveTab] = useState("contact");
  const [itemsDialogOpen, setItemsDialogOpen] = useState(false);
  const [resumeItems, setResumeItems] = useState<ResumeItemSummary[]>([]);
  const [selectedItemIds, setSelectedItemIds] = useState<string[]>([]);
  const [expandedItemIds, setExpandedItemIds] = useState<string[]>([]);
  const [itemDetailsById, setItemDetailsById] = useState<Record<string, ResumeItemRecord>>({});
  const [loadingItems, setLoadingItems] = useState(false);
  const [loadingItemDetails, setLoadingItemDetails] = useState<Record<string, boolean>>({});
  const [addingItems, setAddingItems] = useState(false);
  const [detectingSkills, setDetectingSkills] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const updateContact = (updates: Partial<ResumeContactInfo>) => {
    onChange({ contact: { ...data.contact, ...updates } as ResumeContactInfo });
  };

  const addEducation = () => {
    const newEntry: ResumeEducationEntry = {
      id: generateId(),
      institution: "",
      degree: "",
    };
    onChange({ education: [...(data.education || []), newEntry] });
  };

  const updateEducation = (index: number, updates: Partial<ResumeEducationEntry>) => {
    const updated = [...(data.education || [])];
    updated[index] = { ...updated[index], ...updates };
    onChange({ education: updated });
  };

  const removeEducation = (index: number) => {
    const updated = [...(data.education || [])];
    updated.splice(index, 1);
    onChange({ education: updated });
  };

  const addExperience = () => {
    const newEntry: ResumeExperienceEntry = {
      id: generateId(),
      company: "",
      position: "",
      bullets: [],
    };
    onChange({ experience: [...(data.experience || []), newEntry] });
  };

  const updateExperience = (index: number, updates: Partial<ResumeExperienceEntry>) => {
    const updated = [...(data.experience || [])];
    updated[index] = { ...updated[index], ...updates };
    onChange({ experience: updated });
  };

  const removeExperience = (index: number) => {
    const updated = [...(data.experience || [])];
    updated.splice(index, 1);
    onChange({ experience: updated });
  };

  const addProject = () => {
    const newEntry: ResumeProjectEntry = {
      id: generateId(),
      name: "",
      role: "",
      company: "",
      url: "",
      bullets: [],
    };
    onChange({ projects: [...(data.projects || []), newEntry] });
  };

  const updateProject = (index: number, updates: Partial<ResumeProjectEntry>) => {
    const updated = [...(data.projects || [])];
    updated[index] = { ...updated[index], ...updates };
    onChange({ projects: updated });
  };

  const removeProject = (index: number) => {
    const updated = [...(data.projects || [])];
    updated.splice(index, 1);
    onChange({ projects: updated });
  };

  const addAward = () => {
    const newEntry: ResumeAwardEntry = {
      id: generateId(),
      title: "",
    };
    onChange({ awards: [...(data.awards || []), newEntry] });
  };

  const updateAward = (index: number, updates: Partial<ResumeAwardEntry>) => {
    const updated = [...(data.awards || [])];
    updated[index] = { ...updated[index], ...updates };
    onChange({ awards: updated });
  };

  const removeAward = (index: number) => {
    const updated = [...(data.awards || [])];
    updated.splice(index, 1);
    onChange({ awards: updated });
  };

  const openAddItemsDialog = async () => {
    const token = getStoredToken();
    if (!token) {
      setModalError("Not authenticated");
      return;
    }

    setItemsDialogOpen(true);
    setLoadingItems(true);
    setModalError(null);

    try {
      const response = await listResumeItems(token, 100, 0);
      setResumeItems(response.items || []);
    } catch (err) {
      setModalError(err instanceof Error ? err.message : "Failed to load resume items");
    } finally {
      setLoadingItems(false);
    }
  };

  const toggleItemSelection = (itemId: string) => {
    setSelectedItemIds((prev) =>
      prev.includes(itemId) ? prev.filter((id) => id !== itemId) : [...prev, itemId]
    );
  };

  const toggleItemPreview = async (itemId: string) => {
    if (expandedItemIds.includes(itemId)) {
      setExpandedItemIds((prev) => prev.filter((id) => id !== itemId));
      return;
    }

    setExpandedItemIds((prev) => [...prev, itemId]);
    if (itemDetailsById[itemId]) return;

    const token = getStoredToken();
    if (!token) {
      setModalError("Not authenticated");
      return;
    }

    setLoadingItemDetails((prev) => ({ ...prev, [itemId]: true }));
    try {
      const detail = await getResumeItem(token, itemId);
      setItemDetailsById((prev) => ({ ...prev, [itemId]: detail }));
    } catch (err) {
      setModalError(err instanceof Error ? err.message : "Failed to load item preview");
    } finally {
      setLoadingItemDetails((prev) => ({ ...prev, [itemId]: false }));
    }
  };

  const handleBulkAddSelected = async () => {
    if (selectedItemIds.length === 0) return;

    setAddingItems(true);
    setModalError(null);
    try {
      await onAddResumeItems(selectedItemIds);
      setItemsDialogOpen(false);
      setSelectedItemIds([]);
      setExpandedItemIds([]);
    } catch (err) {
      setModalError(err instanceof Error ? err.message : "Failed to add selected items");
    } finally {
      setAddingItems(false);
    }
  };

  const handleDetectSkillsClick = async () => {
    setDetectingSkills(true);
    setModalError(null);
    try {
      await onDetectSkills();
    } catch (err) {
      setModalError(err instanceof Error ? err.message : "Failed to auto-detect skills");
    } finally {
      setDetectingSkills(false);
    }
  };

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col lg:flex-row">
      {/* Form pane */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden border-b border-r-0 border-gray-200 bg-white lg:w-1/2 lg:border-b-0 lg:border-r">
        <Tabs defaultValue="contact" onValueChange={setActiveTab} className="flex-1 flex flex-col">
          <div className="overflow-x-auto border-b border-gray-100 bg-gray-50">
            <TabsList className="h-auto min-w-max justify-start rounded-none border-0 bg-transparent px-4 py-2">
              <TabsTrigger value="contact" className="text-xs">Contact</TabsTrigger>
              <TabsTrigger value="education" className="text-xs">Education</TabsTrigger>
              <TabsTrigger value="experience" className="text-xs">Experience</TabsTrigger>
              <TabsTrigger value="projects" className="text-xs">Projects</TabsTrigger>
              <TabsTrigger value="skills" className="text-xs">Skills</TabsTrigger>
              <TabsTrigger value="awards" className="text-xs">Awards</TabsTrigger>
            </TabsList>
          </div>

          <div className="flex-1 overflow-auto p-4">
            <TabsContent value="contact" className="mt-0 space-y-4">
              <div className="space-y-2">
                <Label>Full Name</Label>
                <Input
                  value={data.contact?.full_name || ""}
                  onChange={(e) => updateContact({ full_name: e.target.value })}
                  placeholder="John Doe"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input
                    value={data.contact?.email || ""}
                    onChange={(e) => updateContact({ email: e.target.value })}
                    placeholder="john@example.com"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Phone</Label>
                  <Input
                    value={data.contact?.phone || ""}
                    onChange={(e) => updateContact({ phone: e.target.value })}
                    placeholder="(123) 456-7890"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>LinkedIn URL</Label>
                <Input
                  value={data.contact?.linkedin_url || ""}
                  onChange={(e) => updateContact({ linkedin_url: e.target.value })}
                  placeholder="https://linkedin.com/in/johndoe"
                />
              </div>
              <div className="space-y-2">
                <Label>GitHub URL</Label>
                <Input
                  value={data.contact?.github_url || ""}
                  onChange={(e) => updateContact({ github_url: e.target.value })}
                  placeholder="https://github.com/johndoe"
                />
              </div>
              <div className="space-y-2">
                <Label>Location</Label>
                <Input
                  value={data.contact?.location || ""}
                  onChange={(e) => updateContact({ location: e.target.value })}
                  placeholder="City, State"
                />
              </div>
            </TabsContent>

            <TabsContent value="education" className="mt-0 space-y-4">
              {(data.education || []).map((edu, idx) => (
                <div key={edu.id} className="p-4 border border-gray-200 rounded-lg space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Education #{idx + 1}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeEducation(idx)}
                      className="text-red-600 hover:text-red-700"
                    >
                      Remove
                    </Button>
                  </div>
                  <div className="space-y-2">
                    <Label>Institution</Label>
                    <Input
                      value={edu.institution}
                      onChange={(e) => updateEducation(idx, { institution: e.target.value })}
                      placeholder="University Name"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label>Degree</Label>
                      <Input
                        value={edu.degree}
                        onChange={(e) => updateEducation(idx, { degree: e.target.value })}
                        placeholder="Bachelor of Science"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Field of Study</Label>
                      <Input
                        value={edu.field_of_study || ""}
                        onChange={(e) => updateEducation(idx, { field_of_study: e.target.value })}
                        placeholder="Computer Science"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label>Start Date</Label>
                      <Input
                        value={edu.start_date || ""}
                        onChange={(e) => updateEducation(idx, { start_date: e.target.value })}
                        placeholder="Aug 2018"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>End Date</Label>
                      <Input
                        value={edu.end_date || ""}
                        onChange={(e) => updateEducation(idx, { end_date: e.target.value })}
                        placeholder="May 2022"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Location</Label>
                    <Input
                      value={edu.location || ""}
                      onChange={(e) => updateEducation(idx, { location: e.target.value })}
                      placeholder="City, State"
                    />
                  </div>
                </div>
              ))}
              <Button variant="outline" onClick={addEducation} className="w-full">
                + Add Education
              </Button>
            </TabsContent>

            <TabsContent value="experience" className="mt-0 space-y-4">
              {(data.experience || []).map((exp, idx) => (
                <div key={exp.id} className="p-4 border border-gray-200 rounded-lg space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Experience #{idx + 1}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeExperience(idx)}
                      className="text-red-600 hover:text-red-700"
                    >
                      Remove
                    </Button>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label>Company</Label>
                      <Input
                        value={exp.company}
                        onChange={(e) => updateExperience(idx, { company: e.target.value })}
                        placeholder="Company Name"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Position</Label>
                      <Input
                        value={exp.position}
                        onChange={(e) => updateExperience(idx, { position: e.target.value })}
                        placeholder="Software Engineer"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label>Start Date</Label>
                      <Input
                        value={exp.start_date || ""}
                        onChange={(e) => updateExperience(idx, { start_date: e.target.value })}
                        placeholder="Jan 2022"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>End Date</Label>
                      <Input
                        value={exp.end_date || ""}
                        onChange={(e) => updateExperience(idx, { end_date: e.target.value })}
                        placeholder="Present"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Location</Label>
                    <Input
                      value={exp.location || ""}
                      onChange={(e) => updateExperience(idx, { location: e.target.value })}
                      placeholder="City, State"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Bullet Points (one per line)</Label>
                    <Textarea
                      value={(exp.bullets || []).join("\n")}
                      onChange={(e) =>
                        // Keep empty lines while typing so Enter key works naturally
                        updateExperience(idx, { bullets: e.target.value.split("\n") })
                      }
                      onBlur={(e) =>
                        // Filter blank lines only when focus leaves the field
                        updateExperience(idx, {
                          bullets: e.target.value.split("\n").filter((b) => b.trim()),
                        })
                      }
                      placeholder="Developed REST API using FastAPI&#10;Led team of 3 engineers&#10;Reduced latency by 40%"
                      rows={4}
                    />
                  </div>
                </div>
              ))}
              <Button variant="outline" onClick={addExperience} className="w-full">
                + Add Experience
              </Button>
            </TabsContent>

            <TabsContent value="projects" className="mt-0 space-y-4">
              {(data.projects || []).map((proj, idx) => (
                <div key={proj.id} className="p-4 border border-gray-200 rounded-lg space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Project #{idx + 1}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeProject(idx)}
                      className="text-red-600 hover:text-red-700"
                    >
                      Remove
                    </Button>
                  </div>
                  <div className="space-y-2">
                    <Label>Project Name</Label>
                    <Input
                      value={proj.name}
                      onChange={(e) => updateProject(idx, { name: e.target.value })}
                      placeholder="Project Name"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label>Role</Label>
                      <Input
                        value={proj.role || ""}
                        onChange={(e) => updateProject(idx, { role: e.target.value })}
                        placeholder="Lead Developer"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Company</Label>
                      <Input
                        value={proj.company || ""}
                        onChange={(e) => updateProject(idx, { company: e.target.value })}
                        placeholder="Freelance / Personal / Company"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Technologies</Label>
                    <Input
                      value={proj.technologies || ""}
                      onChange={(e) => updateProject(idx, { technologies: e.target.value })}
                      placeholder="React, TypeScript, Node.js"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Project URL</Label>
                    <Input
                      value={proj.url || ""}
                      onChange={(e) => updateProject(idx, { url: e.target.value })}
                      placeholder="https://github.com/username/project"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label>Start Date</Label>
                      <Input
                        value={proj.start_date || ""}
                        onChange={(e) => updateProject(idx, { start_date: e.target.value })}
                        placeholder="Jun 2023"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>End Date</Label>
                      <Input
                        value={proj.end_date || ""}
                        onChange={(e) => updateProject(idx, { end_date: e.target.value })}
                        placeholder="Present"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Bullet Points (one per line)</Label>
                    <Textarea
                      value={(proj.bullets || []).join("\n")}
                      onChange={(e) =>
                        // Keep empty lines while typing so Enter key works naturally
                        updateProject(idx, { bullets: e.target.value.split("\n") })
                      }
                      onBlur={(e) =>
                        // Filter blank lines only when focus leaves the field
                        updateProject(idx, {
                          bullets: e.target.value.split("\n").filter((b) => b.trim()),
                        })
                      }
                      placeholder="Built full-stack web app&#10;Implemented OAuth authentication&#10;Deployed to AWS"
                      rows={4}
                    />
                  </div>
                </div>
              ))}
              <div className="grid grid-cols-2 gap-3">
                <Button variant="outline" onClick={openAddItemsDialog}>
                  Add from Projects
                </Button>
                <Button variant="outline" onClick={addProject}>
                  + Add Project
                </Button>
              </div>
            </TabsContent>

            <TabsContent value="skills" className="mt-0 space-y-4">
              <Button variant="outline" onClick={handleDetectSkillsClick} disabled={detectingSkills} className="w-full">
                {detectingSkills ? "Detecting..." : "Auto-detect Skills from Projects"}
              </Button>
              <div className="space-y-2">
                <Label>Programming Languages (comma-separated)</Label>
                <CommaSeparatedInput
                  value={data.skills?.languages || []}
                  onChange={(languages) =>
                    onChange({
                      skills: {
                        ...data.skills,
                        languages,
                      },
                    })
                  }
                  placeholder="Python, JavaScript, TypeScript, Java"
                />
              </div>
              <div className="space-y-2">
                <Label>Frameworks (comma-separated)</Label>
                <CommaSeparatedInput
                  value={data.skills?.frameworks || []}
                  onChange={(frameworks) =>
                    onChange({
                      skills: {
                        ...data.skills,
                        frameworks,
                      },
                    })
                  }
                  placeholder="React, Node.js, FastAPI, Next.js"
                />
              </div>
              <div className="space-y-2">
                <Label>Developer Tools (comma-separated)</Label>
                <CommaSeparatedInput
                  value={data.skills?.developer_tools || []}
                  onChange={(developer_tools) =>
                    onChange({
                      skills: {
                        ...data.skills,
                        developer_tools,
                      },
                    })
                  }
                  placeholder="Git, Docker, VS Code, AWS"
                />
              </div>
              <div className="space-y-2">
                <Label>Libraries (comma-separated)</Label>
                <CommaSeparatedInput
                  value={data.skills?.libraries || []}
                  onChange={(libraries) =>
                    onChange({
                      skills: {
                        ...data.skills,
                        libraries,
                      },
                    })
                  }
                  placeholder="pandas, NumPy, TensorFlow"
                />
              </div>
            </TabsContent>

            <TabsContent value="awards" className="mt-0 space-y-4">
              {(data.awards || []).map((award, idx) => (
                <div key={award.id} className="p-4 border border-gray-200 rounded-lg space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Award #{idx + 1}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeAward(idx)}
                      className="text-red-600 hover:text-red-700"
                    >
                      Remove
                    </Button>
                  </div>
                  <div className="space-y-2">
                    <Label>Award Title</Label>
                    <Input
                      value={award.title}
                      onChange={(e) => updateAward(idx, { title: e.target.value })}
                      placeholder="Dean's List, Hackathon Winner, etc."
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label>Issuer / Organization</Label>
                      <Input
                        value={award.issuer || ""}
                        onChange={(e) => updateAward(idx, { issuer: e.target.value })}
                        placeholder="University, Company, etc."
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Date</Label>
                      <Input
                        value={award.date || ""}
                        onChange={(e) => updateAward(idx, { date: e.target.value })}
                        placeholder="May 2024"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Description (optional)</Label>
                    <Input
                      value={award.description || ""}
                      onChange={(e) => updateAward(idx, { description: e.target.value })}
                      placeholder="Brief description of the award"
                    />
                  </div>
                </div>
              ))}
              <Button variant="outline" onClick={addAward} className="w-full">
                + Add Award
              </Button>
            </TabsContent>
          </div>
        </Tabs>
      </div>

      <Dialog open={itemsDialogOpen} onOpenChange={setItemsDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>Add Project Blocks from Resume Items</DialogTitle>
          </DialogHeader>

          <div className="flex items-center justify-between text-sm text-gray-600">
            <span>{selectedItemIds.length} selected</span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedItemIds(resumeItems.map((item) => item.id))}
                disabled={resumeItems.length === 0}
              >
                Select All
              </Button>
              <Button variant="outline" size="sm" onClick={() => setSelectedItemIds([])}>
                Deselect All
              </Button>
            </div>
          </div>

          {modalError && <p className="text-sm text-red-600">{modalError}</p>}

          <div className="flex-1 overflow-auto space-y-3 py-1">
            {loadingItems ? (
              <div className="text-sm text-gray-500">Loading resume items...</div>
            ) : resumeItems.length === 0 ? (
              <div className="text-sm text-gray-500">No resume items found.</div>
            ) : (
              resumeItems.map((item) => {
                const selected = selectedItemIds.includes(item.id);
                const expanded = expandedItemIds.includes(item.id);
                const detail = itemDetailsById[item.id];
                return (
                  <div key={item.id} className="border border-gray-200 rounded-lg p-3 space-y-2">
                    <div className="flex items-start justify-between gap-3">
                      <label className="flex items-start gap-2 cursor-pointer flex-1 min-w-0">
                        <Checkbox checked={selected} onCheckedChange={() => toggleItemSelection(item.id)} />
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">{item.project_name}</p>
                          <p className="text-xs text-gray-500">
                            {item.start_date || "Unknown start"}
                            {item.end_date ? ` - ${item.end_date}` : ""}
                          </p>
                        </div>
                      </label>
                      <Button variant="outline" size="sm" onClick={() => toggleItemPreview(item.id)}>
                        {expanded ? "Hide Preview" : "Preview"}
                      </Button>
                    </div>

                    {expanded && (
                      <div className="bg-gray-50 border border-gray-200 rounded-md p-3 text-sm">
                        {loadingItemDetails[item.id] ? (
                          <p className="text-gray-500">Loading preview...</p>
                        ) : detail ? (
                          <div className="space-y-2">
                            <p className="text-xs uppercase tracking-wide text-gray-500">Bullets</p>
                            {detail.bullets.length > 0 ? (
                              <ul className="list-disc list-inside space-y-1">
                                {detail.bullets.map((bullet, idx) => (
                                  <li key={`${item.id}-${idx}`}>{bullet}</li>
                                ))}
                              </ul>
                            ) : (
                              <p className="text-gray-500">No bullets found for this item.</p>
                            )}
                          </div>
                        ) : (
                          <p className="text-gray-500">Preview unavailable.</p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-gray-200">
            <Button
              variant="outline"
              onClick={() => {
                setItemsDialogOpen(false);
                setModalError(null);
              }}
              disabled={addingItems}
            >
              Cancel
            </Button>
            <Button onClick={handleBulkAddSelected} disabled={addingItems || selectedItemIds.length === 0}>
              {addingItems ? "Adding..." : `Add ${selectedItemIds.length} Item${selectedItemIds.length === 1 ? "" : "s"}`}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Preview pane */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col bg-gray-100 lg:w-1/2">
        <div className="px-4 py-2 border-b border-gray-200 bg-white">
          <span className="text-xs font-medium text-gray-600">Preview</span>
        </div>
        <div className="flex-1 overflow-auto p-4 sm:p-5 lg:p-6 xl:p-8">
          <div className="bg-white shadow-lg rounded-lg p-8 max-w-[8.5in] mx-auto min-h-[11in]">
            <FormPreview data={data} />
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Preview Components
// ============================================================================

function PreviewPlaceholder({ latex }: { latex: string }) {
  // Parse basic structure from LaTeX for a simple preview
  // This is a simplified preview - real LaTeX rendering would require a server
  
  return (
    <div className="text-sm text-gray-600 space-y-4">
      <div className="text-center border-b pb-4 mb-4">
        <p className="text-xs text-gray-400 mb-2">LaTeX Preview</p>
        <p className="text-gray-500">
          To see the compiled PDF, download the .tex file and compile it with
          a LaTeX editor like Overleaf, TeXShop, or MiKTeX.
        </p>
      </div>
      <div className="bg-gray-50 rounded p-4 font-mono text-xs max-h-[800px] overflow-auto whitespace-pre-wrap">
        {latex.slice(0, 3000)}
        {latex.length > 3000 && "\n\n... (truncated)"}
      </div>
    </div>
  );
}

function FormPreview({ data }: { data: ResumeStructuredData }) {
  return (
    <div className="space-y-6 text-gray-900">
      {/* Header */}
      {data.contact && (
        <div className="text-center border-b pb-4">
          <h1 className="text-2xl font-bold">{data.contact.full_name || "Your Name"}</h1>
          <div className="text-sm text-gray-600 mt-1 flex flex-wrap justify-center gap-2">
            {data.contact.phone && <a className="text-blue-600 underline" href={`tel:${data.contact.phone}`}>{data.contact.phone}</a>}
            {data.contact.email && (
              <>
                {data.contact.phone && <span>|</span>}
                <a className="text-blue-600 underline" href={`mailto:${data.contact.email}`}>{data.contact.email}</a>
              </>
            )}
            {data.contact.linkedin_url && (
              <>
                <span>|</span>
                <a className="text-blue-600 underline" href={normalizeExternalUrl(data.contact.linkedin_url)} target="_blank" rel="noopener noreferrer">
                  {displayUrl(data.contact.linkedin_url)}
                </a>
              </>
            )}
            {data.contact.github_url && (
              <>
                <span>|</span>
                <a className="text-blue-600 underline" href={normalizeExternalUrl(data.contact.github_url)} target="_blank" rel="noopener noreferrer">
                  {displayUrl(data.contact.github_url)}
                </a>
              </>
            )}
            {data.contact.portfolio_url && (
              <>
                <span>|</span>
                <a className="text-blue-600 underline" href={normalizeExternalUrl(data.contact.portfolio_url)} target="_blank" rel="noopener noreferrer">
                  {displayUrl(data.contact.portfolio_url)}
                </a>
              </>
            )}
          </div>
        </div>
      )}

      {/* Education */}
      {data.education && data.education.length > 0 && (
        <section>
          <h2 className="text-lg font-bold border-b border-gray-300 pb-1 mb-2">Education</h2>
          {data.education.map((edu) => (
            <div key={edu.id} className="mb-2">
              <div className="flex justify-between">
                <span className="font-semibold">{edu.institution}</span>
                <span className="text-gray-600">{edu.location}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="italic">
                  {edu.degree}
                  {edu.field_of_study && `, ${edu.field_of_study}`}
                </span>
                <span className="italic text-gray-600">
                  {edu.start_date && edu.end_date
                    ? `${edu.start_date} -- ${edu.end_date}`
                    : edu.start_date || edu.end_date}
                </span>
              </div>
            </div>
          ))}
        </section>
      )}

      {/* Experience */}
      {data.experience && data.experience.length > 0 && (
        <section>
          <h2 className="text-lg font-bold border-b border-gray-300 pb-1 mb-2">Experience</h2>
          {data.experience.map((exp) => (
            <div key={exp.id} className="mb-3">
              <div className="flex justify-between">
                <span className="font-semibold">{exp.position}</span>
                <span className="text-gray-600">
                  {exp.start_date && exp.end_date
                    ? `${exp.start_date} -- ${exp.end_date}`
                    : exp.start_date || exp.end_date}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="italic">{exp.company}</span>
                <span className="italic text-gray-600">{exp.location}</span>
              </div>
              {exp.bullets && exp.bullets.length > 0 && (
                <ul className="list-disc list-inside mt-1 text-sm space-y-0.5">
                  {exp.bullets.map((bullet, i) => (
                    <li key={i}>{bullet}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </section>
      )}

      {/* Projects */}
      {data.projects && data.projects.length > 0 && (
        <section>
          <h2 className="text-lg font-bold border-b border-gray-300 pb-1 mb-2">Projects</h2>
          {data.projects.map((proj) => (
            <div key={proj.id} className="mb-3">
              <div className="flex justify-between">
                <span>
                  <span className="font-semibold">{proj.name}</span>
                  {(proj.role || proj.company) && (
                    <span className="italic text-gray-600"> {proj.role || "Contributor"}{proj.company ? ` at ${proj.company}` : ""}</span>
                  )}
                  {proj.technologies && (
                    <span className="italic text-gray-600"> | {proj.technologies}</span>
                  )}
                </span>
                <span className="text-gray-600">
                  {proj.start_date && proj.end_date
                    ? `${proj.start_date} -- ${proj.end_date}`
                    : proj.start_date || proj.end_date}
                </span>
              </div>
              {proj.bullets && proj.bullets.length > 0 && (
                <ul className="list-disc list-inside mt-1 text-sm space-y-0.5">
                  {proj.bullets.map((bullet, i) => (
                    <li key={i}>{bullet}</li>
                  ))}
                </ul>
              )}
              {proj.url && (
                <a
                  className="text-sm text-blue-600 underline"
                  href={normalizeExternalUrl(proj.url)}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {displayUrl(proj.url)}
                </a>
              )}
            </div>
          ))}
        </section>
      )}

      {/* Awards */}
      {data.awards && data.awards.length > 0 && (
        <section>
          <h2 className="text-lg font-bold border-b border-gray-300 pb-1 mb-2">Awards & Honors</h2>
          {data.awards.map((award) => (
            <div key={award.id} className="mb-2">
              <div className="flex justify-between">
                <span className="font-semibold">{award.title}</span>
                <span className="text-gray-600">{award.date}</span>
              </div>
              {award.issuer && (
                <div className="text-sm italic text-gray-600">{award.issuer}</div>
              )}
              {award.description && (
                <ul className="list-disc list-inside mt-1 text-sm space-y-0.5">
                  <li>{award.description}</li>
                </ul>
              )}
            </div>
          ))}
        </section>
      )}

      {/* Skills */}
      {data.skills && (
        <section>
          <h2 className="text-lg font-bold border-b border-gray-300 pb-1 mb-2">
            Technical Skills
          </h2>
          <div className="text-sm space-y-1">
            {data.skills.languages && data.skills.languages.length > 0 && (
              <p>
                <span className="font-semibold">Languages:</span>{" "}
                {data.skills.languages.join(", ")}
              </p>
            )}
            {data.skills.frameworks && data.skills.frameworks.length > 0 && (
              <p>
                <span className="font-semibold">Frameworks:</span>{" "}
                {data.skills.frameworks.join(", ")}
              </p>
            )}
            {data.skills.developer_tools && data.skills.developer_tools.length > 0 && (
              <p>
                <span className="font-semibold">Developer Tools:</span>{" "}
                {data.skills.developer_tools.join(", ")}
              </p>
            )}
            {data.skills.libraries && data.skills.libraries.length > 0 && (
              <p>
                <span className="font-semibold">Libraries:</span>{" "}
                {data.skills.libraries.join(", ")}
              </p>
            )}
          </div>
        </section>
      )}

      {/* Empty state */}
      {!data.contact &&
        (!data.education || data.education.length === 0) &&
        (!data.experience || data.experience.length === 0) &&
        (!data.projects || data.projects.length === 0) &&
        (!data.awards || data.awards.length === 0) &&
        !data.skills && (
          <div className="text-center text-gray-400 py-12">
            <p>Start adding content using the form on the left</p>
          </div>
        )}
    </div>
  );
}

// Suspense boundary required because useSearchParams() needs it for static export
export default function ResumeEditorPage() {
  return (
    <Suspense>
      <ResumeEditorPageInner />
    </Suspense>
  );
}
