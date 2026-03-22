"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Plus,
  Loader2,
  FileText,
  Copy,
  Trash2,
  RefreshCw,
  Code,
  FileEdit,
  MoreVertical,
  Wand2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ProfileForm } from "./profile-form";
import { GenerateFromProfileModal } from "./generate-from-profile-modal";
import { getStoredToken } from "@/lib/auth";
import {
  listUserResumes,
  createUserResume,
  deleteUserResume,
  duplicateUserResume,
  getResumeProfile,
  saveResumeProfile,
} from "@/lib/api/user-resume";
import { getTemplateLatex } from "@/lib/latex-templates";
import type { UserResumeSummary, ResumeTemplate, ResumeStructuredData } from "@/types/user-resume";

const TEMPLATE_INFO: Record<ResumeTemplate, { name: string; description: string }> = {
  jake: {
    name: "Jake's Resume",
    description: "Clean, ATS-friendly single-column template",
  },
  classic: {
    name: "Classic",
    description: "Traditional professional layout",
  },
  modern: {
    name: "Modern",
    description: "Contemporary design with clean sections",
  },
  minimal: {
    name: "Minimal",
    description: "Ultra-clean minimalist design",
  },
  custom: {
    name: "Custom",
    description: "Start from scratch",
  },
};

export default function ResumeBuilderPage() {
  const router = useRouter();
  const [resumes, setResumes] = useState<UserResumeSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Create dialog state
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newResumeName, setNewResumeName] = useState("My Resume");
  const [newResumeTemplate, setNewResumeTemplate] = useState<ResumeTemplate>("jake");
  const [newResumeLatexMode, setNewResumeLatexMode] = useState(true);
  const [createError, setCreateError] = useState<string | null>(null);

  // Profile state
  const [profile, setProfile] = useState<ResumeStructuredData | null>(null);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileSaved, setProfileSaved] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [generateModalOpen, setGenerateModalOpen] = useState(false);

  const fetchResumes = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setError("Not authenticated. Please log in.");
      setLoading(false);
      setRefreshing(false);
      return;
    }
    try {
      setError(null);
      const res = await listUserResumes(token);
      setResumes(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load resumes");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchResumes();
  }, [fetchResumes]);

  // Load the user's saved profile once on mount
  useEffect(() => {
    const loadProfile = async () => {
      const token = getStoredToken();
      if (!token) return;
      const record = await getResumeProfile(token);
      setProfile(record?.structured_data ?? null);
    };
    loadProfile();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchResumes();
  };

  const openCreateDialog = () => {
    setNewResumeName("My Resume");
    setNewResumeTemplate("jake");
    setNewResumeLatexMode(true);
    setCreateError(null);
    setCreateDialogOpen(true);
  };

  const handleCreate = async () => {
    if (!newResumeName.trim()) {
      setCreateError("Resume name is required");
      return;
    }

    const token = getStoredToken();
    if (!token) return;

    setCreating(true);
    setCreateError(null);

    try {
      const created = await createUserResume(token, {
        name: newResumeName.trim(),
        template: newResumeTemplate,
        is_latex_mode: newResumeLatexMode,
        latex_content: newResumeLatexMode ? getTemplateLatex(newResumeTemplate) : null,
      });
      setCreateDialogOpen(false);
      // Navigate to the editor
      router.push(`/resume-builder/editor?id=${created.id}` as Parameters<typeof router.push>[0]);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Failed to create resume");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
    const token = getStoredToken();
    if (!token) return;
    try {
      await deleteUserResume(token, id);
      setResumes((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete resume");
    }
  };

  const handleDuplicate = async (id: string) => {
    const token = getStoredToken();
    if (!token) return;
    try {
      const duplicated = await duplicateUserResume(token, id);
      setResumes((prev) => [duplicated, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to duplicate resume");
    }
  };

  const handleOpen = (id: string) => {
    router.push(`/resume-builder/editor?id=${id}` as Parameters<typeof router.push>[0]);
  };

  const handleSaveProfile = async (data: ResumeStructuredData) => {
    const token = getStoredToken();
    if (!token) return;
    setProfileSaving(true);
    setProfileError(null);
    try {
      await saveResumeProfile(token, data);
      setProfile(data);
      setProfileSaved(true);
      setTimeout(() => setProfileSaved(false), 3000);
    } catch (err) {
      setProfileError(err instanceof Error ? err.message : "Failed to save profile");
    } finally {
      setProfileSaving(false);
    }
  };

  const handleGeneratedResume = (id: string) => {
    router.push(`/resume-builder/editor?id=${id}` as Parameters<typeof router.push>[0]);
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  if (loading) {
    return (
      <div className="p-8">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
            <span className="ml-3 text-gray-500">Loading resumes...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <Tabs defaultValue="resumes">
          {/* Header */}
          <div className="px-8 py-6 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
                  Resume Builder
                </h1>
                <p className="mt-2 text-sm text-gray-600">
                  Create and manage your professional resumes
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
                {profile && (
                  <button
                    onClick={() => setGenerateModalOpen(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition-colors"
                    title="Create a new resume pre-filled with your saved profile"
                  >
                    <Wand2 size={18} />
                    <span className="font-medium">Generate from Profile</span>
                  </button>
                )}
                <button
                  onClick={openCreateDialog}
                  className="flex items-center gap-2 px-5 py-2.5 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors shadow-sm"
                >
                  <Plus size={20} />
                  <span className="font-medium">New Resume</span>
                </button>
              </div>
            </div>
            <div className="mt-4">
              <TabsList>
                <TabsTrigger value="resumes">My Resumes</TabsTrigger>
                <TabsTrigger value="profile">My Profile</TabsTrigger>
              </TabsList>
            </div>
          </div>

          {/* ── Resumes tab ─────────────────────────────────────────────────── */}
          <TabsContent value="resumes">
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
              {resumes.length === 0 ? (
                <div className="text-center py-16">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-100 rounded-full mb-4">
                    <FileText className="h-8 w-8 text-gray-400" />
                  </div>
                  <h2 className="text-xl font-semibold text-gray-900 mb-2">
                    No resumes yet
                  </h2>
                  <p className="text-gray-600 mb-6 max-w-md mx-auto">
                    Create your first professional resume using our LaTeX editor or
                    simple form-based builder.
                  </p>
                  <div className="flex items-center justify-center gap-3">
                    {profile && (
                      <button
                        onClick={() => setGenerateModalOpen(true)}
                        className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                      >
                        <Wand2 size={18} />
                        Generate from Profile
                      </button>
                    )}
                    <button
                      onClick={openCreateDialog}
                      className="inline-flex items-center gap-2 px-5 py-2.5 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
                    >
                      <Plus size={18} />
                      Create Your First Resume
                    </button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {resumes.map((resume) => (
                    <div
                      key={resume.id}
                      className="group relative border border-gray-200 rounded-xl p-5 hover:border-gray-300 hover:shadow-sm transition-all cursor-pointer"
                      onClick={() => handleOpen(resume.id)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className="flex items-center justify-center w-10 h-10 bg-gray-100 rounded-lg">
                            {resume.is_latex_mode ? (
                              <Code className="h-5 w-5 text-gray-600" />
                            ) : (
                              <FileEdit className="h-5 w-5 text-gray-600" />
                            )}
                          </div>
                          <div>
                            <h3 className="font-semibold text-gray-900 truncate max-w-[180px]">
                              {resume.name}
                            </h3>
                            <p className="text-xs text-gray-500">
                              {TEMPLATE_INFO[resume.template]?.name || resume.template}
                            </p>
                          </div>
                        </div>
                        <DropdownMenu>
                          <DropdownMenuTrigger
                            onClick={(e) => e.stopPropagation()}
                            className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-md hover:bg-gray-100"
                          >
                            <MoreVertical className="h-4 w-4 text-gray-500" />
                          </DropdownMenuTrigger>
                          <DropdownMenuContent>
                            <DropdownMenuItem
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDuplicate(resume.id);
                              }}
                            >
                              <Copy className="h-4 w-4 mr-2" />
                              Duplicate
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDelete(resume.id, resume.name);
                              }}
                              className="text-red-600"
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                      <div className="mt-4 pt-4 border-t border-gray-100">
                        <div className="flex items-center justify-between text-xs text-gray-500">
                          <span>
                            {resume.is_latex_mode ? "LaTeX" : "Form"} mode
                          </span>
                          <span>
                            Updated {formatDate(resume.updated_at)}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabsContent>

          {/* ── Profile tab ─────────────────────────────────────────────────── */}
          <TabsContent value="profile" className="p-8">
            <ProfileForm
              initialData={profile ?? {}}
              onSave={handleSaveProfile}
              saving={profileSaving}
              saved={profileSaved}
              error={profileError}
            />
          </TabsContent>
        </Tabs>
      </div>

      {/* Generate from Profile Modal */}
      {profile && (
        <GenerateFromProfileModal
          open={generateModalOpen}
          onOpenChange={setGenerateModalOpen}
          profile={profile}
          onGenerated={handleGeneratedResume}
        />
      )}

      {/* Create Resume Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="sm:max-w-[480px]">
          <DialogHeader>
            <DialogTitle>Create New Resume</DialogTitle>
            <DialogDescription>
              Choose a template and editing mode to get started.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {createError && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {createError}
              </p>
            )}

            <div className="space-y-2">
              <Label htmlFor="resume-name">Resume Name</Label>
              <Input
                id="resume-name"
                placeholder="e.g. Software Engineer Resume"
                value={newResumeName}
                onChange={(e) => setNewResumeName(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>Template</Label>
              <Select
                value={newResumeTemplate}
                onValueChange={(v) => setNewResumeTemplate(v as ResumeTemplate)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(TEMPLATE_INFO) as ResumeTemplate[]).map((key) => (
                    <SelectItem key={key} value={key}>
                      <div className="flex flex-col">
                        <span>{TEMPLATE_INFO[key].name}</span>
                        <span className="text-xs text-gray-500">
                          {TEMPLATE_INFO[key].description}
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div>
                <Label htmlFor="latex-mode" className="text-sm font-medium">
                  LaTeX Editor Mode
                </Label>
                <p className="text-xs text-gray-500 mt-0.5">
                  {newResumeLatexMode
                    ? "Full control with LaTeX syntax"
                    : "Simple form-based editing"}
                </p>
              </div>
              <Switch
                id="latex-mode"
                checked={newResumeLatexMode}
                onCheckedChange={setNewResumeLatexMode}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCreateDialogOpen(false)}
              disabled={creating}
            >
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={creating}>
              {creating ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                "Create Resume"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
