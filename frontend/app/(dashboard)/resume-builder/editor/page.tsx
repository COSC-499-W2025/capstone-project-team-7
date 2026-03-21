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
import { getUserResume, updateUserResume } from "@/lib/api/user-resume";
import { getTemplateLatex, generateLatexFromStructuredData } from "@/lib/latex-templates";
import type {
  UserResumeRecord,
  ResumeTemplate,
  ResumeStructuredData,
  ResumeContactInfo,
  ResumeEducationEntry,
  ResumeExperienceEntry,
  ResumeProjectEntry,
} from "@/types/user-resume";

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
        setLatexContent(data.latex_content || getTemplateLatex(data.template));
        setStructuredData(data.structured_data || {});
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
          structured_data: !isLatexMode ? debouncedStructured : undefined,
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
    <div className="h-screen flex flex-col bg-muted">
      {/* Header */}
      <header className="bg-card border-b border-border px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
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
              className="w-64 h-8 text-sm font-medium border-transparent hover:border-border focus:border-border"
            />
          </div>

          <div className="flex items-center gap-3">
            {/* Save status */}
            <span className="text-xs text-muted-foreground">
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
            <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 rounded-lg">
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

            <Button size="sm" onClick={handleSave} disabled={saving}>
              <Save className="h-4 w-4 mr-1" />
              Save
            </Button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {isLatexMode ? (
          <LatexEditor
            content={latexContent}
            onChange={handleLatexChange}
          />
        ) : (
          <FormEditor
            data={structuredData}
            onChange={updateStructuredData}
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
    <div className="flex-1 flex">
      {/* Editor pane */}
      <div className="w-1/2 flex flex-col border-r border-gray-200 bg-white">
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
      <div className="w-1/2 flex flex-col bg-gray-100">
        <div className="px-4 py-2 border-b border-gray-200 bg-white">
          <span className="text-xs font-medium text-gray-600">Preview</span>
        </div>
        <div className="flex-1 overflow-auto p-8">
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
}

function FormEditor({ data, onChange }: FormEditorProps) {
  const [activeTab, setActiveTab] = useState("contact");

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

  return (
    <div className="flex-1 flex">
      {/* Form pane */}
      <div className="w-1/2 flex flex-col border-r border-gray-200 bg-white overflow-hidden">
        <Tabs defaultValue="contact" onValueChange={setActiveTab} className="flex-1 flex flex-col">
          <TabsList className="px-4 py-2 border-b border-gray-100 bg-gray-50 justify-start rounded-none h-auto">
            <TabsTrigger value="contact" className="text-xs">Contact</TabsTrigger>
            <TabsTrigger value="education" className="text-xs">Education</TabsTrigger>
            <TabsTrigger value="experience" className="text-xs">Experience</TabsTrigger>
            <TabsTrigger value="projects" className="text-xs">Projects</TabsTrigger>
            <TabsTrigger value="skills" className="text-xs">Skills</TabsTrigger>
          </TabsList>

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
                  <div className="space-y-2">
                    <Label>Technologies</Label>
                    <Input
                      value={proj.technologies || ""}
                      onChange={(e) => updateProject(idx, { technologies: e.target.value })}
                      placeholder="React, TypeScript, Node.js"
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
              <Button variant="outline" onClick={addProject} className="w-full">
                + Add Project
              </Button>
            </TabsContent>

            <TabsContent value="skills" className="mt-0 space-y-4">
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
          </div>
        </Tabs>
      </div>

      {/* Preview pane */}
      <div className="w-1/2 flex flex-col bg-gray-100">
        <div className="px-4 py-2 border-b border-gray-200 bg-white">
          <span className="text-xs font-medium text-gray-600">Preview</span>
        </div>
        <div className="flex-1 overflow-auto p-8">
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
            {data.contact.phone && <span>{data.contact.phone}</span>}
            {data.contact.email && (
              <>
                {data.contact.phone && <span>|</span>}
                <span>{data.contact.email}</span>
              </>
            )}
            {data.contact.linkedin_url && (
              <>
                <span>|</span>
                <span className="text-blue-600 underline">
                  {data.contact.linkedin_url.replace(/^https?:\/\//, "")}
                </span>
              </>
            )}
            {data.contact.github_url && (
              <>
                <span>|</span>
                <span className="text-blue-600 underline">
                  {data.contact.github_url.replace(/^https?:\/\//, "")}
                </span>
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
