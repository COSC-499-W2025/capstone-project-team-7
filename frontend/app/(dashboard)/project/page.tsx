"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { getStoredToken } from "@/lib/auth";
import {
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

const overviewLanguages = [
  { name: "TypeScript", percentage: 42.3 },
  { name: "Python", percentage: 28.1 },
  { name: "JavaScript", percentage: 15.7 },
  { name: "CSS", percentage: 8.4 },
  { name: "HTML", percentage: 5.5 },
];

const fallbackProject = {
  name: "My Capstone App",
  path: "/home/user/projects/capstone-app",
  scanTimestamp: "2025-01-15 14:32:07",
  filesProcessed: 247,
  totalSizeLabel: "4.8 MB",
  issuesFound: 12,
  totalLines: 18432,
  gitRepos: 2,
  mediaFiles: 15,
  pdfDocs: 3,
  otherDocs: 8,
};

function PlaceholderContent({ label }: { label: string }) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardContent className="p-12 text-center">
        <p className="text-gray-500 text-sm">{label} — This section will be available soon.</p>
      </CardContent>
    </Card>
  );
}


export default function ProjectPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [projectError, setProjectError] = useState<string | null>(null);
  const [projectLoading, setProjectLoading] = useState(false);

  const [skillsTimeline, setSkillsTimeline] = useState<SkillProgressPeriod[]>([]);
  const [skillsSummary, setSkillsSummary] = useState<SkillProgressSummary | null>(null);
  const [skillsNote, setSkillsNote] = useState<string | null>(null);
  const [skillsLoading, setSkillsLoading] = useState(false);
  const [summaryLoading, setSummaryLoading] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const id = params.get("projectId");
    setProjectId(id);
  }, []);

  useEffect(() => {
    if (!projectId) return;
    const token = getStoredToken();
    if (!token) {
      setProjectError("Not authenticated. Please log in through Settings.");
      return;
    }

    let cancelled = false;
    setProjectLoading(true);
    setProjectError(null);
    getProjectById(token, projectId)
      .then((data) => {
        if (cancelled) return;
        setProject(data);
      })
      .catch((err) => {
        if (cancelled) return;
        setProjectError(err instanceof Error ? err.message : "Failed to load project.");
      })
      .finally(() => {
        if (!cancelled) setProjectLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [projectId]);

  useEffect(() => {
    if (!projectId) return;
    const token = getStoredToken();
    if (!token) return;

    let cancelled = false;
    setSkillsLoading(true);
    setSkillsNote(null);
    getProjectSkillTimeline(token, projectId)
      .then((data) => {
        if (cancelled) return;
        setSkillsTimeline(data.timeline || []);
        setSkillsSummary(data.summary ?? null);
        setSkillsNote(data.note ?? null);
      })
      .catch((err) => {
        if (cancelled) return;
        setSkillsNote(err instanceof Error ? err.message : "Failed to load skills timeline.");
      })
      .finally(() => {
        if (!cancelled) setSkillsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const scanData = project?.scan_data || {};
  const summary = scanData.summary || {};
  const skillsAnalysis = scanData.skills_analysis || {};
  const skillsByCategory = skillsAnalysis.skills_by_category || {};
  const totalSkills = skillsAnalysis.total_skills || 0;

  const projectName = project?.project_name ?? fallbackProject.name;
  const projectPath = project?.project_path ?? fallbackProject.path;
  const scanTimestamp = project?.scan_timestamp ?? fallbackProject.scanTimestamp;

  const filesProcessed = summary.total_files ?? project?.total_files ?? fallbackProject.filesProcessed;
  const totalSizeBytes = summary.bytes_processed;
  const issuesFound = summary.issues_found ?? summary.issue_count ?? fallbackProject.issuesFound;
  const totalLines = summary.total_lines ?? project?.total_lines ?? fallbackProject.totalLines;
  const filesProcessedLabel = formatCount(filesProcessed);
  const issuesFoundLabel = formatCount(issuesFound);
  const totalLinesLabel = formatCount(totalLines);

  const languageStats = useMemo(() => {
    const rawLanguages = scanData.languages;
    if (!rawLanguages || typeof rawLanguages !== "object") {
      return null;
    }

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

    const total = entries.reduce((sum, entry) => sum + entry.value, 0);
    if (total <= 0) return null;
    return entries
      .map((entry) => ({
        name: entry.name,
        percentage: Number(((entry.value / total) * 100).toFixed(1)),
      }))
      .sort((a, b) => b.percentage - a.percentage)
      .slice(0, 5);
  }, [scanData.languages]);

  const topLanguages = languageStats ?? overviewLanguages;

  const gitRepos = scanData.git_analysis?.repositories?.length ?? fallbackProject.gitRepos;
  const mediaFiles = scanData.media_analysis?.length ?? fallbackProject.mediaFiles;
  const pdfDocs = scanData.pdf_analysis?.length ?? fallbackProject.pdfDocs;
  const otherDocs = scanData.documents_analysis?.length ?? fallbackProject.otherDocs;

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
    if (!projectId) return;
    const token = getStoredToken();
    if (!token) {
      setSkillsNote("Not authenticated. Please log in through Settings.");
      return;
    }

    setSummaryLoading(true);
    try {
      const response = await generateProjectSkillSummary(token, projectId);
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
        <Link href={"/scanned-results" as any} className="text-sm text-gray-600 hover:text-gray-900 mb-2 inline-block">
          ← Back
        </Link>
        <h1 className="text-4xl font-bold text-gray-900 tracking-tight">Project: {projectName}</h1>
        <p className="text-gray-500 mt-1 text-sm">Scanned project analysis and reports</p>
        {projectLoading && (
          <p className="text-xs text-gray-400 mt-2">Loading project data…</p>
        )}
        {projectError && (
          <p className="text-xs text-red-600 mt-2">{projectError}</p>
        )}
      </div>

      <Tabs defaultValue="overview">
        <TabsList className="flex justify-start overflow-x-auto gap-1 h-auto bg-gray-100 rounded-lg p-1.5 scrollbar-thin">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <TabsTrigger key={tab.value} value={tab.value} className="gap-1.5 text-xs px-2.5 py-1.5 shrink-0">
                <Icon size={14} />
                {tab.label}
              </TabsTrigger>
            );
          })}
        </TabsList>

        {/* Overview tab with real content */}
        <TabsContent value="overview">
          <div className="space-y-6">
            {/* Project Info */}
            <Card className="bg-white border border-gray-200">
              <CardHeader className="border-b border-gray-200">
                <CardTitle className="text-xl font-bold text-gray-900">Project Information</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Project Name</p>
                    <p className="text-sm font-semibold text-gray-900 mt-1">{projectName}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Path</p>
                    <p className="text-sm font-mono text-gray-900 mt-1">{projectPath}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Scan Timestamp</p>
                    <p className="text-sm text-gray-900 mt-1">{scanTimestamp}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Scan Duration</p>
                    <p className="text-sm text-gray-900 mt-1">3.2 seconds</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Summary Stats */}
            <Card className="bg-white border border-gray-200">
              <CardHeader className="border-b border-gray-200">
                <CardTitle className="text-xl font-bold text-gray-900">Summary Statistics</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                  <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-gray-900">{filesProcessedLabel}</p>
                    <p className="text-xs text-gray-500 mt-1">Files Processed</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-gray-900">
                      {totalSizeBytes ? formatBytes(Number(totalSizeBytes)) : fallbackProject.totalSizeLabel}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Total Size</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-gray-900">{issuesFoundLabel}</p>
                    <p className="text-xs text-gray-500 mt-1">Issues Found</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-gray-900">{totalLinesLabel}</p>
                    <p className="text-xs text-gray-500 mt-1">Lines of Code</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Top Languages */}
            <Card className="bg-white border border-gray-200">
              <CardHeader className="border-b border-gray-200">
                <CardTitle className="text-xl font-bold text-gray-900">Top 5 Languages</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="space-y-3">
                  {topLanguages.map((lang) => (
                    <div key={lang.name} className="flex items-center gap-3">
                      <span className="text-sm text-gray-900 w-28 font-medium">{lang.name}</span>
                      <div className="flex-1 bg-gray-100 rounded-full h-2.5">
                        <div
                          className="bg-gray-900 h-2.5 rounded-full"
                          style={{ width: `${lang.percentage}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-500 w-14 text-right">{lang.percentage}%</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Additional Counts */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card className="bg-white border border-gray-200">
                <CardHeader className="border-b border-gray-200">
                  <CardTitle className="text-base font-bold text-gray-900">Git Repositories</CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <p className="text-3xl font-bold text-gray-900">{gitRepos}</p>
                  <p className="text-xs text-gray-500 mt-1">Repositories detected</p>
                </CardContent>
              </Card>

              <Card className="bg-white border border-gray-200">
                <CardHeader className="border-b border-gray-200">
                  <CardTitle className="text-base font-bold text-gray-900">Media Files</CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <p className="text-3xl font-bold text-gray-900">{mediaFiles}</p>
                  <p className="text-xs text-gray-500 mt-1">Images, videos, and audio</p>
                </CardContent>
              </Card>

              <Card className="bg-white border border-gray-200">
                <CardHeader className="border-b border-gray-200">
                  <CardTitle className="text-base font-bold text-gray-900">Documents</CardTitle>
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

        <TabsContent value="skills-progress">
          <div className="space-y-6">
            <Card className="bg-white border border-gray-200">
              <CardHeader className="border-b border-gray-200">
                <CardTitle className="text-xl font-bold text-gray-900">Skill progression timeline</CardTitle>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                {skillsLoading && (
                  <p className="text-sm text-gray-500">Loading skill progression…</p>
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
                        <span className="text-xs text-gray-400">No top skills yet.</span>
                      )}
                    </div>

                    <div className="grid gap-4">
                      {skillsTimeline.map((period) => (
                        <div key={period.period_label} className="rounded-xl border border-gray-200 p-4">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                              <h4 className="text-base font-semibold text-gray-900">
                                {formatPeriodLabel(period.period_label)}
                              </h4>
                              <p className="text-xs text-gray-500">{period.period_label}</p>
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
                              <span className="text-xs text-gray-400">No activity labels</span>
                            )}
                          </div>

                          <div className="mt-4 grid gap-4 md:grid-cols-2">
                            <div>
                              <p className="text-xs font-semibold text-gray-500 uppercase">Top skills</p>
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
                                  <span className="text-xs text-gray-400">No skills recorded</span>
                                )}
                              </div>
                            </div>
                            <div>
                              <p className="text-xs font-semibold text-gray-500 uppercase">Languages</p>
                              <div className="mt-2 flex flex-wrap gap-2">
                                {Object.keys(period.period_languages).length > 0 ? (
                                  Object.entries(period.period_languages).map(([lang, count]) => (
                                    <span
                                      key={lang}
                                      className="px-2.5 py-1 rounded-full bg-gray-100 text-gray-700 text-xs"
                                    >
                                      {lang} · {count}
                                    </span>
                                  ))
                                ) : (
                                  <span className="text-xs text-gray-400">No language data</span>
                                )}
                              </div>
                            </div>
                          </div>

                          <div className="mt-4 grid gap-4 md:grid-cols-2">
                            <div>
                              <p className="text-xs font-semibold text-gray-500 uppercase">Recent commits</p>
                              <ul className="mt-2 space-y-1 text-sm text-gray-700">
                                {period.commit_messages.slice(0, 4).map((msg, index) => (
                                  <li key={`${period.period_label}-commit-${index}`} className="truncate">
                                    {msg}
                                  </li>
                                ))}
                                {period.commit_messages.length === 0 && (
                                  <li className="text-xs text-gray-400">No commit messages recorded.</li>
                                )}
                              </ul>
                            </div>
                            <div>
                              <p className="text-xs font-semibold text-gray-500 uppercase">Files touched</p>
                              <ul className="mt-2 space-y-1 text-sm text-gray-700">
                                {period.top_files.slice(0, 4).map((file, index) => (
                                  <li key={`${period.period_label}-file-${index}`} className="truncate">
                                    {file}
                                  </li>
                                ))}
                                {period.top_files.length === 0 && (
                                  <li className="text-xs text-gray-400">No file highlights recorded.</li>
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
                  <CardTitle className="text-xl font-bold text-gray-900">AI summary</CardTitle>
                  <p className="text-xs text-gray-500 mt-1">Summarize skill growth from the timeline.</p>
                </div>
                <button
                  onClick={handleGenerateSummary}
                  disabled={summaryLoading}
                  className="px-3 py-2 text-xs font-semibold rounded-md bg-gray-900 text-white disabled:opacity-60"
                >
                  {summaryLoading ? "Generating…" : skillsSummary ? "Regenerate" : "Generate"}
                </button>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                {skillsNote && <p className="text-sm text-gray-500">{skillsNote}</p>}
                {skillsSummary && (
                  <div className="space-y-4">
                    <div>
                      <p className="text-sm font-semibold text-gray-700">Overview</p>
                      <p className="text-sm text-gray-700 mt-1">{skillsSummary.overview}</p>
                      {skillsSummary.validation_warning && (
                        <p className="text-xs text-amber-600 mt-2">{skillsSummary.validation_warning}</p>
                      )}
                    </div>
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <p className="text-sm font-semibold text-gray-700">Timeline highlights</p>
                        <ul className="mt-2 space-y-1 text-sm text-gray-700 list-disc list-inside">
                          {skillsSummary.timeline.map((item, index) => (
                            <li key={`timeline-${index}`}>{item}</li>
                          ))}
                          {skillsSummary.timeline.length === 0 && (
                            <li className="text-xs text-gray-400">No timeline highlights.</li>
                          )}
                        </ul>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-700">Skills focus</p>
                        <ul className="mt-2 space-y-1 text-sm text-gray-700 list-disc list-inside">
                          {skillsSummary.skills_focus.map((item, index) => (
                            <li key={`skills-${index}`}>{item}</li>
                          ))}
                          {skillsSummary.skills_focus.length === 0 && (
                            <li className="text-xs text-gray-400">No skill focus notes.</li>
                          )}
                        </ul>
                      </div>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-gray-700">Suggested next steps</p>
                      <ul className="mt-2 space-y-1 text-sm text-gray-700 list-disc list-inside">
                        {skillsSummary.suggested_next_steps.map((item, index) => (
                          <li key={`steps-${index}`}>{item}</li>
                        ))}
                        {skillsSummary.suggested_next_steps.length === 0 && (
                          <li className="text-xs text-gray-400">No suggestions yet.</li>
                        )}
                      </ul>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="skills">
          <div className="space-y-6">
            <Card className="bg-white border border-gray-200">
              <CardHeader className="border-b border-gray-200">
                <CardTitle className="text-xl font-bold text-gray-900">Skills analysis</CardTitle>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                {skillsAnalysis.success === false && (
                  <p className="text-sm text-gray-500">
                    Skills analysis did not complete for this scan.
                  </p>
                )}
                {skillsAnalysis.success !== false && Object.keys(skillsByCategory).length === 0 && (
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
                          {(skills as Array<{ name: string; proficiency?: string }>).map((skill) => (
                            <span
                              key={`${category}-${skill.name}`}
                              className="px-3 py-1 rounded-full bg-gray-900 text-white text-xs"
                            >
                              {skill.name}
                              {skill.proficiency ? ` · ${skill.proficiency}` : ""}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Placeholder tabs */}
        {tabs
          .filter((tab) => !["overview", "skills-progress", "skills"].includes(tab.value))
          .map((tab) => (
            <TabsContent key={tab.value} value={tab.value}>
              <PlaceholderContent label={tab.label} />
            </TabsContent>
          ))}
      </Tabs>
    </div>
  );
}

function formatPeriodLabel(value: string) {
  const [year, month] = value.split("-");
  if (!year || !month) return value;
  const date = new Date(Number(year), Number(month) - 1, 1);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short" });
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
