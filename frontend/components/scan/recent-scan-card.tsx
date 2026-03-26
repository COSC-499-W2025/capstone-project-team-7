"use client";

import React, { useState } from "react";
import Link from "next/link";
import type {
  ProjectDetail,
  ProjectScanData,
  ProjectScanLanguageEntry,
} from "@/types/project";
import {
  Activity,
  Check,
  Clock,
  Copy,
  ExternalLink,
  FileCode,
  FileText,
  Files,
  FolderOpen,
  GitBranch,
  HardDrive,
  Image,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { formatBytes } from "@/lib/format-utils";

interface RecentScanCardProps {
  project: ProjectDetail;
}

interface ContributionMetrics {
  total_commits?: number;
  total_contributors?: number;
  user_commit_share?: number;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function toFiniteNumber(value: unknown): number | undefined {
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  }

  return isFiniteNumber(value) ? value : undefined;
}
function extractLanguages(
  rawLanguages: ProjectScanData["languages"],
  projectLanguages: string[],
): string[] {
  if (Array.isArray(rawLanguages)) {
    return rawLanguages
      .map((lang) => {
        if (typeof lang === "string") return lang;
        if (lang && typeof lang === "object") {
          const entry = lang as ProjectScanLanguageEntry;
          return entry.language ?? entry.name ?? null;
        }
        return null;
      })
      .filter((lang): lang is string => Boolean(lang));
  }

  if (rawLanguages && typeof rawLanguages === "object") {
    return Object.keys(rawLanguages);
  }

  return projectLanguages;
}

function getGitRepositoryCount(raw: unknown): number {
  if (Array.isArray(raw)) {
    return raw.filter(
      (entry) => entry && typeof entry === "object" && !("error" in entry),
    ).length;
  }

  if (raw && typeof raw === "object") {
    const record = raw as Record<string, unknown>;
    const repositories = Array.isArray(record.repositories)
      ? record.repositories
      : Array.isArray(record.repos)
        ? record.repos
        : null;

    if (repositories) {
      return repositories.filter(
        (entry) => entry && typeof entry === "object" && !("error" in entry),
      ).length;
    }

    return record.error ? 0 : 1;
  }

  return 0;
}

function getMediaBreakdown(raw: unknown): { total: number; images: number; videoAudio: number } {
  if (!raw || typeof raw !== "object") {
    return { total: 0, images: 0, videoAudio: 0 };
  }

  const record = raw as Record<string, unknown>;
  const summary =
    record.summary && typeof record.summary === "object"
      ? (record.summary as Record<string, unknown>)
      : record;
  const metrics =
    record.metrics && typeof record.metrics === "object"
      ? (record.metrics as Record<string, unknown>)
      : {};
  const byType =
    summary.by_type && typeof summary.by_type === "object"
      ? (summary.by_type as Record<string, Record<string, unknown>>)
      : {};

  const imageCount = Number(
    summary.image_files ??
      byType.images?.count ??
      (metrics.images as { count?: number } | undefined)?.count ??
      0,
  );
  const audioCount = Number(
    summary.audio_files ??
      byType.audio?.count ??
      (metrics.audio as { count?: number } | undefined)?.count ??
      0,
  );
  const videoCount = Number(
    summary.video_files ??
      byType.videos?.count ??
      (metrics.video as { count?: number } | undefined)?.count ??
      0,
  );

  const totalValue = Number(
    summary.total_media_files ??
      summary.total_files ??
      (isFiniteNumber(imageCount) ? imageCount : 0) +
        (isFiniteNumber(audioCount) ? audioCount : 0) +
        (isFiniteNumber(videoCount) ? videoCount : 0),
  );

  return {
    total: isFiniteNumber(totalValue) ? totalValue : 0,
    images: isFiniteNumber(imageCount) ? imageCount : 0,
    videoAudio:
      (isFiniteNumber(audioCount) ? audioCount : 0) +
      (isFiniteNumber(videoCount) ? videoCount : 0),
  };
}

function getPdfCount(raw: unknown): number {
  if (Array.isArray(raw)) return raw.length;
  if (raw && typeof raw === "object") {
    const record = raw as Record<string, unknown>;
    if (Array.isArray(record.documents)) return record.documents.length;
    if (Array.isArray(record.items)) return record.items.length;
    if (Array.isArray(record.files)) return record.files.length;
  }
  return 0;
}

function getDocumentCount(raw: unknown): number {
  if (Array.isArray(raw)) return raw.length;
  if (raw && typeof raw === "object") {
    const record = raw as Record<string, unknown>;
    if (Array.isArray(record.documents)) return record.documents.length;
    if (Array.isArray(record.items)) return record.items.length;
    if (Array.isArray(record.files)) return record.files.length;
  }
  return 0;
}

function getContributionMetrics(
  rawMetrics: ProjectScanData["contribution_metrics"],
): ContributionMetrics | null {
  if (!rawMetrics || typeof rawMetrics !== "object") {
    return null;
  }

  const metrics = rawMetrics as Record<string, unknown>;

  return {
    total_commits: toFiniteNumber(metrics.total_commits),
    total_contributors: toFiniteNumber(metrics.total_contributors),
    user_commit_share: toFiniteNumber(metrics.user_commit_share),
  };
}
function extractLanguageMetrics(
  rawLanguages: ProjectScanData["languages"],
  projectLanguages: string[],
): Array<{ language: string; value: number }> {
  if (Array.isArray(rawLanguages)) {
    const mapped = rawLanguages
      .map((entry) => {
        if (typeof entry === "string") {
          return { language: entry, value: 1 };
        }

        if (!entry || typeof entry !== "object") {
          return null;
        }

        const languageEntry = entry as ProjectScanLanguageEntry;
        const language = languageEntry.language ?? languageEntry.name;
        if (!language) {
          return null;
        }

        return {
          language,
          value:
            languageEntry.percentage ??
            languageEntry.files ??
            languageEntry.count ??
            languageEntry.lines ??
            languageEntry.bytes ??
            1,
        };
      })
      .filter((entry): entry is { language: string; value: number } => Boolean(entry));

    if (mapped.length > 0) {
      return mapped.sort((left, right) => right.value - left.value);
    }
  }

  if (rawLanguages && typeof rawLanguages === "object") {
    const mapped = Object.entries(rawLanguages)
      .map(([language, value]) => {
        if (value && typeof value === "object") {
          const record = value as Record<string, unknown>;
          return {
            language,
            value: Number(
              record.percentage ??
                record.files ??
                record.count ??
                record.lines ??
                record.bytes ??
                1,
            ),
          };
        }

        return { language, value: 1 };
      })
      .filter((entry) => Number.isFinite(entry.value));

    if (mapped.length > 0) {
      return mapped.sort((left, right) => right.value - left.value);
    }
  }

  return projectLanguages.map((language) => ({ language, value: 1 }));
}

function getLanguageTone(language: string): string {
  switch (language.toLowerCase()) {
    case "typescript":
    case "javascript":
      return "bg-amber-50 text-amber-900 border-amber-200";
    case "python":
      return "bg-blue-50 text-blue-900 border-blue-200";
    case "markdown":
    case "md":
      return "bg-emerald-50 text-emerald-900 border-emerald-200";
    case "json":
    case "yaml":
    case "yml":
      return "bg-violet-50 text-violet-900 border-violet-200";
    case "text":
    case "txt":
      return "bg-slate-100 text-slate-800 border-slate-200";
    default:
      return "bg-slate-50 text-slate-800 border-slate-200";
  }
}

export function RecentScanCard({ project }: RecentScanCardProps) {
  const [copied, setCopied] = useState(false);

  const scanData = (project.scan_data ?? {}) as ProjectScanData;
  const summary =
    scanData.summary && typeof scanData.summary === "object"
      ? scanData.summary
      : {};
  const languages = extractLanguages(scanData.languages, project.languages ?? []);

  const totalFiles = summary.total_files || project.total_files || 0;
  const totalLines = summary.total_lines || project.total_lines || 0;
  const bytesProcessed =
    summary.bytes_processed ??
    summary.total_size_bytes ??
    summary.total_bytes ??
    0;

  const gitRepositories = getGitRepositoryCount(scanData.git_analysis);
  const mediaBreakdown = getMediaBreakdown(scanData.media_analysis ?? scanData.llm_media);
  const pdfCount = getPdfCount(scanData.pdf_analysis);
  const otherDocumentCount = getDocumentCount(scanData.document_analysis);
  const totalDocuments = pdfCount + otherDocumentCount;

  const scanDate = project.scan_timestamp
    ? new Date(project.scan_timestamp).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
      })
    : "Unknown";
  const contributionMetrics = getContributionMetrics(scanData.contribution_metrics);
  const languageMetrics = extractLanguageMetrics(scanData.languages, project.languages ?? []);
  const topLanguageMetrics = languageMetrics.slice(0, 5);
  const topLanguageTotal = topLanguageMetrics.reduce((sum, entry) => sum + entry.value, 0) || 1;
  const scanComposition = [
    { label: "Files", value: totalFiles, background: "linear-gradient(90deg, #2563eb, #22d3ee)" },
    { label: "Documents", value: totalDocuments, background: "linear-gradient(90deg, #4f46e5, #60a5fa)" },
    { label: "Media", value: mediaBreakdown.total, background: "linear-gradient(90deg, #059669, #2dd4bf)" },
    { label: "Repos", value: gitRepositories, background: "linear-gradient(90deg, #d97706, #fb923c)" },
  ];
  const maxComposition = Math.max(...scanComposition.map((entry) => entry.value), 1);

  const metrics = [
    {
      label: "Total Files",
      value: totalFiles.toLocaleString(),
      icon: Files,
      emphasis: true,
    },
    {
      label: "Lines of Code",
      value: totalLines.toLocaleString(),
      icon: FileCode,
      emphasis: false,
    },
    {
      label: "Languages",
      value: languages.length.toLocaleString(),
      icon: FileText,
      emphasis: false,
    },
    {
      label: "Project Size",
      value: formatBytes(Number(bytesProcessed) || 0),
      icon: HardDrive,
      emphasis: false,
    },
  ] as const;

  const detailCards = [
    {
      label: "Git Repositories",
      value: gitRepositories.toLocaleString(),
      icon: GitBranch,
      description:
        gitRepositories === 1 ? "Repository detected" : "Repositories detected",
      split: undefined,
    },
    {
      label: "Media Files",
      value: mediaBreakdown.total.toLocaleString(),
      icon: Image,
      description: "Images, video, and audio assets",
      split: [
        { label: "Images", value: mediaBreakdown.images.toLocaleString() },
        { label: "Video / Audio", value: mediaBreakdown.videoAudio.toLocaleString() },
      ],
    },
    {
      label: "Documents",
      value: totalDocuments.toLocaleString(),
      icon: FileText,
      description: "PDFs and document analysis files",
      split: [
        { label: "PDF files", value: pdfCount.toLocaleString() },
        { label: "Other docs", value: otherDocumentCount.toLocaleString() },
      ],
    },
  ] as const;

  const handleCopyPath = async () => {
    if (!project.project_path || typeof navigator === "undefined" || !navigator.clipboard) {
      return;
    }

    try {
      await navigator.clipboard.writeText(project.project_path);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch (error) {
      console.error("Failed to copy project path:", error);
    }
  };

  return (
    <article className="dashboard-panel dashboard-panel-interactive">
      <div className="flex flex-col gap-6 p-6 lg:p-7">
        <div className="flex flex-col gap-5 border-b border-border/70 pb-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 items-center gap-4">
            <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-2xl border border-[hsl(221_40%_83%)] bg-[linear-gradient(180deg,hsl(221_100%_98%),hsl(0_0%_100%))] text-[hsl(221_83%_53%)]">
              <FileCode className="h-6 w-6" />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="truncate text-[1.8rem] font-semibold tracking-[-0.03em] text-foreground">
                  {project.project_name}
                </h3>
                <span className="dashboard-chip bg-[hsl(221_100%_98%)] text-[hsl(221_70%_42%)] border-[hsl(221_52%_83%)]">
                  Latest scan
                </span>
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                <span className="inline-flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5" />
                  {scanDate}
                </span>
                {project.role && <span>Role: {project.role}</span>}
              </div>
            </div>
          </div>

          <Link
            href="/projects"
            className="inline-flex items-center gap-2 rounded-full border border-border bg-card/85 px-4 py-2 text-sm font-medium text-muted-foreground transition-all duration-200 hover:-translate-y-px hover:border-[hsl(221_34%_80%)] hover:text-foreground"
          >
            View All
            <ExternalLink className="h-4 w-4" />
          </Link>
        </div>

        <div className="dashboard-stat-grid">
          {metrics.map((metric) => {
            const Icon = metric.icon;
            return (
              <div
                key={metric.label}
                className={cn("dashboard-stat", metric.emphasis && "dashboard-stat-primary")}
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                    {metric.label}
                  </p>
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-card/80 text-muted-foreground">
                    <Icon className="size-[1.125rem]" />
                  </div>
                </div>
                <div>
                  <p className={cn("text-3xl font-semibold tracking-[-0.04em] text-foreground", metric.emphasis && "text-[2.35rem]")}>
                    {metric.value}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {metric.label === "Total Files"
                      ? "Processed in the latest scan"
                      : metric.label === "Lines of Code"
                        ? "Detected across project files"
                        : metric.label === "Languages"
                          ? "Recognized across the codebase"
                          : "Total indexed payload size"}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        <div className="grid gap-5 lg:grid-cols-[minmax(0,0.78fr)_minmax(0,1.22fr)]">
          <section className="dashboard-card-subtle p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                  Languages
                </p>
                <h4 className="mt-2 text-lg font-semibold tracking-[-0.02em] text-foreground">
                  Languages detected
                </h4>
              </div>
              <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
                {languages.length}
              </span>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              {languages.length > 0 ? (
                <>
                  {languages.slice(0, 10).map((language) => (
                    <span
                      key={language}
                      className={cn(
                        "inline-flex items-center rounded-full border px-3 py-1.5 text-xs font-medium transition-transform duration-200 hover:-translate-y-px",
                        getLanguageTone(language),
                      )}
                    >
                      {language}
                    </span>
                  ))}
                  {languages.length > 10 && (
                    <span className="dashboard-chip">+{languages.length - 10} more</span>
                  )}
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No language metadata was included in this scan.
                </p>
              )}
            </div>
          </section>

          <section className="dashboard-card-subtle p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                  Project Path
                </p>
                <h4 className="mt-2 text-lg font-semibold tracking-[-0.02em] text-foreground">
                  Source location
                </h4>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopyPath}
                className="h-9 rounded-full border border-border bg-card/80 px-3 text-xs font-medium hover:border-[hsl(221_34%_80%)]"
              >
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                <span>{copied ? "Copied" : "Copy path"}</span>
              </Button>
            </div>

            <div className="mt-4">
              <div className="dashboard-codeblock">
                <FolderOpen className="size-[1.125rem] flex-shrink-0 text-muted-foreground" />
                <code className="min-w-0 break-all font-mono text-[13px] leading-6">
                  {project.project_path || "Path unavailable"}
                </code>
              </div>
            </div>
          </section>
        </div>

        <div className="grid gap-5 xl:grid-cols-[minmax(0,0.88fr)_minmax(0,1.12fr)_minmax(320px,0.8fr)]">
          <section className="dashboard-card-subtle p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                  Scan Summary
                </p>
                <h4 className="mt-2 text-lg font-semibold tracking-[-0.02em] text-foreground">
                  Composition
                </h4>
              </div>
              <Activity className="size-[1.125rem] text-muted-foreground" />
            </div>

            <div className="mt-5 space-y-3">
              {scanComposition.map((entry) => (
                <div key={entry.label} className="space-y-2">
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <span className="font-medium text-foreground">{entry.label}</span>
                    <span className="text-muted-foreground">{entry.value.toLocaleString()}</span>
                  </div>
                  <div className="metric-bar">
                    <div
                      className="metric-bar-fill"
                      style={{
                        width: `${Math.max((entry.value / maxComposition) * 100, entry.value > 0 ? 16 : 0)}%`,
                        background: entry.background,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="dashboard-card-subtle p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                  Language Breakdown
                </p>
                <h4 className="mt-2 text-lg font-semibold tracking-[-0.02em] text-foreground">
                  Dominant languages
                </h4>
              </div>
              <span className="rounded-full bg-card/80 px-2.5 py-1 text-xs font-medium text-muted-foreground">
                {topLanguageMetrics.length || 0} shown
              </span>
            </div>

            <div className="mt-5 space-y-3">
              {topLanguageMetrics.length > 0 ? (
                topLanguageMetrics.map((entry) => (
                  <div key={entry.language} className="space-y-2">
                    <div className="flex items-center justify-between gap-3 text-sm">
                      <span className="font-medium text-foreground">{entry.language}</span>
                      <span className="text-muted-foreground">
                        {Math.round((entry.value / topLanguageTotal) * 100)}%
                      </span>
                    </div>
                    <div className="metric-bar">
                      <div
                        className="metric-bar-fill"
                        style={{ width: `${Math.max((entry.value / topLanguageTotal) * 100, 10)}%` }}
                      />
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">
                  No structured language metrics were included in this scan.
                </p>
              )}
            </div>
          </section>

          <section className="dashboard-card-subtle p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                  Activity Signal
                </p>
                <h4 className="mt-2 text-lg font-semibold tracking-[-0.02em] text-foreground">
                  Contribution snapshot
                </h4>
              </div>
              <Users className="size-[1.125rem] text-muted-foreground" />
            </div>

            <div className="mt-5 grid gap-3">
              <div className="rounded-[18px] border border-border bg-card/80 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Total commits
                </p>
                <p className="mt-2 text-[1.85rem] font-semibold tracking-[-0.04em] text-foreground">
                  {Number(contributionMetrics?.total_commits ?? 0).toLocaleString()}
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-[18px] border border-border bg-card/80 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                    Contributors
                  </p>
                  <p className="mt-2 text-xl font-semibold tracking-[-0.03em] text-foreground">
                    {Number(contributionMetrics?.total_contributors ?? 0).toLocaleString()}
                  </p>
                </div>
                <div className="rounded-[18px] border border-border bg-card/80 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                    Your share
                  </p>
                  <p className="mt-2 text-xl font-semibold tracking-[-0.03em] text-foreground">
                    {contributionMetrics?.user_commit_share != null
                      ? `${Math.round(contributionMetrics.user_commit_share * 100)}%`
                      : "N/A"}
                  </p>
                </div>
              </div>
              <p className="text-xs leading-5 text-muted-foreground">
                Activity metrics appear here when contribution analysis is available in the latest scan.
              </p>
            </div>
          </section>
        </div>

        <div className="dashboard-summary-grid">
          {detailCards.map((card) => {
            const Icon = card.icon;
            return (
              <section key={card.label} className="dashboard-summary-card">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                      {card.label}
                    </p>
                    <p className="mt-3 text-[2rem] font-semibold tracking-[-0.04em] text-foreground">
                      {card.value}
                    </p>
                  </div>
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-[hsl(220_18%_82%)] bg-[linear-gradient(180deg,hsl(220_20%_93%),hsl(220_16%_88%))] text-[hsl(220_11%_53%)] shadow-[inset_0_1px_0_rgba(255,255,255,0.72)] dark:border-white/10 dark:bg-[linear-gradient(180deg,hsl(223_12%_25%),hsl(223_11%_21%))] dark:text-[hsl(220_14%_72%)] dark:shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
                    <Icon className="size-[1.125rem]" />
                  </div>
                </div>

                <p className="text-sm text-muted-foreground">{card.description}</p>

                {card.split && (
                  <div className="dashboard-summary-metric">
                    {card.split.map((item) => (
                      <div key={item.label} className="dashboard-summary-kv">
                        <p className="text-lg font-semibold tracking-[-0.03em] text-foreground">
                          {item.value}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">{item.label}</p>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            );
          })}
        </div>
      </div>
    </article>
  );
}
