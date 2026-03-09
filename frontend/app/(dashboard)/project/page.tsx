"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { DocumentAnalysisTab } from "@/components/project/document-analysis-tab";
import { PdfAnalysisTab } from "@/components/project/pdf-analysis-tab";
import { getStoredToken } from "@/lib/auth";
import {CodeAnalysisTab} from "@/components/project/code-analysis-tab";
import { GitAnalysisTab } from "@/components/project/git-analysis-tab";
import { DuplicateFinderTab } from "@/components/project/duplicate-finder-tab";
import {
  getProjects,
  getProjectById,
  getProjectSkillTimeline,
  generateProjectSkillSummary,
  exportProjectHtml,
  updateProjectOverrides,
  getAvailableRoles,
  getSkillGaps,
} from "@/lib/api/projects";
import {
  detectLanguageMetric,
  normalizeLanguageStats,
  type NormalizedLanguageStat,
  type LanguageMetric,
} from "@/lib/language-stats";
import type {
  ProjectDetail,
  ProjectScanData,
  ProjectSkillCategoryItem,
  SkillEvidenceItem,
  SkillAdoptionEntry,
  SkillProgressPeriod,
  SkillProgressSummary,
  RoleProfile,
  SkillGapAnalysis,
} from "@/types/project";
import {
  MediaAnalysisTab,
} from "@/components/project/media-analysis-tab";
import { resolveMediaAnalysis } from "@/lib/project-media-analysis";
import {
  projectPageSelectors,
  useProjectPageStore,
  type MainTabValue,
  type ToolsTabValue,
} from "@/lib/stores/project-page-store";
import {
  LayoutDashboard,
  Award,
  BookOpen,
  Wrench,
  BarChart3,
  Code2,
  Users,
  FileText,
  Film,
  FileImage,
  GitBranch,
  Copy,
  Search,
  FileEdit,
  FileJson,
  FileCode2,
  Printer,
  Loader2,
  Check,
  AlertCircle,
  Download,
  Info,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { FileTreeView } from "@/components/project/file-tree-view";
import { SearchFilterTab } from "@/components/project/search-filter-tab";
import type { FileEntry } from "@/lib/file-tree";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

// Main section tabs (4 sections)
const mainTabs = [
  { value: "overview", label: "Overview & Analysis", icon: LayoutDashboard },
  { value: "skills", label: "Skills & Progress", icon: Award },
  { value: "content", label: "Content Analysis", icon: BookOpen },
  { value: "tools", label: "Tools & Export", icon: Wrench },
] as const;

// Sub-tabs for Overview & Analysis section
const overviewSubTabs = [
  { value: "overview-main", label: "Overview", icon: LayoutDashboard },
  { value: "languages", label: "Languages", icon: BarChart3 },
] as const;

// Sub-tabs for Skills & Progress section
const skillsSubTabs = [
  { value: "skills-main", label: "Skills", icon: Award },
  { value: "progress", label: "Progress", icon: LayoutDashboard },
  { value: "contributions", label: "Contributions", icon: Users },
] as const;

// Sub-tabs for Content Analysis section
const contentSubTabs = [
  { value: "documents", label: "Documents", icon: FileText },
  { value: "media", label: "Media", icon: Film },
  { value: "pdfs", label: "PDFs", icon: FileImage },
  {value:"code-analysis", label: "Code Analysis", icon: FileCode2}
] as const;

const toolsSubTabs = [
  { value: "tools-main", label: "Overview", icon: Wrench },
  { value: "file-browser", label: "File Browser", icon: FileText },
  { value: "search-filter", label: "Search & Filter Files", icon: Search },
  { value: "git-analysis", label: "Git Analysis", icon: GitBranch },
  { value: "duplicate-finder", label: "Duplicate Finder", icon: Copy },
] as const;

const LANGUAGE_COLORS = [
  "bg-gray-900",
  "bg-blue-600",
  "bg-emerald-600",
  "bg-amber-500",
  "bg-indigo-600",
  "bg-rose-600",
  "bg-teal-600",
  "bg-slate-500",
  "bg-orange-500",
  "bg-purple-600",
] as const;

function PlaceholderContent({ label }: { label: string }) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardContent className="p-12 text-center">
        <p className="text-gray-500 text-sm">
          {label} — This section will be available soon.
        </p>
      </CardContent>
    </Card>
  );
}

