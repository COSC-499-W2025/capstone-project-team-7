"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { DocumentAnalysisTab } from "@/components/project/document-analysis-tab";
import { getStoredToken } from "@/lib/auth";
import {
  getProjects,
  getProjectById,
  getProjectSkillTimeline,
  generateProjectSkillSummary,
} from "@/lib/api/projects";
import {
  detectLanguageMetric,
  normalizeLanguageStats,
  type NormalizedLanguageStat,
  type LanguageMetric,
} from "@/lib/language-stats";
import type {
  ProjectDetail,
  SkillProgressPeriod,
  SkillProgressSummary,
} from "@/types/project";
import {
  MediaAnalysisTab,
  type MediaAnalysisPayload,
  type MediaAnalysisMetrics,
  type MediaAnalysisSummary,
  type MediaListItem,
} from "@/components/project/media-analysis-tab";
import {
  LayoutDashboard,
  FileText,
  BarChart3,
  Code2,
  Award,
  TrendingUp,
  GitBranch,
  Users,
  FileEdit,
  Copy,
  Search,
  FileJson,
  FileCode2,
  Printer,
  FileImage,
  BookOpen,
  Film,
} from "lucide-react";

const tabs = [
  { value: "overview", label: "Show Overview", icon: LayoutDashboard },
  { value: "file-list", label: "View File List", icon: FileText },
  { value: "languages", label: "Language Breakdown", icon: BarChart3 },
  { value: "code-analysis", label: "Code Analysis", icon: Code2 },
  { value: "skills", label: "Skills Analysis", icon: Award },
  { value: "skills-progress", label: "Skills Progression", icon: TrendingUp },
  { value: "git-analysis", label: "Run Git Analysis", icon: GitBranch },
  { value: "contributions", label: "Contribution Metrics", icon: Users },
  { value: "resume-item", label: "Generate Resume Item", icon: FileEdit },
  { value: "duplicates", label: "Find Duplicate Files", icon: Copy },
  { value: "search-filter", label: "Search and Filter Files", icon: Search },
  { value: "export-json", label: "Export JSON Report", icon: FileJson },
  { value: "export-html", label: "Export HTML Report", icon: FileCode2 },
  { value: "export-print", label: "Export Printable Report", icon: Printer },
  { value: "analyze-pdf", label: "Analyze PDF Files", icon: FileImage },
  { value: "doc-analysis", label: "Document Analysis", icon: BookOpen },
  { value: "media-analysis", label: "Media Analysis", icon: Film },
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
  const projectIdParam = searchParams.get("projectId");

  const [projectId, setProjectId] = useState<string | null>(projectIdParam);
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [projectError, setProjectError] = useState<string | null>(null);
  const [projectLoading, setProjectLoading] = useState(true);

  const isMountedRef = useRef(true);

  // Skills / progression state (from main)
  const [skillsTimeline, setSkillsTimeline] = useState<SkillProgressPeriod[]>(
    []
  );
  const [skillsSummary, setSkillsSummary] =
    useState<SkillProgressSummary | null>(null);
  const [skillsNote, setSkillsNote] = useState<string | null>(null);
  const [skillsLoading, setSkillsLoading] = useState(false);
  const [summaryLoading, setSummaryLoading] = useState(false);

  // Keep local projectId in sync with URL
  useEffect(() => {
    setProjectId(projectIdParam);
  }, [projectIdParam]);

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
  }, [projectIdParam]);

  useEffect(() => {
    isMountedRef.current = true;
    loadProject();
    return () => {
      isMountedRef.current = false;
    };
  }, [loadProject]);

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

  const scanData = (project?.scan_data ?? {}) as any;
  const summary = (scanData.summary ?? {}) as any;
  const skillsAnalysis = (scanData.skills_analysis ?? {}) as any;
  const skillsByCategory = (skillsAnalysis.skills_by_category ?? {}) as any;
  const totalSkills = (skillsAnalysis.total_skills ?? 0) as number;

  const hasProject = Boolean(project);

  const projectName = project?.project_name ?? "";
  const projectPath = project?.project_path ?? "";
  const scanTimestamp = project?.scan_timestamp ?? "Not available";

  const scanDurationRaw = Number(
    summary.scan_duration_seconds ?? scanData.scan_duration_seconds ?? scanData.scan_duration
  );
  const scanDurationLabel = Number.isFinite(scanDurationRaw)
    ? formatDurationSeconds(scanDurationRaw)
    : "Not available";

  const filesProcessed = summary.total_files ?? project?.total_files ?? 0;
  const totalSizeBytes = summary.bytes_processed;
  const issuesFound = summary.issues_found ?? summary.issue_count ?? 0;
  const totalLines = summary.total_lines ?? project?.total_lines ?? 0;

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

  const gitRepos = scanData.git_analysis?.repositories?.length ?? 0;

  const documentAnalysis = scanData.document_analysis;
  const otherDocs = Array.isArray(documentAnalysis)
    ? documentAnalysis.length
    : Array.isArray(documentAnalysis?.documents)
    ? documentAnalysis.documents.length
    : Array.isArray(documentAnalysis?.items)
    ? documentAnalysis.items.length
    : 0;

  // Media analysis (from feature/media-analysis)
  const mediaAnalysis = useMemo<MediaAnalysisPayload | null>(() => {
    if (!project?.scan_data) return null;
    const data = project.scan_data as Record<string, unknown>;
    return resolveMediaAnalysis(data);
  }, [project]);

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
        <Link
          href={"/scanned-results" as any}
          className="text-sm text-gray-600 hover:text-gray-900 mb-2 inline-block"
        >
          ← Back
        </Link>

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
      <Tabs defaultValue="overview">
        <TabsList className="flex justify-start overflow-x-auto gap-1 h-auto bg-gray-100 rounded-lg p-1.5 scrollbar-thin">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <TabsTrigger
                key={tab.value}
                value={tab.value}
                className="gap-1.5 text-xs px-2.5 py-1.5 shrink-0"
              >
                <Icon size={14} />
                {tab.label}
              </TabsTrigger>
            );
          })}
        </TabsList>

        {/* Overview */}
        <TabsContent value="overview">
          <div className="space-y-6">
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
                    <p className="text-xs text-gray-500 mt-1">Files Processed</p>
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

            <Card className="bg-white border border-gray-200">
              <CardHeader className="border-b border-gray-200">
                <CardTitle className="text-xl font-bold text-gray-900">
                  Top 5 Languages
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                {topLanguages.length === 0 ? (
                  <p className="text-sm text-gray-500">No language data available for this project.</p>
                ) : (
                  <div className="space-y-3">
                    {topLanguages.map((lang) => (
                      <div key={lang.name} className="flex items-center gap-3">
                        <span className="text-sm text-gray-900 w-28 font-medium">
                          {lang.name}
                        </span>
                        <div className="flex-1 bg-gray-100 rounded-full h-2.5">
                          <div
                            className="bg-gray-900 h-2.5 rounded-full"
                            style={{ width: `${lang.percentage}%` }}
                          />
                        </div>
                        <span className="text-sm text-gray-500 w-14 text-right">
                          {lang.percentage}%
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card className="bg-white border border-gray-200">
                <CardHeader className="border-b border-gray-200">
                  <CardTitle className="text-base font-bold text-gray-900">
                    Git Repositories
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <p className="text-3xl font-bold text-gray-900">{gitRepos}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    Repositories detected
                  </p>
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
          </div>
        </TabsContent>

        {/* Language Breakdown */}
        <TabsContent value="languages">
          <div className="space-y-6">
            <Card className="bg-white border border-gray-200">
              <CardHeader className="border-b border-gray-200">
                <CardTitle className="text-xl font-bold text-gray-900">
                  Language Breakdown
                </CardTitle>
                <p className="text-xs text-gray-500 mt-1">
                  Distribution across detected languages.
                </p>
              </CardHeader>
              <CardContent className="p-6 space-y-6">
                {projectLoading && (
                  <div className="space-y-4 animate-pulse">
                    <div className="h-3 w-full rounded-full bg-gray-100" />
                    <div className="h-3 w-5/6 rounded-full bg-gray-100" />
                    <div className="h-3 w-2/3 rounded-full bg-gray-100" />
                  </div>
                )}

                {!projectLoading && projectError && (
                  <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                    <p className="text-sm font-semibold text-red-700">
                      Couldn’t load language breakdown.
                    </p>
                    <p className="text-xs text-red-600 mt-1">
                      {projectError}
                    </p>
                  </div>
                )}

                {!projectLoading &&
                  !projectError &&
                  languageBreakdown.length === 0 && (
                    <div className="rounded-lg border border-gray-200 bg-gray-50 p-6 text-center">
                      <p className="text-sm font-semibold text-gray-900">
                        No language breakdown available for this project yet.
                      </p>
                      <p className="text-xs text-gray-500 mt-2">
                        Run a scan with language detection enabled to see distribution details.
                      </p>
                    </div>
                  )}

                {!projectLoading &&
                  !projectError &&
                  languageBreakdown.length > 0 && (
                    <>
                      <div className="space-y-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="text-sm font-semibold text-gray-700">
                            Distribution
                          </p>
                          {languageTotalValue > 0 && (
                            <p className="text-xs text-gray-500">
                              {languageTotalLabel}:{" "}
                              <span className="font-semibold text-gray-900">
                                {formatLanguageValue(languageTotalValue)}
                              </span>
                            </p>
                          )}
                        </div>

                        <div className="h-3 w-full rounded-full overflow-hidden bg-gray-100 flex">
                          {languageChartData.map((lang, index) => {
                            const color =
                              LANGUAGE_COLORS[index % LANGUAGE_COLORS.length];
                            return (
                              <div
                                key={`${lang.name}-${index}`}
                                className={`h-full ${color}`}
                                style={{ width: `${lang.percent}%` }}
                                title={`${lang.name} • ${lang.percent}%`}
                              />
                            );
                          })}
                        </div>

                        <div className="flex flex-wrap gap-3 text-xs text-gray-600">
                          {languageChartData.map((lang, index) => {
                            const color =
                              LANGUAGE_COLORS[index % LANGUAGE_COLORS.length];
                            return (
                              <div
                                key={`${lang.name}-legend-${index}`}
                                className="flex items-center gap-2"
                              >
                                <span className={`h-2.5 w-2.5 rounded-full ${color}`} />
                                <span className="font-medium text-gray-800">
                                  {lang.name}
                                </span>
                                <span>{lang.percent}%</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      <div className="overflow-x-auto">
                        <table className="w-full text-sm border border-gray-200 rounded-lg">
                          <thead className="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
                            <tr>
                              <th className="text-left px-4 py-3">Language</th>
                              <th className="text-right px-4 py-3">%</th>
                              <th className="text-right px-4 py-3">
                                {languageMetricLabel}
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            {languageBreakdown.map((lang, index) => {
                              const color =
                                LANGUAGE_COLORS[index % LANGUAGE_COLORS.length];
                              return (
                                <tr
                                  key={lang.name}
                                  className="border-t border-gray-200"
                                >
                                  <td className="px-4 py-3">
                                    <div className="flex items-center gap-2">
                                      <span
                                        className={`h-2.5 w-2.5 rounded-full ${color}`}
                                      />
                                      <span className="font-medium text-gray-900">
                                        {lang.name}
                                      </span>
                                    </div>
                                  </td>
                                  <td className="px-4 py-3 text-right text-gray-700">
                                    {lang.percent.toFixed(1)}%
                                  </td>
                                  <td className="px-4 py-3 text-right text-gray-700">
                                    {formatLanguageValue(lang.bytes)}
                                  </td>
                                </tr>
                              );
                            })}
                            {languageValuesTotal > 0 && (
                              <tr className="border-t border-gray-200 bg-gray-50">
                                <td className="px-4 py-3 font-semibold text-gray-900">
                                  Total
                                </td>
                                <td className="px-4 py-3 text-right text-gray-700">
                                  {languageTotalPercent.toFixed(1)}%
                                </td>
                                <td className="px-4 py-3 text-right font-semibold text-gray-900">
                                  {formatLanguageValue(languageValuesTotal)}
                                </td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Document Analysis */}
        <TabsContent value="doc-analysis">
          <DocumentAnalysisTab
            documentAnalysis={scanData.document_analysis}
            isLoading={projectLoading}
            errorMessage={projectError}
          />
        </TabsContent>

        {/* Media Analysis */}
        <TabsContent value="media-analysis">
          <MediaAnalysisTab
            loading={projectLoading}
            error={projectError}
            mediaAnalysis={mediaAnalysis}
            onRetry={loadProject}
          />
        </TabsContent>

        {/* Skills Progress */}
        <TabsContent value="skills-progress">
          <div className="space-y-6">
            <Card className="bg-white border border-gray-200">
              <CardHeader className="border-b border-gray-200">
                <CardTitle className="text-xl font-bold text-gray-900">
                  Skill progression timeline
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
                    AI summary
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
          </div>
        </TabsContent>

        {/* Skills */}
        <TabsContent value="skills">
          <div className="space-y-6">
            <Card className="bg-white border border-gray-200">
              <CardHeader className="border-b border-gray-200">
                <CardTitle className="text-xl font-bold text-gray-900">
                  Skills analysis
                </CardTitle>
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
                      <span className="px-3 py-1 rounded-full bg-gray-100 text-gray-700 text-xs font-semibold">
                        Categories · {Object.keys(skillsByCategory).length}
                      </span>
                    </div>

                    {Object.entries(skillsByCategory).map(([category, skills]) => (
                      <div key={category} className="border border-gray-200 rounded-lg p-4">
                        <p className="text-xs font-semibold text-gray-500 uppercase">
                          {category.replace(/_/g, " ")}
                        </p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {(skills as Array<{ name: string; proficiency?: string }>).map(
                            (skill) => (
                              <span
                                key={`${category}-${skill.name}`}
                                className="px-3 py-1 rounded-full bg-gray-900 text-white text-xs"
                              >
                                {skill.name}
                                {skill.proficiency ? ` · ${formatConfidence(skill.proficiency)}` : ""}
                              </span>
                            )
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Remaining placeholders (exclude tabs we rendered above) */}
        {tabs
          .filter(
            (tab) =>
              ![
                "overview",
                "languages",
                "doc-analysis",
                "media-analysis",
                "skills-progress",
                "skills",
              ].includes(tab.value)
          )
          .map((tab) => (
            <TabsContent key={tab.value} value={tab.value}>
              <PlaceholderContent label={tab.label} />
            </TabsContent>
          ))}
      </Tabs>
      )}
    </div>
  );
}

/** ------------------ Media helpers (from feature/media-analysis) ------------------ */

function resolveMediaAnalysis(scanData: Record<string, unknown>): MediaAnalysisPayload | null {
  const aiPayload = (scanData as any).llm_media;
  if (isNonEmptyMedia(aiPayload)) {
    const normalized = normalizeMediaPayload(aiPayload);
    if (normalized) return normalized;
  }

  const localPayload = (scanData as any).media_analysis;
  if (isNonEmptyMedia(localPayload)) {
    const normalized = normalizeMediaPayload(localPayload);
    if (normalized) return normalized;
  }

  return null;
}

function isNonEmptyMedia(value: unknown): boolean {
  if (!value) return false;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "string") return value.trim().length > 0;
  if (typeof value === "object") return Object.keys(value).length > 0;
  return false;
}

function normalizeMediaPayload(value: unknown): MediaAnalysisPayload | null {
  if (!value) return null;

  if (Array.isArray(value)) {
    if (value.length === 0) return null;
    if (isStringArray(value)) return { insights: value };
    if (isObjectArray(value)) return { assetItems: mapMediaItems(value) };
    return { insights: [] };
  }

  if (typeof value === "string") return { insights: [value] };

  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    const insights: string[] = [];
    let assetItems: MediaListItem[] = [];
    let briefingItems: MediaListItem[] = [];

    if (isStringArray(record.insights)) insights.push(...record.insights);
    if (isStringArray(record.media_briefings)) insights.push(...record.media_briefings);
    else if (isObjectArray(record.media_briefings)) briefingItems = mapMediaItems(record.media_briefings);
    else if (typeof record.media_briefings === "string") insights.push(...splitLines(record.media_briefings));

    if (isStringArray(record.media_assets)) insights.push(...record.media_assets);
    else if (isObjectArray(record.media_assets)) assetItems = mapMediaItems(record.media_assets);
    else if (typeof record.media_assets === "string") insights.push(...splitLines(record.media_assets));

    if (isObjectArray(record.assetItems)) assetItems = assetItems.concat(mapMediaItems(record.assetItems));
    if (isObjectArray(record.briefingItems)) briefingItems = briefingItems.concat(mapMediaItems(record.briefingItems));

    const payload: MediaAnalysisPayload = {
      summary: isPlainObject(record.summary) ? (record.summary as MediaAnalysisSummary) : undefined,
      metrics: isPlainObject(record.metrics) ? (record.metrics as MediaAnalysisMetrics) : undefined,
      insights: insights.length > 0 ? insights : undefined,
      issues: isStringArray(record.issues) ? record.issues : undefined,
      assetItems: assetItems.length > 0 ? assetItems : undefined,
      briefingItems: briefingItems.length > 0 ? briefingItems : undefined,
    };

    const hasAny =
      payload.summary ||
      payload.metrics ||
      (payload.insights && payload.insights.length > 0) ||
      (payload.issues && payload.issues.length > 0) ||
      (payload.assetItems && payload.assetItems.length > 0) ||
      (payload.briefingItems && payload.briefingItems.length > 0);

    return hasAny ? payload : { insights: [] };
  }

  return null;
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((entry) => typeof entry === "string");
}

function isObjectArray(value: unknown): value is Array<Record<string, unknown>> {
  return (
    Array.isArray(value) &&
    value.every((entry) => entry !== null && typeof entry === "object" && !Array.isArray(entry))
  );
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function splitLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.replace(/^[•\-\s]+/, "").trim())
    .filter(Boolean);
}

function mapMediaItems(items: Array<Record<string, unknown>>): MediaListItem[] {
  return items.map((item) => ({
    label: deriveItemLabel(item),
    type: typeof item.type === "string" ? item.type : undefined,
    analysis:
      typeof item.analysis === "string"
        ? item.analysis
        : typeof item.description === "string"
        ? item.description
        : typeof item.summary === "string"
        ? item.summary
        : undefined,
    metadata: isPlainObject(item.metadata) ? item.metadata : undefined,
    path: typeof item.path === "string" ? item.path : undefined,
    file_name: typeof item.file_name === "string" ? item.file_name : undefined,
  }));
}

function deriveItemLabel(item: Record<string, unknown>): string {
  const candidates = [
    item.summary,
    item.title,
    item.path,
    item.filename,
    item.file_name,
    item.source,
    item.name,
  ];

  for (const candidate of candidates) {
    if (typeof candidate === "string" && candidate.trim().length > 0) {
      return truncateText(candidate.trim(), 120);
    }
  }

  try {
    return truncateText(JSON.stringify(item), 120);
  } catch {
    return "Media item";
  }
}

function truncateText(value: string, maxLength: number): string {
  if (value.length <= maxLength) return value;
  return `${value.slice(0, Math.max(0, maxLength - 1)).trim()}…`;
}

/** ------------------ Formatting helpers (from main) ------------------ */

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
