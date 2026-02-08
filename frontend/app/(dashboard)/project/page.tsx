"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import {
  MediaAnalysisTab,
  type MediaAnalysisPayload,
  type MediaAnalysisMetrics,
  type MediaAnalysisSummary,
  type MediaListItem,
} from "@/components/project/media-analysis-tab";
import { getProjects, getProjectById } from "@/lib/api/projects";
import { getStoredToken } from "@/lib/auth";
import type { ProjectDetail } from "@/types/project";
import {
  LayoutDashboard,
  FileText,
  BarChart3,
  Code2,
  Award,
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
  const searchParams = useSearchParams();
  const projectIdParam = searchParams.get("projectId");
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loadingProject, setLoadingProject] = useState(true);
  const [projectError, setProjectError] = useState<string | null>(null);
  const isMountedRef = useRef(true);

  const loadProject = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      if (isMountedRef.current) {
        setProjectError("Not authenticated. Please log in through Settings.");
        setLoadingProject(false);
      }
      return;
    }

    try {
      setProjectError(null);
      setLoadingProject(true);

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
        const message = err instanceof Error ? err.message : "Failed to load project";
        setProjectError(message);
      }
    } finally {
      if (isMountedRef.current) setLoadingProject(false);
    }
  }, [projectIdParam]);

  useEffect(() => {
    isMountedRef.current = true;
    loadProject();
    return () => {
      isMountedRef.current = false;
    };
  }, [loadProject]);

  const mediaAnalysis = useMemo<MediaAnalysisPayload | null>(() => {
    if (!project?.scan_data) return null;
    const scanData = project.scan_data as Record<string, unknown>;
    return resolveMediaAnalysis(scanData);
  }, [project]);

  const headerTitle = project?.project_name ?? "Project Analysis";
  // TODO: wire project path into header detail when the overall page is data-driven

  return (
    <div className="p-8">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 mb-6">
        <Link href={"/scanned-results" as any} className="text-sm text-gray-600 hover:text-gray-900 mb-2 inline-block">
          ← Back
        </Link>
        <h1 className="text-4xl font-bold text-gray-900 tracking-tight">
          {project ? `Project: ${project.project_name}` : headerTitle}
        </h1>
        <p className="text-gray-500 mt-1 text-sm">Scanned project analysis and reports</p>
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
                    <p className="text-sm font-semibold text-gray-900 mt-1">My Capstone App</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Path</p>
                    <p className="text-sm font-mono text-gray-900 mt-1">/home/user/projects/capstone-app</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Scan Timestamp</p>
                    <p className="text-sm text-gray-900 mt-1">2025-01-15 14:32:07</p>
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
                    <p className="text-2xl font-bold text-gray-900">247</p>
                    <p className="text-xs text-gray-500 mt-1">Files Processed</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-gray-900">4.8 MB</p>
                    <p className="text-xs text-gray-500 mt-1">Total Size</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-gray-900">12</p>
                    <p className="text-xs text-gray-500 mt-1">Issues Found</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-gray-900">18,432</p>
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
                  {overviewLanguages.map((lang) => (
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
                  <p className="text-3xl font-bold text-gray-900">2</p>
                  <p className="text-xs text-gray-500 mt-1">Repositories detected</p>
                </CardContent>
              </Card>

              <Card className="bg-white border border-gray-200">
                <CardHeader className="border-b border-gray-200">
                  <CardTitle className="text-base font-bold text-gray-900">Media Files</CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <p className="text-3xl font-bold text-gray-900">15</p>
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
                      <p className="text-3xl font-bold text-gray-900">3</p>
                      <p className="text-xs text-gray-500 mt-1">PDF files</p>
                    </div>
                    <div>
                      <p className="text-3xl font-bold text-gray-900">8</p>
                      <p className="text-xs text-gray-500 mt-1">Other docs</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* Placeholder tabs */}
        {tabs.slice(1).map((tab) => {
          if (tab.value === "media-analysis") {
            return (
              <TabsContent key={tab.value} value={tab.value}>
                <MediaAnalysisTab
                  loading={loadingProject}
                  error={projectError}
                  mediaAnalysis={mediaAnalysis}
                  onRetry={loadProject}
                />
              </TabsContent>
            );
          }
          return (
            <TabsContent key={tab.value} value={tab.value}>
              <PlaceholderContent label={tab.label} />
            </TabsContent>
          );
        })}
      </Tabs>
    </div>
  );
}

function resolveMediaAnalysis(scanData: Record<string, unknown>): MediaAnalysisPayload | null {
  const aiPayload = scanData.llm_media;
  if (isNonEmptyMedia(aiPayload)) {
    const normalized = normalizeMediaPayload(aiPayload);
    if (normalized) return normalized;
  }

  const localPayload = scanData.media_analysis;
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

export function normalizeMediaPayload(value: unknown): MediaAnalysisPayload | null {
  if (!value) return null;

  if (Array.isArray(value)) {
    if (value.length === 0) return null;
    if (isStringArray(value)) {
      return { insights: value };
    }
    if (isObjectArray(value)) {
      return { assetItems: mapMediaItems(value) };
    }
    return { insights: [] };
  }

  if (typeof value === "string") {
    return { insights: [value] };
  }

  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    const insights: string[] = [];
    let assetItems: MediaListItem[] = [];
    let briefingItems: MediaListItem[] = [];

    if (isStringArray(record.insights)) {
      insights.push(...record.insights);
    }
    if (isStringArray(record.issues)) {
      // handled later
    }

    if (isStringArray(record.media_briefings)) {
      insights.push(...record.media_briefings);
    } else if (isObjectArray(record.media_briefings)) {
      briefingItems = mapMediaItems(record.media_briefings);
    } else if (typeof record.media_briefings === "string") {
      insights.push(...splitLines(record.media_briefings));
    }

    if (isStringArray(record.media_assets)) {
      insights.push(...record.media_assets);
    } else if (isObjectArray(record.media_assets)) {
      assetItems = mapMediaItems(record.media_assets);
    } else if (typeof record.media_assets === "string") {
      insights.push(...splitLines(record.media_assets));
    }

    if (isObjectArray(record.assetItems)) {
      assetItems = assetItems.concat(mapMediaItems(record.assetItems));
    }
    if (isObjectArray(record.briefingItems)) {
      briefingItems = briefingItems.concat(mapMediaItems(record.briefingItems));
    }

    const payload: MediaAnalysisPayload = {
      summary: isPlainObject(record.summary)
        ? (record.summary as MediaAnalysisSummary)
        : undefined,
      metrics: isPlainObject(record.metrics)
        ? (record.metrics as MediaAnalysisMetrics)
        : undefined,
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
    value.every(
      (entry) =>
        entry !== null &&
        typeof entry === "object" &&
        !Array.isArray(entry)
    )
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
