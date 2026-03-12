"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DocumentAnalysisTab } from "@/components/project/document-analysis-tab";
import { OverviewTab } from "@/components/project/overview-tab";
import { LanguagesTab } from "@/components/project/languages-tab";
import { SkillsTab } from "@/components/project/skills-tab";
import { ProgressTab } from "@/components/project/progress-tab";
import { ContributionsTab } from "@/components/project/contributions-tab";
import { ToolsMainTab } from "@/components/project/tools-main-tab";
import { PdfAnalysisTab } from "@/components/project/pdf-analysis-tab";
import { getStoredToken } from "@/lib/auth";
import { consent as consentApi, secrets as secretsApi } from "@/lib/api";
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
  ProjectSkillsAnalysis,
  SkillEvidenceItem,
  SkillAdoptionEntry,
  SkillProgressPeriod,
  SkillProgressSummary,
  RoleProfile,
  SkillGapAnalysis,
} from "@/types/project";
import { getCategoryLabel, buildEvidenceMap } from "@/lib/skills-utils";
import {
  isPlainObject,
  formatDurationSeconds,
  formatBytes,
  formatCount,
} from "@/lib/format-utils";
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
  Users,
  FileText,
  Film,
  FileImage,
  GitBranch,
  Copy,
  Search,
  FileCode2,
  Sparkles,
} from "lucide-react";
import { FileTreeView } from "@/components/project/file-tree-view";
import { SearchFilterTab } from "@/components/project/search-filter-tab";
import type { FileEntry } from "@/lib/file-tree";