export default function ProjectPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const projectIdParam = searchParams.get("projectId");

  const activeMainTab = useProjectPageStore(projectPageSelectors.activeMainTab);
  const activeToolsTab = useProjectPageStore(projectPageSelectors.activeToolsTab);
  const projectId = useProjectPageStore(projectPageSelectors.projectId);
  const project = useProjectPageStore(projectPageSelectors.project);
  const projectError = useProjectPageStore(projectPageSelectors.projectError);
  const projectLoading = useProjectPageStore(projectPageSelectors.projectLoading);
  const hasProject = useProjectPageStore(projectPageSelectors.hasProject);
  const setActiveMainTab = useProjectPageStore(projectPageSelectors.setActiveMainTab);
  const setActiveToolsTab = useProjectPageStore(projectPageSelectors.setActiveToolsTab);
  const setProjectId = useProjectPageStore(projectPageSelectors.setProjectId);
  const setProject = useProjectPageStore(projectPageSelectors.setProject);
  const setProjectError = useProjectPageStore(projectPageSelectors.setProjectError);
  const setProjectLoading = useProjectPageStore(projectPageSelectors.setProjectLoading);
  const setRetryLoadProject = useProjectPageStore(
    projectPageSelectors.setRetryLoadProject
  );

  const isMountedRef = useRef(true);

  // Export HTML state
  const [htmlExportStatus, setHtmlExportStatus] = useState<"idle" | "exporting" | "success" | "error">("idle");
  const [htmlExportError, setHtmlExportError] = useState<string | null>(null);
  // Export JSON state
  const [exportStatus, setExportStatus] = useState<"idle" | "exporting" | "success" | "error">("idle");
  const [exportError, setExportError] = useState<string | null>(null);

  // Skills / progression state (from main)
  const [skillsTimeline, setSkillsTimeline] = useState<SkillProgressPeriod[]>(
    []
  );
  const [skillsSummary, setSkillsSummary] =
    useState<SkillProgressSummary | null>(null);
  const [skillsNote, setSkillsNote] = useState<string | null>(null);
  const [skillsLoading, setSkillsLoading] = useState(false);
  const [summaryLoading, setSummaryLoading] = useState(false);

  // Highlighted skills state
  const [highlightedSkills, setHighlightedSkills] = useState<string[]>([]);
  const [isSavingHighlights, setIsSavingHighlights] = useState(false);
  const [highlightSaveStatus, setHighlightSaveStatus] = useState<"idle" | "success" | "error">("idle");

  // Skills search, filter, and evidence expansion state
  const [skillsSearchQuery, setSkillsSearchQuery] = useState("");
  const [skillsCategoryFilter, setSkillsCategoryFilter] = useState<string>("all");
  const [expandedSkill, setExpandedSkill] = useState<string | null>(null);

  // Gap analysis state
  const [gapRoles, setGapRoles] = useState<RoleProfile[]>([]);
  const [selectedGapRole, setSelectedGapRole] = useState<string>("");
  const [gapResult, setGapResult] = useState<SkillGapAnalysis | null>(null);
  const [gapLoading, setGapLoading] = useState(false);
  const [gapError, setGapError] = useState<string | null>(null);

  // Keep local projectId in sync with URL
  useEffect(() => {
    setProjectId(projectIdParam);
  }, [projectIdParam, setProjectId]);

  const loadProject = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      if (isMountedRef.current) {
        setProjectError("Not authenticated. Please log in through Settings.");
        setProjectLoading(false);
      }
      return;
    }

    try {
      setProjectError(null);
      setProjectLoading(true);

      // If projectId in URL, load it. Otherwise load most recent.
      if (projectIdParam) {
        const details = await getProjectById(token, projectIdParam);
        if (isMountedRef.current) setProject(details);
        return;
      }

      const response = await getProjects(token);
      const mostRecent = response.projects?.[0];
      if (!mostRecent) {
        if (isMountedRef.current) setProject(null);
        return;
      }
      const details = await getProjectById(token, mostRecent.id);
      if (isMountedRef.current) setProject(details);
    } catch (err) {
      if (isMountedRef.current) {
        const message =
          err instanceof Error ? err.message : "Failed to load project";
        setProjectError(message);
      }
    } finally {
      if (isMountedRef.current) setProjectLoading(false);
    }
  }, [projectIdParam, setProject, setProjectError, setProjectLoading]);

  useEffect(() => {
    setRetryLoadProject(loadProject);
    return () => {
      setRetryLoadProject(null);
    };
  }, [loadProject, setRetryLoadProject]);

  useEffect(() => {
    isMountedRef.current = true;
    loadProject();
    return () => {
      isMountedRef.current = false;
    };
  }, [loadProject]);

  // Load highlighted skills from project data
  useEffect(() => {
    if (project?.user_overrides?.highlighted_skills) {
      setHighlightedSkills(project.user_overrides.highlighted_skills);
    } else {
      setHighlightedSkills([]);
    }
  }, [project]);

  // Save highlighted skills to backend
  const saveHighlightedSkills = async (skills: string[]) => {
    const token = getStoredToken();
    if (!token || !project?.id) return;

    try {
      setIsSavingHighlights(true);
      setHighlightSaveStatus("idle");
      
      await updateProjectOverrides(token, project.id, {
        highlighted_skills: skills,
      });
      
      setHighlightSaveStatus("success");
      
      // Reload project to get updated data
      await loadProject();
      
      // Clear success message after 2 seconds
      setTimeout(() => {
        setHighlightSaveStatus("idle");
      }, 2000);
    } catch (err) {
      console.error("Failed to save highlighted skills:", err);
      setHighlightSaveStatus("error");
      setTimeout(() => {
        setHighlightSaveStatus("idle");
      }, 3000);
    } finally {
      setIsSavingHighlights(false);
    }
  };

  // Toggle skill highlight
  const toggleSkillHighlight = (skillName: string) => {
    setHighlightedSkills((prev) => {
      const newHighlights = prev.includes(skillName)
        ? prev.filter((s) => s !== skillName)
        : [...prev, skillName];
      return newHighlights;
    });
  };

  // Load available role profiles when skills tab is active
  useEffect(() => {
    if (activeMainTab !== "skills" || gapRoles.length > 0) return;
    const token = getStoredToken();
    if (!token) return;
    getAvailableRoles(token)
      .then((roles) => { if (isMountedRef.current) setGapRoles(roles); })
      .catch(() => { /* roles are optional, ignore errors */ });
  }, [activeMainTab, gapRoles.length]);

  // Run gap analysis when role is selected
  const runGapAnalysis = async (role: string) => {
    setSelectedGapRole(role);
    setGapResult(null);
    setGapError(null);
    if (!role) return;

    const token = getStoredToken();
    const pid = project?.id;
    if (!token || !pid) return;

    try {
      setGapLoading(true);
      const result = await getSkillGaps(token, pid, role);
      if (isMountedRef.current) setGapResult(result);
    } catch (err) {
      if (isMountedRef.current) {
        setGapError(err instanceof Error ? err.message : "Gap analysis failed");
      }
    } finally {
      if (isMountedRef.current) setGapLoading(false);
    }
  };

  // Fetch skills timeline/summary when we have a projectId
  useEffect(() => {
    const effectiveProjectId = projectId ?? project?.id ?? null;
    if (!effectiveProjectId) return;

    const token = getStoredToken();
    if (!token) return;

    let cancelled = false;
    setSkillsLoading(true);
    setSkillsNote(null);

    getProjectSkillTimeline(token, effectiveProjectId)
      .then((data) => {
        if (cancelled) return;
        setSkillsTimeline(data.timeline || []);
        setSkillsSummary(data.summary ?? null);
        setSkillsNote(data.note ?? null);
      })
      .catch((err) => {
        if (cancelled) return;
        setSkillsNote(
          err instanceof Error ? err.message : "Failed to load skills timeline."
        );
      })
      .finally(() => {
        if (!cancelled) setSkillsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [projectId, project?.id]);

  /** Build and trigger an HTML report download for the current project. */
  const handleExportHtml = useCallback(async () => {
    if (!project) {
      setHtmlExportError("No project loaded");
      setHtmlExportStatus("error");
      return;
    }

    const token = getStoredToken();
    if (!token) {
      setHtmlExportError("Not authenticated");
      setHtmlExportStatus("error");
      return;
    }

    try {
      setHtmlExportStatus("exporting");
      setHtmlExportError(null);

      const htmlContent = await exportProjectHtml(token, project.id);

      const blob = new Blob([htmlContent], { type: "text/html" });
      const url = URL.createObjectURL(blob);

      // Sanitise project name for filename
      const safeName = (project.project_name || "project")
        .replace(/[^a-zA-Z0-9_-]/g, "_")
        .replace(/_+/g, "_")
        .toLowerCase();
      const ts = new Date().toISOString().slice(0, 10);
      const filename = `${safeName}_report_${ts}.html`;

      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setHtmlExportStatus("success");
      setTimeout(() => setHtmlExportStatus("idle"), 2500);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "HTML export failed";
      setHtmlExportError(msg);
      setHtmlExportStatus("error");
      setTimeout(() => {
        setHtmlExportStatus("idle");
        setHtmlExportError(null);
      }, 4000);
    }
  }, [project]);

  /** Build and trigger a JSON report download for the current project. */
  const handleExportJson = useCallback(() => {
    if (!project) {
      setExportError("No project loaded");
      setExportStatus("error");
      return;
    }

    try {
      setExportStatus("exporting");
      setExportError(null);

      // Build the export payload: project metadata + everything in scan_data.
      // scan_data keys vary depending on how the scan was created (upload vs
      // full TUI scan), so we spread all of scan_data rather than cherry-picking
      // keys that might not exist yet.
      const sd = project.scan_data ?? {};
      const payload: Record<string, unknown> = {
        export_format: "json",
        exported_at: new Date().toISOString(),
        project: {
          id: project.id,
          name: project.project_name,
          path: project.project_path,
          scan_timestamp: project.scan_timestamp ?? null,
          total_files: project.total_files,
          total_lines: project.total_lines,
          languages: project.languages ?? [],
          contribution_score: project.contribution_score ?? null,
          primary_contributor: project.primary_contributor ?? null,
          role: project.role ?? null,
        },
        // Spread every key from scan_data so nothing is silently dropped
        ...sd,
      };

      const jsonStr = JSON.stringify(payload, null, 2);
      const blob = new Blob([jsonStr], { type: "application/json" });
      const url = URL.createObjectURL(blob);

      // Sanitise project name for filename
      const safeName = (project.project_name || "project")
        .replace(/[^a-zA-Z0-9_-]/g, "_")
        .replace(/_+/g, "_")
        .toLowerCase();
      const ts = new Date().toISOString().slice(0, 10);
      const filename = `${safeName}_report_${ts}.json`;

      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setExportStatus("success");
      // Reset back to idle after a brief period
      setTimeout(() => setExportStatus("idle"), 2500);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Export failed";
      setExportError(msg);
      setExportStatus("error");
      setTimeout(() => {
        setExportStatus("idle");
        setExportError(null);
      }, 4000);
    }
  }, [project]);

  const scanData =
    useProjectPageStore(projectPageSelectors.scanData) as ProjectScanData;
  const summary = scanData.summary ?? {};
  const skillsAnalysis = scanData.skills_analysis ?? {};
  const skillsByCategory = skillsAnalysis.skills_by_category ?? {};
  const totalSkills =
    typeof skillsAnalysis.total_skills === "number" ? skillsAnalysis.total_skills : 0;

  // Category labels from backend, with fallback
  const categoryLabels: Record<string, string> = (skillsAnalysis.category_labels as Record<string, string>) ?? {};
  const getCategoryLabel = (key: string) =>
    categoryLabels[key] || key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  // Full skills list from backend (with evidence)
  const fullSkillsList = Array.isArray((skillsAnalysis as any).skills) ? (skillsAnalysis as any).skills : [];

  // Get evidence for a skill by name
  const getSkillEvidence = (skillName: string): SkillEvidenceItem[] => {
    const found = fullSkillsList.find((s: any) => s.name === skillName);
    return Array.isArray(found?.evidence) ? found.evidence : [];
  };

  // Adoption timeline
  const skillAdoptionTimeline: SkillAdoptionEntry[] = Array.isArray((skillsAnalysis as any).skill_adoption_timeline)
    ? (skillsAnalysis as any).skill_adoption_timeline
    : [];

  // Filter skills by search query and category filter
  const filteredSkillsByCategory = useMemo(() => {
    const result: Record<string, Array<ProjectSkillCategoryItem>> = {};
    for (const [category, skills] of Object.entries(skillsByCategory)) {
      if (skillsCategoryFilter !== "all" && category !== skillsCategoryFilter) continue;
      const filtered = (skills as Array<ProjectSkillCategoryItem>).filter((skill) => {
        const name = typeof skill === "string" ? skill : skill.name ?? "";
        return name.toLowerCase().includes(skillsSearchQuery.toLowerCase());
      });
      if (filtered.length > 0) result[category] = filtered;
    }
    return result;
  }, [skillsByCategory, skillsSearchQuery, skillsCategoryFilter]);

  // Extract all available skill names
  const allAvailableSkills = useMemo(() => {
    const skills: string[] = [];
    Object.values(skillsByCategory).forEach((categorySkills) => {
      if (Array.isArray(categorySkills)) {
        categorySkills.forEach((skill: unknown) => {
          if (typeof skill === "string") {
            skills.push(skill);
          } else if (
            typeof skill === "object" &&
            skill !== null &&
            typeof (skill as { name?: unknown }).name === "string"
          ) {
            skills.push((skill as { name: string }).name);
          }
        });
      }
    });
    return skills.sort();
  }, [skillsByCategory]);

  const projectFiles: FileEntry[] = Array.isArray(scanData.files)
    ? scanData.files
        .map((file: unknown): FileEntry => {
          const scanFile =
            typeof file === "object" && file !== null
              ? (file as Record<string, unknown>)
              : {};
          const normalizedPath =
            typeof scanFile.path === "string"
              ? scanFile.path
              : typeof scanFile.file_path === "string"
                ? scanFile.file_path
                : "";

          return {
            path: normalizedPath,
            size_bytes:
              typeof scanFile.size_bytes === "number" && Number.isFinite(scanFile.size_bytes)
                ? scanFile.size_bytes
                : 0,
            mime_type:
              typeof scanFile.mime_type === "string" && scanFile.mime_type.length > 0
                ? scanFile.mime_type
                : "application/octet-stream",
            created_at:
              typeof scanFile.created_at === "string" || scanFile.created_at === null
                ? scanFile.created_at
                : undefined,
            modified_at:
              typeof scanFile.modified_at === "string" || scanFile.modified_at === null
                ? scanFile.modified_at
                : undefined,
            file_hash:
              typeof scanFile.file_hash === "string" || scanFile.file_hash === null
                ? scanFile.file_hash
                : undefined,
          };
        })
        .filter((file: FileEntry) => file.path.length > 0)
    : [];

  const projectName = project?.project_name ?? "";
  const projectPath = project?.project_path ?? "";
  const scanTimestamp = project?.scan_timestamp ?? "Not available";

  const scanDurationRaw = Number(
    summary.scan_duration_seconds ?? scanData.scan_duration_seconds ?? scanData.scan_duration
  );
  const scanDurationLabel = Number.isFinite(scanDurationRaw)
    ? formatDurationSeconds(scanDurationRaw)
    : "Not available";

  const filesProcessed =
    typeof summary.total_files === "number" ? summary.total_files : project?.total_files ?? 0;
  const totalSizeBytes =
    typeof summary.bytes_processed === "number" ? summary.bytes_processed : undefined;
  const issuesFound =
    typeof summary.issues_found === "number"
      ? summary.issues_found
      : typeof summary.issue_count === "number"
        ? summary.issue_count
        : 0;
  const totalLines =
    typeof summary.total_lines === "number" ? summary.total_lines : project?.total_lines ?? 0;

  const filesProcessedLabel = formatCount(filesProcessed);
  const issuesFoundLabel = formatCount(issuesFound);
  const totalLinesLabel = formatCount(totalLines);
  const totalSizeLabel =
    typeof totalSizeBytes === "number" && Number.isFinite(totalSizeBytes)
      ? formatBytes(totalSizeBytes)
      : "Not available";

  const languageMetric = useMemo<LanguageMetric>(
    () => detectLanguageMetric(scanData),
    [scanData]
  );

  const languageBreakdown = useMemo(() => {
    const totalOverride = Number(
      summary.bytes_processed ??
        scanData.total_size_bytes ??
        scanData.total_bytes ??
        scanData.bytes_processed
    );
    return normalizeLanguageStats(
      scanData,
      languageMetric === "bytes" && Number.isFinite(totalOverride)
        ? totalOverride
        : undefined
    );
  }, [
    scanData,
    summary.bytes_processed,
    scanData.total_size_bytes,
    scanData.total_bytes,
    scanData.bytes_processed,
    languageMetric,
  ]);

  const topLanguages: Array<{ name: string; percentage: number }> = languageBreakdown
    .slice(0, 5)
    .map((lang) => ({ name: lang.name, percentage: lang.percent }));

  const languageTotalValue = useMemo(() => {
    const computed = languageBreakdown.reduce((sum, item) => sum + item.bytes, 0);
    if (languageMetric !== "bytes") return computed;
    const totalOverride = Number(
      summary.bytes_processed ??
        scanData.total_size_bytes ??
        scanData.total_bytes ??
        scanData.bytes_processed
    );
    if (Number.isFinite(totalOverride) && totalOverride > 0) {
      return Math.max(totalOverride, computed);
    }
    return computed;
  }, [
    languageBreakdown,
    summary.bytes_processed,
    scanData.total_size_bytes,
    scanData.total_bytes,
    scanData.bytes_processed,
    languageMetric,
  ]);

  const languageValuesTotal = useMemo(
    () => languageBreakdown.reduce((sum, item) => sum + item.bytes, 0),
    [languageBreakdown]
  );

  const languageTotalPercent =
    languageTotalValue > 0
      ? Number(((languageValuesTotal / languageTotalValue) * 100).toFixed(1))
      : 0;

  const languageMetricLabel =
    languageMetric === "lines"
      ? "Lines"
      : languageMetric === "files"
      ? "Files"
      : "Size";

  const languageTotalLabel =
    languageMetric === "lines"
      ? "Total lines"
      : languageMetric === "files"
      ? "Total files"
      : "Total size";

  const formatLanguageValue = (value: number) =>
    languageMetric === "bytes" ? formatBytes(value) : formatCount(value);

  const languageChartData: NormalizedLanguageStat[] = useMemo(() => {
    if (languageBreakdown.length === 0) return [];
    const maxSegments = 8;
    const primary = languageBreakdown.slice(0, maxSegments);
    const remainder = languageBreakdown.slice(maxSegments);
    if (remainder.length === 0) return primary;

    const otherBytes = remainder.reduce((sum, item) => sum + item.bytes, 0);
    const percent =
      languageTotalValue > 0
        ? Number(((otherBytes / languageTotalValue) * 100).toFixed(1))
        : 0;
    return [...primary, { name: "Other", bytes: otherBytes, percent }];
  }, [languageBreakdown, languageTotalValue]);

  useEffect(() => {
    if (projectError) {
      console.error("Language breakdown failed to load.", projectError);
    }
  }, [projectError]);

  // Backend now returns git_analysis as a flat array: [ { path, commit_count, ... }, ... ]
  // Legacy format used git_analysis.repositories; support both for backwards compat.
  const gitAnalysisLegacy =
    typeof scanData.git_analysis === "object" &&
    scanData.git_analysis !== null &&
    !Array.isArray(scanData.git_analysis)
      ? (scanData.git_analysis as { repositories?: unknown[] })
    : null;
  const gitRepos = Array.isArray(scanData.git_analysis)
    ? scanData.git_analysis.length
    : Array.isArray(gitAnalysisLegacy?.repositories)
      ? gitAnalysisLegacy.repositories.length
      : 0;

  const documentAnalysis = scanData.document_analysis;
  const documentAnalysisRecord =
    typeof documentAnalysis === "object" &&
    documentAnalysis !== null &&
    !Array.isArray(documentAnalysis)
      ? (documentAnalysis as { documents?: unknown[]; items?: unknown[] })
    : null;
  const otherDocs = Array.isArray(documentAnalysis)
    ? documentAnalysis.length
    : Array.isArray(documentAnalysisRecord?.documents)
      ? documentAnalysisRecord.documents.length
      : Array.isArray(documentAnalysisRecord?.items)
        ? documentAnalysisRecord.items.length
        : 0;

  // Media analysis (from feature/media-analysis)
  const mediaAnalysis = useMemo(() => resolveMediaAnalysis(scanData), [scanData]);

  const mediaFiles = Array.isArray(scanData.media_analysis)
    ? scanData.media_analysis.length
    : 0;

  const pdfDocs = Array.isArray(scanData.pdf_analysis)
    ? scanData.pdf_analysis.length
    : 0;

  const topSkills = useMemo(() => {
    const counts = new Map<string, number>();
    skillsTimeline.forEach((period) => {
      period.top_skills.forEach((skill) => {
        counts.set(skill, (counts.get(skill) ?? 0) + 1);
      });
    });
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6);
  }, [skillsTimeline]);

  const gitAnalysisRepos = useMemo(() => {
    const raw = scanData.git_analysis;
    if (!Array.isArray(raw)) return [];
    return raw.filter(
      (entry): entry is Record<string, unknown> =>
        typeof entry === "object" && entry !== null && !Array.isArray(entry)
    );
  }, [scanData.git_analysis]);

  const gitRepoTotal = gitAnalysisRepos.length;
  const gitCommitTotal = gitAnalysisRepos.reduce((sum, repo) => {
    const commits = repo.commit_count;
    if (typeof commits === "number" && Number.isFinite(commits)) {
      return sum + commits;
    }
    return sum;
  }, 0);

  const duplicateOverview = useMemo(() => {
    const report = scanData.duplicate_report;
    if (!report || typeof report !== "object" || Array.isArray(report)) {
      return null;
    }

    const record = report as Record<string, unknown>;
    const groups = Array.isArray(record.duplicate_groups)
      ? record.duplicate_groups
      : [];

    const totalGroupsRaw = Number(record.total_duplicates);
    const totalWastedBytesRaw = Number(record.total_wasted_bytes);

    const totalGroups =
      Number.isFinite(totalGroupsRaw) && totalGroupsRaw >= 0
        ? totalGroupsRaw
        : groups.length;

    const totalWastedBytes =
      Number.isFinite(totalWastedBytesRaw) && totalWastedBytesRaw >= 0
        ? totalWastedBytesRaw
        : 0;

    return {
      totalGroups,
      totalWastedBytes,
    };
  }, [scanData.duplicate_report]);

  const openToolsTab = useCallback((nextTab: ToolsTabValue) => {
    setActiveMainTab("tools");
    setActiveToolsTab(nextTab);
  }, []);

  const handleGenerateSummary = async () => {
    const effectiveProjectId = projectId ?? project?.id ?? null;
    if (!effectiveProjectId) return;

    const token = getStoredToken();
    if (!token) {
      setSkillsNote("Not authenticated. Please log in through Settings.");
      return;
    }

    setSummaryLoading(true);
    try {
      const response = await generateProjectSkillSummary(token, effectiveProjectId);
      setSkillsSummary(response.summary ?? null);
      setSkillsNote(response.note ?? null);
    } catch (err) {
      setSkillsNote(err instanceof Error ? err.message : "Failed to generate summary.");
    } finally {
      setSummaryLoading(false);
    }
  };

  return (
    <div className="p-8">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 mb-6">
        <button
          onClick={() => router.back()}
          className="text-sm text-gray-600 hover:text-gray-900 mb-2 inline-block"
        >
          ← Back
        </button>

        <h1 className="text-4xl font-bold text-gray-900 tracking-tight">
          {hasProject ? `Project: ${projectName}` : "Project"}
        </h1>

        <p className="text-gray-500 mt-1 text-sm">Scanned project analysis and reports</p>

        {projectLoading && (
          <p className="text-xs text-gray-400 mt-2">Loading project data…</p>
        )}
        {projectError && <p className="text-xs text-red-600 mt-2">{projectError}</p>}
      </div>

      {!projectLoading && !projectError && !hasProject && (
        <Card className="bg-white border border-gray-200">
          <CardContent className="p-8 text-center space-y-3">
            <p className="text-lg font-semibold text-gray-900">No project selected</p>
            <p className="text-sm text-gray-600">
              Select a project from your scanned results to view its analysis.
            </p>
            <Link href="/projects" className="text-sm text-gray-900 underline">
              Go to projects
            </Link>
          </CardContent>
        </Card>
      )}

      {projectError && !hasProject && (
        <Card className="bg-white border border-red-200">
          <CardContent className="p-8 text-center space-y-2">
            <p className="text-sm font-semibold text-red-700">Unable to load project data</p>
            <p className="text-sm text-gray-600">Please return to Settings and verify your session.</p>
          </CardContent>
        </Card>
      )}

      {hasProject && (
        <Tabs
          key={activeMainTab}
          defaultValue={activeMainTab}
          onValueChange={(value) => setActiveMainTab(value as MainTabValue)}
        >
          {/* Main 4 tabs */}
          <TabsList className="flex justify-start gap-2 h-auto bg-gray-100 rounded-lg p-2 mb-6">
            {mainTabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <TabsTrigger
                  key={tab.value}
                  value={tab.value}
                  className="text-sm px-5 py-2.5 font-medium"
                >
                  <Icon size={18} className="mr-2" />
                  {tab.label}
                </TabsTrigger>
              );
            })}
          </TabsList>

          {/* ============================================
              TAB 1: OVERVIEW & ANALYSIS
          ============================================ */}
          <TabsContent value="overview">
            <Tabs defaultValue="overview-main" className="space-y-6">
              <TabsList className="flex justify-start gap-1 h-auto bg-transparent p-0 border-b border-gray-200 rounded-none">
                {overviewSubTabs.map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <TabsTrigger
                      key={tab.value}
                      value={tab.value}
                      className="text-xs px-4 py-2 rounded-t-lg rounded-b-none border-b-2 border-transparent data-[state=active]:border-gray-900 data-[state=active]:bg-white"
                    >
                      <Icon size={14} className="mr-1.5" />
                      {tab.label}
                    </TabsTrigger>
                  );
                })}
              </TabsList>

              {/* Overview Main - Project Info & Stats */}
              <TabsContent value="overview-main" className="space-y-6">
                <Card className="bg-white border border-gray-200">
                  <CardHeader className="border-b border-gray-200">
                    <CardTitle className="text-xl font-bold text-gray-900">
                      Project Information
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Project Name
                        </p>
                        <p className="text-sm font-semibold text-gray-900 mt-1">
                          {projectName}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Path
                        </p>
                        <p className="text-sm font-mono text-gray-900 mt-1">
                          {projectPath}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Scan Timestamp
                        </p>
                        <p className="text-sm text-gray-900 mt-1">{scanTimestamp}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Scan Duration
                        </p>
                        <p className="text-sm text-gray-900 mt-1">{scanDurationLabel}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-white border border-gray-200">
                  <CardHeader className="border-b border-gray-200">
                    <CardTitle className="text-xl font-bold text-gray-900">
                      Summary Statistics
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                      <div className="bg-gray-50 rounded-lg p-4 text-center">
                        <p className="text-2xl font-bold text-gray-900">
                          {filesProcessedLabel}
                        </p>
                        <p className="text-xs text-gray-500 mt-1 inline-flex items-center gap-1">
                          Files Processed
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button
                                  type="button"
                                  aria-label="Files processed info"
                                  className="inline-flex items-center"
                                >
                                  <Info size={12} className="text-gray-400 cursor-help" />
                                </button>
                              </TooltipTrigger>
                              <TooltipContent side="top" className="max-w-xs text-xs">
                                Only relevant files are counted. Files in excluded
                                directories (node_modules, .git, __pycache__, etc.)
                                and unsupported file types are filtered out during
                                scanning.
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </p>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-4 text-center">
                        <p className="text-2xl font-bold text-gray-900">
                          {totalSizeLabel}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">Total Size</p>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-4 text-center">
                        <p className="text-2xl font-bold text-gray-900">
                          {issuesFoundLabel}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">Issues Found</p>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-4 text-center">
                        <p className="text-2xl font-bold text-gray-900">
                          {totalLinesLabel}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">Lines of Code</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <Card className="bg-white border border-gray-200">
                    <CardHeader className="border-b border-gray-200">
                      <CardTitle className="text-base font-bold text-gray-900 flex items-center gap-2">
                        <GitBranch size={16} />
                        Git Repositories
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-6">
                      <p className="text-3xl font-bold text-gray-900">{gitRepos}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {gitRepos === 1 ? "Repository" : "Repositories"} detected
                      </p>
                      {scanData.contribution_metrics?.total_commits != null && (
                        <div className="mt-3 pt-3 border-t border-gray-100 text-sm text-gray-600">
                          <span className="font-medium">{scanData.contribution_metrics.total_commits}</span> commits
                          {scanData.contribution_metrics.total_contributors != null && (
                            <span> · <span className="font-medium">{scanData.contribution_metrics.total_contributors}</span> {scanData.contribution_metrics.total_contributors === 1 ? "contributor" : "contributors"}</span>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  <Card className="bg-white border border-gray-200">
                    <CardHeader className="border-b border-gray-200">
                      <CardTitle className="text-base font-bold text-gray-900">
                        Media Files
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-6">
                      <p className="text-3xl font-bold text-gray-900">{mediaFiles}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        Images, videos, and audio
                      </p>
                    </CardContent>
                  </Card>

                  <Card className="bg-white border border-gray-200">
                    <CardHeader className="border-b border-gray-200">
                      <CardTitle className="text-base font-bold text-gray-900">
                        Documents
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-6">
                      <div className="flex gap-6">
                        <div>
                          <p className="text-3xl font-bold text-gray-900">{pdfDocs}</p>
                          <p className="text-xs text-gray-500 mt-1">PDF files</p>
                        </div>
                        <div>
                          <p className="text-3xl font-bold text-gray-900">{otherDocs}</p>
                          <p className="text-xs text-gray-500 mt-1">Other docs</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>

              {/* Languages Breakdown */}
              <TabsContent value="languages">
                <Card className="bg-white border border-gray-200">
                  <CardHeader className="border-b border-gray-200">
                    <CardTitle className="text-xl font-bold text-gray-900">
                      Language Breakdown
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {topLanguages.length === 0 ? (
                      <p className="text-sm text-gray-500">
                        No language data available for this project.
                      </p>
                    ) : (
                      <div className="space-y-4">
                        {topLanguages.map((lang) => (
                          <div key={lang.name} className="space-y-1">
                            <div className="flex justify-between text-sm">
                              <span className="font-medium text-gray-900">{lang.name}</span>
                              <span className="text-gray-500">{lang.percentage}%</span>
                            </div>
                            <div className="w-full bg-gray-100 rounded-full h-2">
                              <div
                                className="bg-gray-900 h-2 rounded-full transition-all"
                                style={{ width: `${lang.percentage}%` }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>


            </Tabs>
          </TabsContent>

          {/* ============================================
              TAB 2: SKILLS & PROGRESS
          ============================================ */}
          <TabsContent value="skills">
            <Tabs defaultValue="skills-main" className="space-y-6">
              <TabsList className="flex justify-start gap-1 h-auto bg-transparent p-0 border-b border-gray-200 rounded-none">
                {skillsSubTabs.map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <TabsTrigger
                      key={tab.value}
                      value={tab.value}
                      className="text-xs px-4 py-2 rounded-t-lg rounded-b-none border-b-2 border-transparent data-[state=active]:border-gray-900 data-[state=active]:bg-white"
                    >
                      <Icon size={14} className="mr-1.5" />
                      {tab.label}
                    </TabsTrigger>
                  );
                })}
              </TabsList>

              {/* Skills Main */}
              <TabsContent value="skills-main" className="space-y-6">
                {/* Highlighted Skills Section */}
                <Card className="bg-white border border-gray-200">
                  <CardHeader className="border-b border-gray-200">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-xl font-bold text-gray-900">
                        Highlighted Skills
                      </CardTitle>
                      {highlightSaveStatus === "success" && (
                        <span className="flex items-center gap-1.5 text-sm text-green-600 font-medium">
                          <Check size={16} />
                          Saved
                        </span>
                      )}
                      {highlightSaveStatus === "error" && (
                        <span className="flex items-center gap-1.5 text-sm text-red-600 font-medium">
                          <AlertCircle size={16} />
                          Save failed
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 mt-1">
                      Select skills you want to emphasize on your resume or portfolio
                    </p>
                  </CardHeader>
                  <CardContent className="p-6">
                    {highlightedSkills.length === 0 ? (
                      <p className="text-sm text-gray-500">
                        No skills highlighted yet. Select skills below to highlight them.
                      </p>
                    ) : (
                      <div className="flex flex-wrap gap-2">
                        {highlightedSkills.map((skill) => (
                          <span
                            key={`highlighted-${skill}`}
                            className="px-3 py-1.5 rounded-full bg-blue-600 text-white text-sm font-medium flex items-center gap-2"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* All Skills with Selection */}
                <Card className="bg-white border border-gray-200">
                  <CardHeader className="border-b border-gray-200">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-xl font-bold text-gray-900">
                        Select Skills to Highlight
                      </CardTitle>
                      <Button
                        onClick={() => saveHighlightedSkills(highlightedSkills)}
                        disabled={isSavingHighlights}
                        size="sm"
                        className="bg-gray-900 hover:bg-gray-800"
                      >
                        {isSavingHighlights ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Saving...
                          </>
                        ) : (
                          <>
                            <Check className="mr-2 h-4 w-4" />
                            Save Highlights
                          </>
                        )}
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="p-6 space-y-4">
                    {skillsAnalysis.success === false && (
                      <p className="text-sm text-gray-500">
                        Skills analysis did not complete for this scan.
                      </p>
                    )}

                    {skillsAnalysis.success !== false &&
                      Object.keys(skillsByCategory).length === 0 && (
                        <p className="text-sm text-gray-500">
                          No skills analysis available yet. Run a scan with skills extraction enabled.
                        </p>
                      )}

                    {Object.keys(skillsByCategory).length > 0 && (
                      <div className="space-y-6">
                        <div className="flex flex-wrap gap-3">
                          <span className="px-3 py-1 rounded-full bg-gray-900 text-white text-xs font-semibold">
                            Total skills · {totalSkills}
                          </span>
                          <span className="px-3 py-1 rounded-full bg-blue-100 text-blue-700 text-xs font-semibold">
                            Highlighted · {highlightedSkills.length}
                          </span>
                          <span className="px-3 py-1 rounded-full bg-gray-100 text-gray-700 text-xs font-semibold">
                            Categories · {Object.keys(skillsByCategory).length}
                          </span>
                        </div>

                        {/* Category average proficiency bars */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                          {Object.entries(skillsByCategory).map(([category, skills]) => {
                            const items = skills as Array<ProjectSkillCategoryItem>;
                            const scores = items
                              .map((s) => (typeof s === "object" ? s.proficiency_score ?? 0 : 0))
                              .filter((v) => v > 0);
                            const avg = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
                            return (
                              <div key={`avg-${category}`} className="bg-gray-50 rounded-lg p-3">
                                <p className="text-xs font-medium text-gray-500 truncate">{getCategoryLabel(category)}</p>
                                <div className="mt-1.5 w-full bg-gray-200 rounded-full h-2">
                                  <div
                                    className="bg-gray-900 h-2 rounded-full transition-all"
                                    style={{ width: `${Math.round(avg * 100)}%` }}
                                  />
                                </div>
                                <p className="text-xs text-gray-400 mt-1">{Math.round(avg * 100)}%</p>
                              </div>
                            );
                          })}
                        </div>

                        {/* Search and filter */}
                        <div className="flex flex-col sm:flex-row gap-3">
                          <Input
                            placeholder="Search skills..."
                            value={skillsSearchQuery}
                            onChange={(e) => setSkillsSearchQuery(e.target.value)}
                            className="sm:max-w-xs text-sm"
                          />
                          <select
                            value={skillsCategoryFilter}
                            onChange={(e) => setSkillsCategoryFilter(e.target.value)}
                            className="text-sm border border-gray-200 rounded-md px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-gray-900"
                          >
                            <option value="all">All categories</option>
                            {Object.keys(skillsByCategory).map((cat) => (
                              <option key={cat} value={cat}>{getCategoryLabel(cat)}</option>
                            ))}
                          </select>
                        </div>

                        {Object.entries(filteredSkillsByCategory).map(([category, skills]) => (
                          <div key={category} className="border border-gray-200 rounded-lg p-4">
                            <p className="text-sm font-semibold text-gray-700 mb-3">
                              {getCategoryLabel(category)}
                            </p>
                            <div className="space-y-2">
                              {(skills as Array<ProjectSkillCategoryItem>).map(
                                (skill) => {
                                  const skillName = typeof skill === "string" ? skill : skill.name ?? "";
                                  const isHighlighted = highlightedSkills.includes(skillName);
                                  const description = typeof skill === "object" ? skill.description : undefined;
                                  const profScore = typeof skill === "object" ? skill.proficiency_score ?? 0 : 0;
                                  const evidence = getSkillEvidence(skillName);
                                  const isExpanded = expandedSkill === skillName;

                                  return (
                                    <div
                                      key={`${category}-${skillName}`}
                                      className={`rounded-md transition-colors ${
                                        isHighlighted ? "bg-blue-50 border border-blue-200" : "border border-transparent hover:bg-gray-50"
                                      }`}
                                    >
                                      <div className="flex items-center gap-3 p-2">
                                        <Checkbox
                                          id={`skill-${category}-${skillName}`}
                                          checked={isHighlighted}
                                          onChange={() => toggleSkillHighlight(skillName)}
                                          className="border-gray-300"
                                        />
                                        <button
                                          type="button"
                                          onClick={() => setExpandedSkill(isExpanded ? null : skillName)}
                                          className="flex-1 text-left"
                                        >
                                          <span className="text-sm font-medium text-gray-900">
                                            {skillName}
                                          </span>
                                          {description && (
                                            <span className="block text-xs text-gray-500 mt-0.5">
                                              {description}
                                            </span>
                                          )}
                                        </button>
                                        <div className="flex items-center gap-2">
                                          {/* Proficiency bar */}
                                          {profScore > 0 && (
                                            <div className="flex items-center gap-1.5">
                                              <div className="w-16 bg-gray-200 rounded-full h-1.5">
                                                <div
                                                  className={`h-1.5 rounded-full ${
                                                    profScore >= 0.8 ? "bg-green-500" : profScore >= 0.6 ? "bg-blue-500" : profScore >= 0.4 ? "bg-amber-500" : "bg-gray-400"
                                                  }`}
                                                  style={{ width: `${Math.round(profScore * 100)}%` }}
                                                />
                                              </div>
                                              <span className="text-xs text-gray-400 w-8">{Math.round(profScore * 100)}%</span>
                                            </div>
                                          )}
                                          {evidence.length > 0 && (
                                            <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                                              {evidence.length}
                                            </span>
                                          )}
                                          {isHighlighted && (
                                            <Check size={16} className="text-blue-600" />
                                          )}
                                          {evidence.length > 0 && (
                                            isExpanded ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />
                                          )}
                                        </div>
                                      </div>
                                      {/* Evidence panel */}
                                      {isExpanded && evidence.length > 0 && (
                                        <div className="px-10 pb-3 space-y-1.5">
                                          {evidence.slice(0, 5).map((ev, idx) => (
                                            <div key={idx} className="text-xs text-gray-600 flex items-start gap-2">
                                              <span className="text-gray-300 mt-0.5">-</span>
                                              <div>
                                                <span>{ev.description || ev.type || "Evidence"}</span>
                                                {ev.file && (
                                                  <span className="ml-1 text-gray-400 font-mono">
                                                    {ev.file}{ev.line ? `:${ev.line}` : ""}
                                                  </span>
                                                )}
                                              </div>
                                            </div>
                                          ))}
                                          {evidence.length > 5 && (
                                            <p className="text-xs text-gray-400 italic">
                                              + {evidence.length - 5} more evidence items
                                            </p>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  );
                                }
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Skill Adoption Timeline */}
                {skillAdoptionTimeline.length > 0 && (
                  <Card className="bg-white border border-gray-200">
                    <CardHeader className="border-b border-gray-200">
                      <CardTitle className="text-xl font-bold text-gray-900">
                        Skill Adoption Timeline
                      </CardTitle>
                      <p className="text-sm text-gray-500 mt-1">
                        When each skill was first detected in the codebase
                      </p>
                    </CardHeader>
                    <CardContent className="p-6">
                      <div className="space-y-3">
                        {skillAdoptionTimeline.map((entry, idx) => (
                          <div
                            key={idx}
                            className="flex items-center gap-4 py-2 border-b border-gray-100 last:border-0"
                          >
                            <span className="text-xs font-mono text-gray-400 w-20 shrink-0">
                              {entry.first_used_period || "Unknown"}
                            </span>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-gray-900 truncate">
                                {entry.skill_name}
                              </p>
                              <p className="text-xs text-gray-500 truncate">
                                {getCategoryLabel(entry.category ?? "")}
                                {entry.file ? ` · ${entry.file}` : ""}
                              </p>
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                              <div className="w-12 bg-gray-200 rounded-full h-1.5">
                                <div
                                  className="bg-gray-900 h-1.5 rounded-full"
                                  style={{ width: `${Math.round((entry.current_proficiency ?? 0) * 100)}%` }}
                                />
                              </div>
                              <span className="text-xs text-gray-400">
                                {entry.total_usage ?? 0} uses
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Gap Analysis */}
                <Card className="bg-white border border-gray-200">
                  <CardHeader className="border-b border-gray-200">
                    <CardTitle className="text-xl font-bold text-gray-900">
                      Skill Gap Analysis
                    </CardTitle>
                    <p className="text-sm text-gray-500 mt-1">
                      Compare detected skills against a target role profile
                    </p>
                  </CardHeader>
                  <CardContent className="p-6 space-y-4">
                    <div className="flex items-center gap-3">
                      <select
                        className="border border-gray-300 rounded-md px-3 py-2 text-sm bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-400"
                        value={selectedGapRole}
                        onChange={(e) => runGapAnalysis(e.target.value)}
                      >
                        <option value="">Select a role...</option>
                        {gapRoles.map((r) => (
                          <option key={r.key} value={r.key}>
                            {r.label}
                          </option>
                        ))}
                      </select>
                      {gapLoading && (
                        <Loader2 size={16} className="animate-spin text-gray-400" />
                      )}
                    </div>

                    {gapError && (
                      <p className="text-sm text-red-600">{gapError}</p>
                    )}

                    {gapResult && (
                      <div className="space-y-4">
                        {/* Coverage bar */}
                        <div className="space-y-1">
                          <div className="flex justify-between text-sm">
                            <span className="font-medium text-gray-900">
                              Coverage for {gapResult.role_label}
                            </span>
                            <span className="text-gray-500">
                              {gapResult.coverage_percent}%
                            </span>
                          </div>
                          <div className="w-full bg-gray-100 rounded-full h-3">
                            <div
                              className={`h-3 rounded-full transition-all ${
                                gapResult.coverage_percent >= 75
                                  ? "bg-emerald-600"
                                  : gapResult.coverage_percent >= 40
                                    ? "bg-amber-500"
                                    : "bg-red-500"
                              }`}
                              style={{ width: `${gapResult.coverage_percent}%` }}
                            />
                          </div>
                        </div>

                        {([
                          { label: "Matched", items: gapResult.matched, bg: "bg-emerald-100", text: "text-emerald-800" },
                          { label: "Missing", items: gapResult.missing, bg: "bg-amber-100", text: "text-amber-800" },
                          { label: "Additional Skills", items: gapResult.extra, bg: "bg-gray-100", text: "text-gray-700" },
                        ] as const).map(({ label, items, bg, text }) =>
                          items.length > 0 && (
                            <div key={label}>
                              <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                                {label} ({items.length})
                              </p>
                              <div className="flex flex-wrap gap-1.5">
                                {items.map((s) => (
                                  <span
                                    key={s}
                                    className={`px-2.5 py-1 rounded-full ${bg} ${text} text-xs font-medium`}
                                  >
                                    {s}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ),
                        )}
                      </div>
                    )}

                    {!selectedGapRole && !gapResult && (
                      <p className="text-sm text-gray-400">
                        Select a role above to see how your project skills compare.
                      </p>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Skills Progress */}
              <TabsContent value="progress" className="space-y-6">
                <Card className="bg-white border border-gray-200">
                  <CardHeader className="border-b border-gray-200">
                    <CardTitle className="text-xl font-bold text-gray-900">
                      Skill Progression Timeline
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6 space-y-4">
                    {skillsLoading && (
                      <p className="text-sm text-gray-500">
                        Loading skill progression…
                      </p>
                    )}
                    {!skillsLoading && skillsTimeline.length === 0 && (
                      <p className="text-sm text-gray-500">
                        {skillsNote || "No skill progression timeline available yet."}
                      </p>
                    )}

                    {skillsTimeline.length > 0 && (
                      <div className="space-y-4">
                        <div className="flex flex-wrap gap-2">
                          {topSkills.length > 0 ? (
                            topSkills.map(([skill, count]) => (
                              <span
                                key={skill}
                                className="px-3 py-1 rounded-full bg-gray-900 text-white text-xs font-semibold"
                              >
                                {skill} · {count}
                              </span>
                            ))
                          ) : (
                            <span className="text-xs text-gray-400">
                              No top skills yet.
                            </span>
                          )}
                        </div>

                        <div className="grid gap-4">
                          {skillsTimeline.map((period) => (
                            <div
                              key={period.period_label}
                              className="rounded-xl border border-gray-200 p-4"
                            >
                              <div className="flex flex-wrap items-center justify-between gap-3">
                                <div>
                                  <h4 className="text-base font-semibold text-gray-900">
                                    {formatPeriodLabel(period.period_label)}
                                  </h4>
                                  <p className="text-xs text-gray-500">
                                    {period.period_label}
                                  </p>
                                </div>
                                <div className="flex flex-wrap gap-2 text-xs font-semibold">
                                  <span className="px-2.5 py-1 rounded-full bg-gray-900 text-white">
                                    {period.commits} commits
                                  </span>
                                  <span className="px-2.5 py-1 rounded-full bg-gray-100 text-gray-700">
                                    {period.skill_count} skills
                                  </span>
                                  <span className="px-2.5 py-1 rounded-full bg-gray-100 text-gray-700">
                                    {period.tests_changed} tests
                                  </span>
                                  <span className="px-2.5 py-1 rounded-full bg-gray-100 text-gray-700">
                                    {period.contributors} contributors
                                  </span>
                                </div>
                              </div>

                              <div className="mt-3 flex flex-wrap gap-2">
                                {period.activity_types.length > 0 ? (
                                  period.activity_types.map((type) => (
                                    <span
                                      key={type}
                                      className="px-2.5 py-1 rounded-full bg-gray-50 text-gray-600 text-xs font-semibold border border-gray-200"
                                    >
                                      {type}
                                    </span>
                                  ))
                                ) : (
                                  <span className="text-xs text-gray-400">
                                    No activity labels
                                  </span>
                                )}
                              </div>

                              <div className="mt-4 grid gap-4 md:grid-cols-2">
                                <div>
                                  <p className="text-xs font-semibold text-gray-500 uppercase">
                                    Top skills
                                  </p>
                                  <div className="mt-2 flex flex-wrap gap-2">
                                    {period.top_skills.length > 0 ? (
                                      period.top_skills.map((skill) => (
                                        <span
                                          key={skill}
                                          className="px-2.5 py-1 rounded-full bg-gray-900 text-white text-xs"
                                        >
                                          {skill}
                                        </span>
                                      ))
                                    ) : (
                                      <span className="text-xs text-gray-400">
                                        No skills recorded
                                      </span>
                                    )}
                                  </div>
                                </div>

                                <div>
                                  <p className="text-xs font-semibold text-gray-500 uppercase">
                                    Languages
                                  </p>
                                  <div className="mt-2 flex flex-wrap gap-2">
                                    {Object.keys(period.period_languages).length > 0 ? (
                                      Object.entries(period.period_languages).map(
                                        ([lang, count]) => (
                                          <span
                                            key={lang}
                                            className="px-2.5 py-1 rounded-full bg-gray-100 text-gray-700 text-xs"
                                          >
                                            {lang} · {count}
                                          </span>
                                        )
                                      )
                                    ) : (
                                      <span className="text-xs text-gray-400">
                                        No language data
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>

                              <div className="mt-4 grid gap-4 md:grid-cols-2">
                                <div>
                                  <p className="text-xs font-semibold text-gray-500 uppercase">
                                    Recent commits
                                  </p>
                                  <ul className="mt-2 space-y-1 text-sm text-gray-700">
                                    {period.commit_messages
                                      .slice(0, 4)
                                      .map((msg, index) => (
                                        <li
                                          key={`${period.period_label}-commit-${index}`}
                                          className="truncate"
                                        >
                                          {msg}
                                        </li>
                                      ))}
                                    {period.commit_messages.length === 0 && (
                                      <li className="text-xs text-gray-400">
                                        No commit messages recorded.
                                      </li>
                                    )}
                                  </ul>
                                </div>

                                <div>
                                  <p className="text-xs font-semibold text-gray-500 uppercase">
                                    Files touched
                                  </p>
                                  <ul className="mt-2 space-y-1 text-sm text-gray-700">
                                    {period.top_files.slice(0, 4).map((file, index) => (
                                      <li
                                        key={`${period.period_label}-file-${index}`}
                                        className="truncate"
                                      >
                                        {file}
                                      </li>
                                    ))}
                                    {period.top_files.length === 0 && (
                                      <li className="text-xs text-gray-400">
                                        No file highlights recorded.
                                      </li>
                                    )}
                                  </ul>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card className="bg-white border border-gray-200">
                  <CardHeader className="border-b border-gray-200 flex flex-row items-center justify-between">
                    <div>
                      <CardTitle className="text-xl font-bold text-gray-900">
                        AI Summary
                      </CardTitle>
                      <p className="text-xs text-gray-500 mt-1">
                        Summarize skill growth from the timeline.
                      </p>
                    </div>
                    <button
                      onClick={handleGenerateSummary}
                      disabled={summaryLoading}
                      className="px-3 py-2 text-xs font-semibold rounded-md bg-gray-900 text-white disabled:opacity-60"
                    >
                      {summaryLoading
                        ? "Generating…"
                        : skillsSummary
                        ? "Regenerate"
                        : "Generate"}
                    </button>
                  </CardHeader>
                  <CardContent className="p-6 space-y-4">
                    {skillsNote && <p className="text-sm text-gray-500">{skillsNote}</p>}
                    {skillsSummary && (
                      <div className="space-y-4">
                        <div>
                          <p className="text-sm font-semibold text-gray-700">Overview</p>
                          <p className="text-sm text-gray-700 mt-1">
                            {skillsSummary.overview}
                          </p>
                          {skillsSummary.validation_warning && (
                            <p className="text-xs text-amber-600 mt-2">
                              {skillsSummary.validation_warning}
                            </p>
                          )}
                        </div>

                        <div className="grid gap-4 md:grid-cols-2">
                          <div>
                            <p className="text-sm font-semibold text-gray-700">
                              Timeline highlights
                            </p>
                            <ul className="mt-2 space-y-1 text-sm text-gray-700 list-disc list-inside">
                              {skillsSummary.timeline.map((item, index) => (
                                <li key={`timeline-${index}`}>{item}</li>
                              ))}
                              {skillsSummary.timeline.length === 0 && (
                                <li className="text-xs text-gray-400">
                                  No timeline highlights.
                                </li>
                              )}
                            </ul>
                          </div>

                          <div>
                            <p className="text-sm font-semibold text-gray-700">
                              Skills focus
                            </p>
                            <ul className="mt-2 space-y-1 text-sm text-gray-700 list-disc list-inside">
                              {skillsSummary.skills_focus.map((item, index) => (
                                <li key={`skills-${index}`}>{item}</li>
                              ))}
                              {skillsSummary.skills_focus.length === 0 && (
                                <li className="text-xs text-gray-400">
                                  No skill focus notes.
                                </li>
                              )}
                            </ul>
                          </div>
                        </div>

                        <div>
                          <p className="text-sm font-semibold text-gray-700">
                            Suggested next steps
                          </p>
                          <ul className="mt-2 space-y-1 text-sm text-gray-700 list-disc list-inside">
                            {skillsSummary.suggested_next_steps.map((item, index) => (
                              <li key={`steps-${index}`}>{item}</li>
                            ))}
                            {skillsSummary.suggested_next_steps.length === 0 && (
                              <li className="text-xs text-gray-400">
                                No suggestions yet.
                              </li>
                            )}
                          </ul>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Contributions */}
              <TabsContent value="contributions">
                <Card className="bg-white border border-gray-200">
                  <CardHeader className="border-b border-gray-200">
                    <CardTitle className="text-xl font-bold text-gray-900">
                      Contribution Metrics
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {!scanData.contribution_metrics ? (
                      <p className="text-sm text-gray-500">
                        No contribution data available for this project.
                      </p>
                    ) : (
                      <div className="space-y-6">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div className="bg-gray-50 rounded-lg p-4 text-center">
                            <p className="text-2xl font-bold text-gray-900 capitalize">
                              {scanData.contribution_metrics.project_type ?? "Unknown"}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">Project Type</p>
                          </div>
                          <div className="bg-gray-50 rounded-lg p-4 text-center">
                            <p className="text-2xl font-bold text-gray-900">
                              {scanData.contribution_metrics.total_commits ?? 0}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">Total Commits</p>
                          </div>
                          <div className="bg-gray-50 rounded-lg p-4 text-center">
                            <p className="text-2xl font-bold text-gray-900">
                              {scanData.contribution_metrics.total_contributors ?? 1}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">Contributors</p>
                          </div>
                          <div className="bg-gray-50 rounded-lg p-4 text-center">
                            <p className="text-2xl font-bold text-gray-900">
                              {scanData.contribution_metrics.user_commit_share != null
                                ? `${(scanData.contribution_metrics.user_commit_share * 100).toFixed(0)}%`
                                : "—"}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">Your Share</p>
                          </div>
                        </div>

                        {scanData.contribution_metrics.contributors && 
                         scanData.contribution_metrics.contributors.length > 0 && (
                          <div>
                            <h4 className="text-sm font-semibold text-gray-900 mb-3">
                              Top Contributors
                            </h4>
                            <div className="space-y-3">
                              {scanData.contribution_metrics.contributors
                                .slice(0, 5)
                                .map((contributor: { name?: string; commits?: number; commit_percentage?: number }, idx: number) => (
                                <div key={idx} className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <Users size={14} className="text-gray-400" />
                                    <span className="text-sm font-medium text-gray-900">{contributor.name ?? "Unknown"}</span>
                                  </div>
                                  <div className="text-sm text-gray-500">
                                    {contributor.commits ?? 0} commits
                                    {contributor.commit_percentage != null && (
                                      <span className="ml-2 text-gray-400">
                                        ({contributor.commit_percentage.toFixed(0)}%)
                                      </span>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {scanData.contribution_metrics.project_start_date && (
                          <div className="pt-4 border-t border-gray-200">
                            <div className="flex gap-8 text-sm">
                              <div>
                                <span className="text-gray-500">Started:</span>{" "}
                                <span className="text-gray-900">
                                  {new Date(scanData.contribution_metrics.project_start_date).toLocaleDateString()}
                                </span>
                              </div>
                              {scanData.contribution_metrics.project_end_date && (
                                <div>
                                  <span className="text-gray-500">Last activity:</span>{" "}
                                  <span className="text-gray-900">
                                    {new Date(scanData.contribution_metrics.project_end_date).toLocaleDateString()}
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </TabsContent>

          {/* ============================================
              TAB 3: CONTENT ANALYSIS
          ============================================ */}
          <TabsContent value="content">
            <Tabs defaultValue="documents" className="space-y-6">
              <TabsList className="flex justify-start gap-1 h-auto bg-transparent p-0 border-b border-gray-200 rounded-none">
                {contentSubTabs.map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <TabsTrigger
                      key={tab.value}
                      value={tab.value}
                      className="text-xs px-4 py-2 rounded-t-lg rounded-b-none border-b-2 border-transparent data-[state=active]:border-gray-900 data-[state=active]:bg-white"
                    >
                      <Icon size={14} className="mr-1.5" />
                      {tab.label}
                    </TabsTrigger>
                  );
                })}
              </TabsList>

              {/* Documents */}
              <TabsContent value="documents">
                <DocumentAnalysisTab
                  documentAnalysis={scanData.document_analysis}
                  isLoading={projectLoading}
                  errorMessage={projectError}
                />
              </TabsContent>

                 {/* Code Analysis */}
            <TabsContent value="code-analysis">
              <CodeAnalysisTab
                codeAnalysis={isPlainObject(scanData.code_analysis) ? scanData.code_analysis : null}
                isLoading={projectLoading}
                errorMessage={projectError}
              />
            </TabsContent>

              {/* Media */}
              <TabsContent value="media">
                <MediaAnalysisTab
                  loading={projectLoading}
                  error={projectError}
                  mediaAnalysis={mediaAnalysis}
                  onRetry={loadProject}
                />
              </TabsContent>

              {/* PDFs */}
              <TabsContent value="pdfs">
                <PdfAnalysisTab
                  pdfAnalysis={scanData.pdf_analysis}
                  isLoading={projectLoading}
                  errorMessage={projectError}
                />
              </TabsContent>
            </Tabs>
          </TabsContent>

          {/* ============================================
              TAB 4: TOOLS & EXPORT
          ============================================ */}
          <TabsContent value="tools">
            <Tabs
              key={activeToolsTab}
              defaultValue={activeToolsTab}
              onValueChange={(value) => setActiveToolsTab(value as ToolsTabValue)}
              className="space-y-6"
            >
              <TabsList className="flex justify-start gap-1 h-auto bg-transparent p-0 border-b border-gray-200 rounded-none">
                {toolsSubTabs.map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <TabsTrigger
                      key={tab.value}
                      value={tab.value}
                      className="text-xs px-4 py-2 rounded-t-lg rounded-b-none border-b-2 border-transparent data-[state=active]:border-gray-900 data-[state=active]:bg-white"
                    >
                      <Icon size={14} className="mr-1.5" />
                      {tab.label}
                    </TabsTrigger>
                  );
                })}
              </TabsList>

              <TabsContent value="tools-main">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  <Card className="bg-white border border-gray-200">
                    <CardHeader className="border-b border-gray-200">
                      <CardTitle className="text-base font-bold text-gray-900">
                        <button
                          type="button"
                          onClick={() => openToolsTab("file-browser")}
                          className="inline-flex items-center gap-2 hover:text-gray-700"
                        >
                          <FileText size={18} />
                          File Browser
                        </button>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 space-y-4">
                      <p className="text-sm text-gray-500">
                        Browse indexed project files in a dedicated full view.
                      </p>
                      <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                        <p className="text-xs text-gray-500">Indexed files</p>
                        <p className="mt-1 text-lg font-semibold text-gray-900">
                          {formatCount(projectFiles.length)}
                        </p>
                      </div>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => openToolsTab("file-browser")}
                      >
                        Open Full View
                      </Button>
                    </CardContent>
                  </Card>

                  <Card className="bg-white border border-gray-200">
                    <CardHeader className="border-b border-gray-200">
                      <CardTitle className="text-base font-bold text-gray-900">
                        <button
                          type="button"
                          onClick={() => openToolsTab("git-analysis")}
                          className="inline-flex items-center gap-2 hover:text-gray-700"
                        >
                          <GitBranch size={18} />
                          Git Analysis
                        </button>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 space-y-4">
                      <p className="text-sm text-gray-500">
                        Compact view of repositories and commit activity.
                      </p>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                          <p className="text-xs text-gray-500">Repositories</p>
                          <p className="mt-1 text-lg font-semibold text-gray-900">
                            {gitRepoTotal}
                          </p>
                        </div>
                        <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                          <p className="text-xs text-gray-500">Commits</p>
                          <p className="mt-1 text-lg font-semibold text-gray-900">
                            {formatCount(gitCommitTotal)}
                          </p>
                        </div>
                      </div>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => openToolsTab("git-analysis")}
                      >
                        Open Full View
                      </Button>
                    </CardContent>
                  </Card>

                  <Card className="bg-white border border-gray-200">
                    <CardHeader className="border-b border-gray-200">
                      <CardTitle className="text-base font-bold text-gray-900">
                        <button
                          type="button"
                          onClick={() => openToolsTab("duplicate-finder")}
                          className="inline-flex items-center gap-2 hover:text-gray-700"
                        >
                          <Copy size={18} />
                          Duplicate Finder
                        </button>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 space-y-4">
                      <p className="text-sm text-gray-500">
                        Quick snapshot of duplicate groups and storage waste.
                      </p>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                          <p className="text-xs text-gray-500">Groups</p>
                          <p className="mt-1 text-lg font-semibold text-gray-900">
                            {duplicateOverview?.totalGroups ?? 0}
                          </p>
                        </div>
                        <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                          <p className="text-xs text-gray-500">Wasted</p>
                          <p className="mt-1 text-lg font-semibold text-gray-900">
                            {formatBytes(duplicateOverview?.totalWastedBytes ?? 0)}
                          </p>
                        </div>
                      </div>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => openToolsTab("duplicate-finder")}
                      >
                        Open Full View
                      </Button>
                    </CardContent>
                  </Card>

                  {/* Search & Filter */}
                  <Card className="bg-white border border-gray-200">
                    <CardHeader className="border-b border-gray-200">
                      <CardTitle className="text-base font-bold text-gray-900 flex items-center gap-2">
                        <Search size={18} />
                        Search & Filter
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-6">
                      <p className="text-sm text-gray-500 mb-4">
                        Use the dedicated search workspace to query files and skills across scanned projects.
                      </p>
                      <Link
                        href="/search"
                        className="inline-flex items-center rounded-md bg-gray-900 px-3 py-2 text-xs font-semibold text-white hover:bg-gray-800"
                      >
                        Open Search
                      </Link>
                    </CardContent>
                  </Card>

                  {/* Resume Generator */}
                  <Card className="bg-white border border-gray-200">
                    <CardHeader className="border-b border-gray-200">
                      <CardTitle className="text-base font-bold text-gray-900 flex items-center gap-2">
                        <FileEdit size={18} />
                        Resume Generator
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-6">
                      <p className="text-sm text-gray-500 mb-4">
                        Generate resume items from project analysis.
                      </p>
                      <PlaceholderContent label="Resume Generator" />
                    </CardContent>
                  </Card>

                  {/* Export Options */}
                  <Card className="bg-white border border-gray-200">
                    <CardHeader className="border-b border-gray-200">
                      <CardTitle className="text-base font-bold text-gray-900 flex items-center gap-2">
                        <FileJson size={18} />
                        Export Options
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 space-y-3">
                      <p className="text-sm text-gray-500">
                        Export project analysis in various formats.
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {/* Export JSON — active */}
                        <button
                          onClick={handleExportJson}
                          disabled={!hasProject || exportStatus === "exporting"}
                          className={[
                            "px-3 py-2 text-xs font-semibold rounded-md flex items-center gap-1 transition-colors",
                            exportStatus === "success"
                              ? "bg-emerald-100 text-emerald-700"
                              : exportStatus === "error"
                                ? "bg-red-100 text-red-700"
                                : !hasProject
                                  ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                                  : "bg-gray-900 text-white hover:bg-gray-700 cursor-pointer",
                          ].join(" ")}
                        >
                          {exportStatus === "exporting" ? (
                            <><Loader2 size={14} className="animate-spin" /> Exporting…</>
                          ) : exportStatus === "success" ? (
                            <><Check size={14} /> Downloaded!</>
                          ) : exportStatus === "error" ? (
                            <><AlertCircle size={14} /> {exportError ?? "Failed"}</>
                          ) : (
                            <><Download size={14} /> Export JSON</>
                          )}
                        </button>
                        <button
                          onClick={handleExportHtml}
                          disabled={!hasProject || htmlExportStatus === "exporting"}
                          className={[
                            "px-3 py-2 text-xs font-semibold rounded-md flex items-center gap-1 transition-colors",
                            htmlExportStatus === "success"
                              ? "bg-emerald-100 text-emerald-700"
                              : htmlExportStatus === "error"
                                ? "bg-red-100 text-red-700"
                                : !hasProject
                                  ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                                  : "bg-gray-900 text-white hover:bg-gray-700 cursor-pointer",
                          ].join(" ")}
                        >
                          {htmlExportStatus === "exporting" ? (
                            <><Loader2 size={14} className="animate-spin" /> Exporting…</>
                          ) : htmlExportStatus === "success" ? (
                            <><Check size={14} /> Downloaded!</>
                          ) : htmlExportStatus === "error" ? (
                            <><AlertCircle size={14} /> {htmlExportError ?? "Failed"}</>
                          ) : (
                            <><FileCode2 size={14} /> Export HTML</>
                          )}
                        </button>
                      </div>
                      {htmlExportStatus === "error" && htmlExportError && (
                        <p className="text-xs text-red-500 mt-1">{htmlExportError}</p>
                      )}
                      {exportStatus === "error" && exportError && (
                        <p className="text-xs text-red-500 mt-1">{exportError}</p>
                      )}
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>

              <TabsContent value="file-browser" className="space-y-4">
                <Card className="bg-white border border-gray-200">
                  <CardHeader className="border-b border-gray-200 flex flex-row items-center justify-between">
                    <CardTitle className="text-xl font-bold text-gray-900 flex items-center gap-2">
                      <FileText size={18} />
                      File Browser
                    </CardTitle>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setActiveToolsTab("tools-main")}
                    >
                      Back to Overview
                    </Button>
                  </CardHeader>
                  <CardContent className="p-6">
                    <FileTreeView files={projectFiles} />
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="search-filter" className="space-y-4">
                <Card className="bg-white border border-gray-200">
                  <CardHeader className="border-b border-gray-200 flex flex-row items-center justify-between">
                    <CardTitle className="text-xl font-bold text-gray-900 flex items-center gap-2">
                      <Search size={18} />
                      Search &amp; Filter Files
                    </CardTitle>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setActiveToolsTab("tools-main")}
                    >
                      Back to Overview
                    </Button>
                  </CardHeader>
                  <CardContent className="p-6">
                    <SearchFilterTab
                      files={projectFiles}
                      loading={projectLoading}
                      error={projectError}
                      onRetry={loadProject}
                    />
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="git-analysis" className="space-y-4">
                <Card className="bg-white border border-gray-200">
                  <CardHeader className="border-b border-gray-200 flex flex-row items-center justify-between">
                    <CardTitle className="text-xl font-bold text-gray-900 flex items-center gap-2">
                      <GitBranch size={18} />
                      Git Analysis
                    </CardTitle>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setActiveToolsTab("tools-main")}
                    >
                      Back to Overview
                    </Button>
                  </CardHeader>
                  <CardContent className="p-6">
                    <GitAnalysisTab
                      loading={projectLoading}
                      error={projectError}
                      gitAnalysis={scanData.git_analysis}
                      onRetry={loadProject}
                    />
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="duplicate-finder" className="space-y-4">
                <Card className="bg-white border border-gray-200">
                  <CardHeader className="border-b border-gray-200 flex flex-row items-center justify-between">
                    <CardTitle className="text-xl font-bold text-gray-900 flex items-center gap-2">
                      <Copy size={18} />
                      Duplicate Finder
                    </CardTitle>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setActiveToolsTab("tools-main")}
                    >
                      Back to Overview
                    </Button>
                  </CardHeader>
                  <CardContent className="p-6">
                    <DuplicateFinderTab
                      duplicateReport={scanData.duplicate_report}
                      isLoading={projectLoading}
                      errorMessage={projectError}
                      onRetry={loadProject}
                    />
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}

/** ------------------ Formatting helpers (from main) ------------------ */

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function formatPeriodLabel(value: string) {
  const [year, month] = value.split("-");
  if (!year || !month) return value;
  const date = new Date(Number(year), Number(month) - 1, 1);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short" });
}

function formatDurationSeconds(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "Not available";
  if (seconds >= 10) return `${seconds.toFixed(0)} seconds`;
  return `${seconds.toFixed(1)} seconds`;
}

function formatBytes(bytes: number): string {
  if (!bytes || Number.isNaN(bytes)) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const value = bytes / Math.pow(k, i);
  return `${value.toFixed(1)} ${sizes[i]}`;
}

function formatCount(value: number | string): string {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return numeric.toLocaleString();
}

function formatConfidence(value: number | string): string {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  if (numeric <= 1) return `${(numeric * 100).toFixed(0)}%`;
  if (numeric <= 100) return `${numeric.toFixed(0)}%`;
  return numeric.toFixed(2);
}
