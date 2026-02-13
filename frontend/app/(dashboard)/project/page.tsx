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
} from "lucide-react";

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
  { value: "code-analysis", label: "Code Analysis", icon: Code2 },
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

  const languageStats = useMemo(() => {
    const rawLanguages = scanData.languages;
    if (!rawLanguages || typeof rawLanguages !== "object") return null;

    const entries: Array<{ name: string; value: number }> = [];

    if (Array.isArray(rawLanguages)) {
      if (rawLanguages.length > 0 && typeof rawLanguages[0] === "object") {
        rawLanguages.forEach((lang: any) => {
          const name = lang.language || lang.name;
          const value = Number(lang.percentage ?? lang.lines ?? lang.files ?? 0);
          if (name) entries.push({ name, value });
        });
      } else {
        rawLanguages.forEach((lang: any) => {
          if (typeof lang === "string") entries.push({ name: lang, value: 1 });
        });
      }
    } else {
      Object.entries(rawLanguages).forEach(([name, data]) => {
        if (!name) return;
        if (typeof data === "number") {
          entries.push({ name, value: data });
          return;
        }
        const metric = data as Record<string, number>;
        const value = Number(metric.lines ?? metric.files ?? metric.bytes ?? 0);
        entries.push({ name, value });
      });
    }

    const total = entries.reduce((sum, e) => sum + e.value, 0);
    if (total <= 0) return null;

    return entries
      .map((e) => ({
        name: e.name,
        percentage: Number(((e.value / total) * 100).toFixed(1)),
      }))
      .sort((a, b) => b.percentage - a.percentage)
      .slice(0, 5);
  }, [scanData.languages]);

  const topLanguages: Array<{ name: string; percentage: number }> = languageStats ?? [];

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

              {/* Code Analysis */}
              <TabsContent value="code-analysis">
                <Card className="bg-white border border-gray-200">
                  <CardHeader className="border-b border-gray-200">
                    <CardTitle className="text-xl font-bold text-gray-900">
                      Code Analysis
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {!scanData.code_analysis || scanData.code_analysis.success === false ? (
                      <p className="text-sm text-gray-500">
                        No code analysis data available for this project.
                      </p>
                    ) : (
                      <div className="space-y-6">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div className="bg-gray-50 rounded-lg p-4 text-center">
                            <p className="text-2xl font-bold text-gray-900">
                              {scanData.code_analysis.total_files ?? 0}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">Files Analyzed</p>
                          </div>
                          <div className="bg-gray-50 rounded-lg p-4 text-center">
                            <p className="text-2xl font-bold text-gray-900">
                              {Object.keys(scanData.code_analysis.languages ?? {}).length}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">Languages</p>
                          </div>
                          <div className="bg-gray-50 rounded-lg p-4 text-center">
                            <p className="text-2xl font-bold text-gray-900">
                              {scanData.code_analysis.metrics?.total_lines?.toLocaleString() ?? "—"}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">Total Lines</p>
                          </div>
                          <div className="bg-gray-50 rounded-lg p-4 text-center">
                            <p className="text-2xl font-bold text-gray-900">
                              {scanData.code_analysis.quality?.avg_maintainability?.toFixed(0) ?? "—"}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">Maintainability</p>
                          </div>
                        </div>

                        {scanData.code_analysis.refactor_candidates && 
                         scanData.code_analysis.refactor_candidates.length > 0 && (
                          <div>
                            <h4 className="text-sm font-semibold text-gray-900 mb-3">
                              Refactor Candidates ({scanData.code_analysis.refactor_candidates.length})
                            </h4>
                            <div className="space-y-2">
                              {scanData.code_analysis.refactor_candidates.slice(0, 5).map((candidate: { path: string; reason?: string }, idx: number) => (
                                <div key={idx} className="flex items-start gap-2 text-sm">
                                  <Code2 size={14} className="text-gray-400 mt-0.5 flex-shrink-0" />
                                  <div>
                                    <span className="font-mono text-gray-900">{candidate.path}</span>
                                    {candidate.reason && (
                                      <span className="text-gray-500 ml-2">— {candidate.reason}</span>
                                    )}
                                  </div>
                                </div>
                              ))}
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
                <Card className="bg-white border border-gray-200">
                  <CardHeader className="border-b border-gray-200">
                    <CardTitle className="text-xl font-bold text-gray-900">
                      Skills Analysis
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
                              {scanData.contribution_metrics.contributors.slice(0, 5).map((contributor: { name: string; commits: number; commit_percentage?: number }, idx: number) => (
                                <div key={idx} className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <Users size={14} className="text-gray-400" />
                                    <span className="text-sm font-medium text-gray-900">{contributor.name}</span>
                                  </div>
                                  <div className="text-sm text-gray-500">
                                    {contributor.commits} commits
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

              {/* Media */}
              <TabsContent value="media">
                <MediaAnalysisTab
                  loading={projectLoading}
                  error={projectError}
                  mediaAnalysis={mediaAnalysis}
                  onRetry={loadProject}
                />
              </TabsContent>

              {/* PDFs Placeholder */}
              <TabsContent value="pdfs">
                <PlaceholderContent label="PDF Analysis" />
              </TabsContent>
            </Tabs>
          </TabsContent>

          {/* ============================================
              TAB 4: TOOLS & EXPORT
          ============================================ */}
          <TabsContent value="tools">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* File Browser */}
              <Card className="bg-white border border-gray-200">
                <CardHeader className="border-b border-gray-200">
                  <CardTitle className="text-base font-bold text-gray-900 flex items-center gap-2">
                    <FileText size={18} />
                    File Browser
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <p className="text-sm text-gray-500 mb-4">
                    Browse and view all files in the project.
                  </p>
                  <PlaceholderContent label="File Browser" />
                </CardContent>
              </Card>

              {/* Git Analysis */}
              <Card className="bg-white border border-gray-200">
                <CardHeader className="border-b border-gray-200">
                  <CardTitle className="text-base font-bold text-gray-900 flex items-center gap-2">
                    <GitBranch size={18} />
                    Git Analysis
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <p className="text-sm text-gray-500 mb-4">
                    Analyze git history, branches, and commits.
                  </p>
                  <PlaceholderContent label="Git Analysis" />
                </CardContent>
              </Card>

              {/* Duplicate Finder */}
              <Card className="bg-white border border-gray-200">
                <CardHeader className="border-b border-gray-200">
                  <CardTitle className="text-base font-bold text-gray-900 flex items-center gap-2">
                    <Copy size={18} />
                    Duplicate Finder
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <p className="text-sm text-gray-500 mb-4">
                    Find and manage duplicate files across the project.
                  </p>
                  <PlaceholderContent label="Duplicate Finder" />
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
                    Advanced search and filtering across all project files.
                  </p>
                  <PlaceholderContent label="Search & Filter" />
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
                    <button
                      disabled
                      className="px-3 py-2 text-xs font-semibold rounded-md bg-gray-100 text-gray-400 cursor-not-allowed flex items-center gap-1"
                    >
                      <FileJson size={14} />
                      Export JSON
                    </button>
                    <button
                      disabled
                      className="px-3 py-2 text-xs font-semibold rounded-md bg-gray-100 text-gray-400 cursor-not-allowed flex items-center gap-1"
                    >
                      <FileCode2 size={14} />
                      Export HTML
                    </button>
                    <button
                      disabled
                      className="px-3 py-2 text-xs font-semibold rounded-md bg-gray-100 text-gray-400 cursor-not-allowed flex items-center gap-1"
                    >
                      <Printer size={14} />
                      Print
                    </button>
                  </div>
                  <p className="text-xs text-gray-400 mt-2">Export features coming soon.</p>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
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