const mainTabs = [
  { value: "overview", label: "Overview & Analysis", icon: LayoutDashboard },
  { value: "skills", label: "Skills & Progress", icon: Award },
  { value: "content", label: "Content Analysis", icon: BookOpen },
  { value: "ai-analysis", label: "AI Analysis", icon: Sparkles },
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
  const [aiEligibilityChecked, setAiEligibilityChecked] = useState(false);
  const [aiEligibilityLoading, setAiEligibilityLoading] = useState(false);
  const [externalServicesConsentEnabled, setExternalServicesConsentEnabled] = useState(false);
  const [openAiKeyValid, setOpenAiKeyValid] = useState(false);
  const [aiEligibilityMessage, setAiEligibilityMessage] = useState<string | null>(null);

  // Highlighted skills state
  const [highlightedSkills, setHighlightedSkills] = useState<string[]>([]);
  const [isSavingHighlights, setIsSavingHighlights] = useState(false);
  const [highlightSaveStatus, setHighlightSaveStatus] = useState<"idle" | "success" | "error">("idle");

  // Skills search, filter, and evidence expansion state
  const [skillsSearchQuery, setSkillsSearchQuery] = useState("");
  const [skillsCategoryFilter, setSkillsCategoryFilter] = useState<string>("all");
  const [expandedSkillKey, setExpandedSkillKey] = useState<string | null>(null);

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

  const checkAiEligibility = useCallback(async (): Promise<boolean> => {
    const token = getStoredToken();
    if (!token) {
      setExternalServicesConsentEnabled(false);
      setOpenAiKeyValid(false);
      setAiEligibilityMessage(
        "AI analysis is unavailable because you are not logged in. Sign in from Settings and try again."
      );
      setAiEligibilityChecked(true);
      return false;
    }

    setAiEligibilityLoading(true);
    setAiEligibilityMessage(null);

    try {
      const consentResult = await consentApi.get();
      if (!consentResult.ok) {
        const authFailure = consentResult.status === 401 || consentResult.status === 403;
        setExternalServicesConsentEnabled(false);
        setOpenAiKeyValid(false);
        setAiEligibilityMessage(
          authFailure
            ? "AI analysis is unavailable because your session expired. Log in again from Settings."
            : consentResult.error ||
                "Unable to load consent status. Open Settings and verify your consent preferences."
        );
        return false;
      }

      const externalConsent = Boolean(consentResult.data.external_services);
      setExternalServicesConsentEnabled(externalConsent);

      if (!externalConsent) {
        setOpenAiKeyValid(false);
        setAiEligibilityMessage(
          "AI analysis is disabled because External Data consent is not enabled. Enable it in Settings > Consent."
        );
        return false;
      }

      const verifyResult = await secretsApi.verify();
      if (!verifyResult.ok) {
        setOpenAiKeyValid(false);
        setAiEligibilityMessage(
          verifyResult.error ||
            "Unable to verify your OpenAI API key. Open Settings and verify the key before running AI analysis."
        );
        return false;
      }

      if (!verifyResult.data.valid) {
        setOpenAiKeyValid(false);
        setAiEligibilityMessage(
          verifyResult.data.message ||
            "Your OpenAI API key is not valid. Update it in Settings before running AI analysis."
        );
        return false;
      }

      setOpenAiKeyValid(true);
      setAiEligibilityMessage(null);
      return true;
    } catch (err) {
      setExternalServicesConsentEnabled(false);
      setOpenAiKeyValid(false);
      setAiEligibilityMessage(
        err instanceof Error
          ? err.message
          : "Unable to validate AI analysis prerequisites. Try again from the AI Analysis tab."
      );
      return false;
    } finally {
      setAiEligibilityLoading(false);
      setAiEligibilityChecked(true);
    }
  }, []);

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

  useEffect(() => {
    if (activeMainTab === "ai-analysis") {
      void checkAiEligibility();
    }
  }, [activeMainTab, checkAiEligibility]);

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
  const skillsAnalysis: ProjectSkillsAnalysis = scanData.skills_analysis ?? {};
  const skillsByCategory = skillsAnalysis.skills_by_category ?? {};
  const totalSkills =
    typeof skillsAnalysis.total_skills === "number" ? skillsAnalysis.total_skills : 0;

  // Category labels from backend, with fallback
  const categoryLabels: Record<string, string> = skillsAnalysis.category_labels ?? {};
  const categoryLabel = (key: string) => getCategoryLabel(key, categoryLabels);

  // Pre-indexed evidence map for O(1) lookups
  const evidenceMap = useMemo(
    () => buildEvidenceMap(skillsAnalysis.skills ?? []),
    [skillsAnalysis.skills],
  );
  const getSkillEvidence = (skillName: string): SkillEvidenceItem[] =>
    evidenceMap[skillName] ?? [];

  // Adoption timeline
  const skillAdoptionTimeline: SkillAdoptionEntry[] = skillsAnalysis.skill_adoption_timeline ?? [];

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

  const aiEligibilityReady =
    externalServicesConsentEnabled && openAiKeyValid;

  const handleGenerateSummary = async () => {
    const effectiveProjectId = projectId ?? project?.id ?? null;
    if (!effectiveProjectId) return;

    const token = getStoredToken();
    if (!token) {
      setSkillsNote("Not authenticated. Please log in through Settings.");
      return;
    }

    const eligible = await checkAiEligibility();
    if (!eligible) {
      setSkillsNote(
        aiEligibilityMessage ||
          "AI analysis could not run because consent or key requirements are not met."
      );
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
              <TabsContent value="overview-main">
                <OverviewTab
                  projectName={projectName}
                  projectPath={projectPath}
                  scanTimestamp={scanTimestamp}
                  scanDurationLabel={scanDurationLabel}
                  filesProcessedLabel={filesProcessedLabel}
                  totalSizeLabel={totalSizeLabel}
                  issuesFoundLabel={issuesFoundLabel}
                  totalLinesLabel={totalLinesLabel}
                  gitRepos={gitRepos}
                  mediaFiles={mediaFiles}
                  pdfDocs={pdfDocs}
                  otherDocs={otherDocs}
                  contributionMetrics={scanData.contribution_metrics as { total_commits?: number | null; total_contributors?: number | null } | undefined}
                />
              </TabsContent>

              {/* Languages Breakdown */}
              <TabsContent value="languages">
                <LanguagesTab topLanguages={topLanguages} />
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
              <TabsContent value="skills-main">
                <SkillsTab
                  highlightedSkills={highlightedSkills}
                  highlightSaveStatus={highlightSaveStatus}
                  isSavingHighlights={isSavingHighlights}
                  saveHighlightedSkills={saveHighlightedSkills}
                  toggleSkillHighlight={toggleSkillHighlight}
                  skillsAnalysis={skillsAnalysis}
                  skillsByCategory={skillsByCategory}
                  totalSkills={totalSkills}
                  categoryLabel={categoryLabel}
                  skillsSearchQuery={skillsSearchQuery}
                  setSkillsSearchQuery={setSkillsSearchQuery}
                  skillsCategoryFilter={skillsCategoryFilter}
                  setSkillsCategoryFilter={setSkillsCategoryFilter}
                  filteredSkillsByCategory={filteredSkillsByCategory}
                  expandedSkillKey={expandedSkillKey}
                  setExpandedSkillKey={setExpandedSkillKey}
                  getSkillEvidence={getSkillEvidence}
                  skillAdoptionTimeline={skillAdoptionTimeline}
                  gapRoles={gapRoles}
                  selectedGapRole={selectedGapRole}
                  gapResult={gapResult}
                  gapLoading={gapLoading}
                  gapError={gapError}
                  runGapAnalysis={runGapAnalysis}
                />
              </TabsContent>

              {/* Skills Progress */}
              <TabsContent value="progress">
                <ProgressTab
                  skillsTimeline={skillsTimeline}
                  topSkills={topSkills}
                  skillsLoading={skillsLoading}
                  skillsNote={skillsNote}
                  skillsSummary={skillsSummary}
                  summaryLoading={summaryLoading}
                  handleGenerateSummary={handleGenerateSummary}
                />
              </TabsContent>

              {/* Contributions */}
              <TabsContent value="contributions">
                <ContributionsTab contributionMetrics={scanData.contribution_metrics} />
              </TabsContent>
            </Tabs>
          </TabsContent>

          <TabsContent value="ai-analysis" className="space-y-6">
            <Card className="bg-white border border-gray-200">
              <CardHeader className="border-b border-gray-200">
                <CardTitle className="text-xl font-bold text-gray-900">
                  AI Analysis Status
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                    <p className="text-xs font-semibold text-gray-500 uppercase">External Data Consent</p>
                    <p className={`mt-2 text-sm font-medium ${externalServicesConsentEnabled ? "text-green-700" : "text-gray-600"}`}>
                      {externalServicesConsentEnabled ? "Enabled" : "Not enabled"}
                    </p>
                  </div>
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                    <p className="text-xs font-semibold text-gray-500 uppercase">OpenAI API Key</p>
                    <p className={`mt-2 text-sm font-medium ${openAiKeyValid ? "text-green-700" : "text-gray-600"}`}>
                      {openAiKeyValid ? "Verified" : "Missing or invalid"}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => void checkAiEligibility()}
                    disabled={aiEligibilityLoading}
                    className="border-gray-300"
                  >
                    {aiEligibilityLoading ? "Checking..." : "Re-check requirements"}
                  </Button>
                  <Link href="/settings" className="text-sm text-gray-700 underline">
                    Open Settings
                  </Link>
                </div>

                {!aiEligibilityChecked && (
                  <p className="text-sm text-gray-500">
                    Open this tab to validate consent and API key requirements.
                  </p>
                )}

                {aiEligibilityChecked && !aiEligibilityReady && (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                    <p className="text-sm text-amber-800">
                      {aiEligibilityMessage ||
                        "AI analysis is currently blocked. Enable External Data consent and verify your OpenAI API key in Settings."}
                    </p>
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
                  disabled={summaryLoading || aiEligibilityLoading || !aiEligibilityReady}
                  className="px-3 py-2 text-xs font-semibold rounded-md bg-gray-900 text-white disabled:opacity-60"
                >
                  {summaryLoading
                    ? "Generating..."
                    : skillsSummary
                    ? "Regenerate"
                    : "Generate"}
                </button>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                {skillsNote && <p className="text-sm text-gray-500">{skillsNote}</p>}
                {!aiEligibilityReady && (
                  <p className="text-sm text-gray-500">
                    AI summary generation stays disabled until External Data consent is enabled and a valid OpenAI API key is verified in Settings.
                  </p>
                )}
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
                <ToolsMainTab
                  openToolsTab={openToolsTab}
                  projectFilesCount={projectFiles.length}
                  gitRepoTotal={gitRepoTotal}
                  gitCommitTotal={gitCommitTotal}
                  duplicateOverview={duplicateOverview}
                  hasProject={hasProject}
                  exportStatus={exportStatus}
                  exportError={exportError}
                  handleExportJson={handleExportJson}
                  htmlExportStatus={htmlExportStatus}
                  htmlExportError={htmlExportError}
                  handleExportHtml={handleExportHtml}
                />
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
