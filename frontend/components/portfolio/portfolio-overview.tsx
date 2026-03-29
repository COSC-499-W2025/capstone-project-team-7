"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  Award,
  Briefcase,
  Calendar,
  Check,
  Copy,
  Eye,
  EyeOff,
  GitCommit,
  Globe,
  Linkedin,
  Loader2,
  Lock,
  Rocket,
  Trash2,
  Sparkles,
  Trophy,
  User,
} from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { getStoredToken } from "@/lib/auth";
import { publishPortfolio, getProjectEvolution, deployPortfolio, undeployPortfolio } from "@/lib/api/portfolio";
import type { PortfolioChronology, PortfolioSettings, ProjectEvolutionItem } from "@/types/portfolio";
import type { ProjectMetadata } from "@/types/project";
import type { UserProfile } from "@/lib/api.types";
import { ActivityHeatmap } from "@/components/portfolio/activity-heatmap";
import { SkillsTimeline } from "@/components/portfolio/skills-timeline";
import { ProjectEvolution } from "@/components/portfolio/project-evolution";

interface PortfolioOverviewProps {
  profile: UserProfile | null;
  chronology: PortfolioChronology | null;
  projects: ProjectMetadata[];
  skills: string[];
  initialSettings?: PortfolioSettings | null;
  onShareLinkedIn?: () => void;
}

interface SectionVisibility {
  heatmap: boolean;
  skillsTimeline: boolean;
  topProjects: boolean;
  allSkills: boolean;
}

function computeStats(
  chronology: PortfolioChronology | null,
  projectCount: number,
  skillCount: number,
) {
  const totalCommits =
    chronology?.skills.reduce((sum, skill) => sum + skill.commits, 0) ?? 0;
  const activeMonths = chronology?.skills.length ?? 0;
  return { totalCommits, activeMonths, projectCount, skillCount };
}

function getTopProjects(projects: ProjectMetadata[], limit = 4): ProjectMetadata[] {
  const withScore = projects.filter(
    (project) =>
      project.contribution_score != null && project.contribution_score > 0,
  );

  if (withScore.length > 0) {
    return [...withScore]
      .sort(
        (left, right) =>
          (right.contribution_score ?? 0) - (left.contribution_score ?? 0),
      )
      .slice(0, limit);
  }

  return [...projects]
    .sort(
      (left, right) =>
        new Date(right.created_at ?? 0).getTime() -
        new Date(left.created_at ?? 0).getTime(),
    )
    .slice(0, limit);
}

function parsePeriodValue(label: string): number {
  const match = /^(\d{4})-(\d{2})$/.exec(label);
  if (!match) {
    return 0;
  }

  const yearValue = Number.parseInt(match[1], 10);
  const monthValue = Number.parseInt(match[2], 10);

  if (monthValue < 1 || monthValue > 12) {
    return 0;
  }

  return yearValue * 100 + monthValue;
}

function formatPeriodLabel(label: string | null | undefined): string {
  if (!label) {
    return "No activity yet";
  }

  const match = /^(\d{4})-(\d{2})$/.exec(label);
  if (!match) {
    return label;
  }

  const year = match[1];
  const monthIndex = Number.parseInt(match[2], 10);
  const months = [
    "",
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];

  if (monthIndex < 1 || monthIndex > 12) {
    return label;
  }

  return `${months[monthIndex]} ${year}`;
}

function formatProjectPath(projectPath: string | null | undefined): string {
  if (!projectPath) {
    return "Path unavailable";
  }

  const segments = projectPath.split(/[\\/]+/).filter(Boolean);
  if (segments.length === 0) {
    return projectPath;
  }

  if (segments.length <= 2) {
    return segments.join("/");
  }

  return `.../${segments.slice(-2).join("/")}`;
}

function getPrimarySkill(
  chronology: PortfolioChronology | null,
  skills: string[],
): string {
  const counts = new Map<string, number>();

  for (const period of chronology?.skills ?? []) {
    for (const skill of period.skills) {
      counts.set(skill, (counts.get(skill) ?? 0) + 1);
    }
  }

  const ranked = [...counts.entries()].sort((left, right) => right[1] - left[1]);
  return ranked[0]?.[0] ?? skills[0] ?? "No skill data";
}

function getLatestActivityLabel(chronology: PortfolioChronology | null): string {
  const periods = chronology?.skills ?? [];
  if (periods.length === 0) {
    return "No activity yet";
  }

  const latest = [...periods].sort(
    (left, right) =>
      parsePeriodValue(right.period_label) - parsePeriodValue(left.period_label),
  )[0];

  return formatPeriodLabel(latest?.period_label);
}

function getPeakActivityLabel(
  chronology: PortfolioChronology | null,
): { label: string; commits: number } {
  const periods = chronology?.skills ?? [];
  if (periods.length === 0) {
    return { label: "No activity yet", commits: 0 };
  }

  const peak = [...periods].sort((left, right) => right.commits - left.commits)[0];
  return {
    label: formatPeriodLabel(peak?.period_label),
    commits: peak?.commits ?? 0,
  };
}

function formatShare(share: number | null | undefined): string | null {
  if (share == null) {
    return null;
  }

  return `${Math.round(share * 100)}% yours`;
}

export function PortfolioOverview({
  profile,
  chronology,
  projects,
  skills,
  initialSettings,
  onShareLinkedIn,
}: PortfolioOverviewProps) {
  const [visibility, setVisibility] = useState<SectionVisibility>({
    heatmap: true,
    skillsTimeline: true,
    topProjects: true,
    allSkills: true,
  });

  // Publish state — initialized from parent-fetched settings
  const [pubSettings, setPubSettings] = useState<PortfolioSettings | null>(initialSettings ?? null);
  const [publishing, setPublishing] = useState(false);
  const [copied, setCopied] = useState(false);
  const [publishError, setPublishError] = useState<string | null>(null);
  const [deploying, setDeploying] = useState(false);
  const [undeploying, setUndeploying] = useState(false);
  const [deployError, setDeployError] = useState<string | null>(null);

  // Project evolution data
  const [evolutionData, setEvolutionData] = useState<ProjectEvolutionItem[]>([]);

  // Sync if parent re-fetches settings
  useEffect(() => {
    if (initialSettings) setPubSettings(initialSettings);
  }, [initialSettings]);

  // Fetch evolution data for top projects
  useEffect(() => {
    const topIds = getTopProjects(projects, 4).map((p) => p.id);
    if (topIds.length === 0) return;
    const token = getStoredToken();
    if (!token) return;
    getProjectEvolution(token, topIds)
      .then(setEvolutionData)
      .catch(() => setEvolutionData([]));
  }, [projects]);

  const handleTogglePublish = useCallback(async () => {
    const token = getStoredToken();
    if (!token) return;
    setPublishing(true);
    setPublishError(null);
    setDeployError(null);
    try {
      const newPublic = !pubSettings?.is_public;
      // Auto-undeploy from Vercel when going private
      if (!newPublic && pubSettings?.deployed_url) {
        try {
          await undeployPortfolio(token);
        } catch (undeployErr) {
          // Block the unpublish — the deployed site is still live, so we
          // must keep showing the URL and surface an error instead of
          // silently clearing state while the page remains publicly hosted.
          setDeployError(
            undeployErr instanceof Error
              ? `Could not remove deployment: ${undeployErr.message}. Please remove the deployment first, then try again.`
              : "Could not remove deployment. Please remove the deployment first, then try again.",
          );
          setPublishing(false);
          return;
        }
      }
      const result = await publishPortfolio(token, newPublic);
      setPubSettings((prev) => prev
        ? {
            ...prev,
            is_public: result.is_public,
            share_token: result.share_token,
            ...(result.is_public ? {} : { deployed_url: null }),
          }
        : null,
      );
    } catch (err) {
      setPublishError(err instanceof Error ? err.message : "Failed to publish portfolio");
    } finally {
      setPublishing(false);
    }
  }, [pubSettings?.is_public, pubSettings?.deployed_url]);

  const handleCopyLink = useCallback(() => {
    if (!pubSettings?.share_token) return;
    const url = `${window.location.origin}/p?token=${pubSettings.share_token}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [pubSettings?.share_token]);

  const toggleSection = useCallback((key: keyof SectionVisibility) => {
    setVisibility((current) => ({ ...current, [key]: !current[key] }));
  }, []);

  const stats = computeStats(chronology, projects.length, skills.length);
  const topProjects = getTopProjects(projects, 4);
  const heatmapData = (chronology?.skills ?? []).map((entry) => ({
    period: entry.period_label,
    commits: entry.commits,
  }));
  const primarySkill = getPrimarySkill(chronology, skills);
  const latestActivity = getLatestActivityLabel(chronology);
  const peakActivity = getPeakActivityLabel(chronology);
  const leadProject = topProjects[0];

  const sectionControls = [
    { key: "heatmap", label: "Activity Heatmap" },
    { key: "skillsTimeline", label: "Skills Timeline" },
    { key: "topProjects", label: "Top Projects" },
    { key: "allSkills", label: "Skills Summary" },
  ] as const;

  const insightSections = visibility.heatmap || visibility.skillsTimeline;
  const librarySections = visibility.topProjects || visibility.allSkills;

  const summaryLinks = [
    { id: "portfolio-summary", label: "Summary", visible: true },
    { id: "portfolio-insights", label: "Insights", visible: insightSections },
    { id: "portfolio-projects", label: "Projects", visible: visibility.topProjects },
    { id: "portfolio-skills", label: "Skills", visible: visibility.allSkills },
  ].filter((section) => section.visible);

  return (
    <div className="space-y-4">
      <section id="portfolio-summary" className="portfolio-panel p-5 sm:p-6">
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.82fr)]">
          <div className="flex gap-4">
            <div className="flex h-16 w-16 flex-shrink-0 items-center justify-center overflow-hidden rounded-md border-2 border-border bg-muted">
              {profile?.avatar_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={profile.avatar_url}
                  alt="avatar"
                  className="h-full w-full object-cover"
                />
              ) : (
                <User className="h-7 w-7 text-muted-foreground" />
              )}
            </div>

            <div className="min-w-0 space-y-3">
              <div className="space-y-1">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-muted-foreground">
                  Portfolio Dashboard
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-[2.2rem] font-semibold tracking-[-0.04em] text-foreground">
                    {profile?.display_name || profile?.email || "Portfolio"}
                  </h2>
                  <span className="rounded-full border border-primary/15 bg-primary/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[hsl(var(--accent-foreground))]">
                    Storyboard
                  </span>
                </div>
                {profile?.career_title && (
                  <p className="text-base font-medium text-foreground">
                    {profile.career_title}
                  </p>
                )}
                {(profile?.education || profile?.email) && (
                  <p className="text-sm text-muted-foreground">
                    {profile?.education || profile?.email}
                  </p>
                )}
              </div>

              <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
                Project output, contribution activity, and extracted skills are grouped
                into a tighter dashboard so the strongest signals are visible quickly.
              </p>

              {publishError && (
                <div className="rounded-[12px] border border-red-300 bg-red-50/80 px-3 py-2 text-xs text-red-700">
                  {publishError}
                </div>
              )}

              <div className="rounded-[16px] border border-primary/25 bg-primary/5 p-3 shadow-[0_4px_12px_rgba(15,23,42,0.04)]">
                <div className="flex flex-col gap-3">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground mb-0.5">
                        Visibility
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {pubSettings?.is_public
                          ? "Public • Share with anyone"
                          : "Private • Link only"}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={handleTogglePublish}
                        disabled={publishing}
                        className={`inline-flex items-center gap-1.5 rounded-[12px] border px-3.5 py-2 text-xs font-semibold transition-all ${
                          pubSettings?.is_public
                            ? "border-primary bg-primary text-primary-foreground shadow-[0_6px_16px_hsl(var(--primary)/0.25)] hover:shadow-[0_8px_20px_hsl(var(--primary)/0.3)]"
                            : "border-border bg-card text-foreground hover:bg-muted hover:border-primary/30 shadow-[0_2px_8px_rgba(15,23,42,0.04)]"
                        } disabled:cursor-not-allowed disabled:opacity-50`}
                      >
                        {publishing ? (
                          <>
                            <Spinner size={14} />
                            Updating...
                          </>
                        ) : pubSettings?.is_public ? (
                          <>
                            <Globe className="h-3.5 w-3.5" />
                            Make Private
                          </>
                        ) : (
                          <>
                            <Globe className="h-3.5 w-3.5" />
                            Make Public
                          </>
                        )}
                      </button>

                      {pubSettings?.is_public && pubSettings.share_token && (
                        <button
                          type="button"
                          onClick={handleCopyLink}
                          className="inline-flex items-center gap-1.5 rounded-[12px] border border-primary/30 bg-primary/10 px-3.5 py-2 text-xs font-semibold text-primary transition-all hover:bg-primary/15 hover:border-primary/50 shadow-[0_2px_8px_rgba(15,23,42,0.04)]"
                        >
                          {copied ? (
                            <>
                              <Check className="h-3.5 w-3.5" />
                              Copied!
                            </>
                          ) : (
                            <>
                              <Copy className="h-3.5 w-3.5" />
                              Copy Link
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                  {onShareLinkedIn && (
                    <div className="flex">
                      <button
                        type="button"
                        onClick={onShareLinkedIn}
                        className="inline-flex items-center gap-2 rounded-[14px] border border-border bg-background px-4 py-2.5 text-xs font-semibold text-foreground shadow-[0_2px_8px_rgba(15,23,42,0.04)] transition-[transform,border-color,background-color,color] hover:-translate-y-px hover:border-primary/20 hover:bg-card"
                      >
                        <span className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-primary/15 bg-primary/10 text-[hsl(var(--accent-foreground))]">
                          <Linkedin className="h-3.5 w-3.5" />
                        </span>
                        Share on LinkedIn
                      </button>
                    </div>
                  )}
                  {pubSettings?.is_public && (
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled={deploying}
                        onClick={async () => {
                          const t = getStoredToken();
                          if (!t) return;
                          setDeploying(true);
                          setDeployError(null);
                          try {
                            const res = await deployPortfolio(t);
                            if (res.status === "success" && res.url) {
                              setPubSettings((prev) => prev ? { ...prev, deployed_url: res.url } : prev);
                            } else {
                              setDeployError(res.error ?? "Deployment failed");
                            }
                          } catch (err) {
                            setDeployError(err instanceof Error ? err.message : "Deployment failed");
                          } finally {
                            setDeploying(false);
                          }
                        }}
                        className="inline-flex items-center gap-2 rounded-[14px] border border-border bg-background px-4 py-2.5 text-xs font-semibold text-foreground shadow-[0_2px_8px_rgba(15,23,42,0.04)] transition-[transform,border-color,background-color,color] hover:-translate-y-px hover:border-primary/20 hover:bg-card"
                      >
                        <span className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-emerald-200/60 bg-emerald-500/10 text-emerald-600">
                          {deploying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Rocket className="h-3.5 w-3.5" />}
                        </span>
                        {deploying ? "Deploying..." : pubSettings.deployed_url ? "Redeploy" : "Deploy Portfolio"}
                      </button>
                      {pubSettings.deployed_url && (
                        <button
                          type="button"
                          disabled={undeploying}
                          onClick={async () => {
                            if (!confirm("Remove your deployed portfolio? This will take it offline.")) return;
                            const t = getStoredToken();
                            if (!t) return;
                            setUndeploying(true);
                            setDeployError(null);
                            try {
                              await undeployPortfolio(t);
                              setPubSettings((prev) => prev ? { ...prev, deployed_url: null } : prev);
                            } catch (err) {
                              setDeployError(err instanceof Error ? err.message : "Failed to remove");
                            } finally {
                              setUndeploying(false);
                            }
                          }}
                          className="inline-flex items-center gap-2 rounded-[14px] border border-red-200/60 bg-background px-4 py-2.5 text-xs font-semibold text-red-600 shadow-[0_2px_8px_rgba(15,23,42,0.04)] transition-[transform,border-color,background-color,color] hover:-translate-y-px hover:border-red-300 hover:bg-red-50"
                        >
                          <span className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-red-200/60 bg-red-500/10 text-red-500">
                            {undeploying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                          </span>
                          {undeploying ? "Removing..." : "Remove"}
                        </button>
                      )}
                    </div>
                  )}
                  {pubSettings?.deployed_url && (
                    <a
                      href={pubSettings.deployed_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[10px] text-primary hover:underline truncate max-w-[280px]"
                    >
                      {pubSettings.deployed_url}
                    </a>
                  )}
                  {deployError && (
                    <p className="text-[10px] text-red-500">{deployError}</p>
                  )}
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <span className="portfolio-chip">
                  <Briefcase className="h-3.5 w-3.5" />
                  {stats.projectCount} project{stats.projectCount === 1 ? "" : "s"}
                </span>
                <span className="portfolio-chip">
                  <Award className="h-3.5 w-3.5" />
                  Focus skill: {primarySkill}
                </span>
                <span className="portfolio-chip">
                  <Calendar className="h-3.5 w-3.5" />
                  Latest activity: {latestActivity}
                </span>
              </div>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
            <div className="portfolio-panel-subtle p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                    Top Project
                  </p>
                  <p className="mt-1 truncate text-sm font-semibold text-foreground">
                    {leadProject?.project_name || "No ranked project yet"}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {leadProject?.contribution_score != null
                      ? `Score ${Math.round(leadProject.contribution_score)}`
                      : "Contribution ranking appears here once available."}
                  </p>
                </div>
                <div className="rounded-2xl border border-border bg-white p-2.5 text-foreground shadow-[0_10px_20px_rgba(15,23,42,0.07)]">
                  <Trophy className="h-4 w-4" />
                </div>
              </div>
            </div>

            <div className="portfolio-panel-subtle p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                    Peak Activity
                  </p>
                  <p className="mt-1 text-sm font-semibold text-foreground">
                    {peakActivity.label}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {peakActivity.commits > 0
                      ? `${peakActivity.commits.toLocaleString()} commits in the busiest period`
                      : "Scan git history to surface your busiest period."}
                  </p>
                </div>
                <div className="rounded-2xl border border-border bg-white p-2.5 text-foreground shadow-[0_10px_20px_rgba(15,23,42,0.07)]">
                  <GitCommit className="h-4 w-4" />
                </div>
              </div>
            </div>

            <div className="portfolio-panel-subtle p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                    Skills Coverage
                  </p>
                  <p className="mt-1 text-sm font-semibold text-foreground">
                    {skills.length > 0 ? `${skills.length} tracked skills` : "Awaiting extraction"}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {skills.length > 0
                      ? "Skill signals stay grouped with timeline activity for faster review."
                      : "Run project scans to populate the skills library."}
                  </p>
                </div>
                <div className="rounded-2xl border border-border bg-white p-2.5 text-foreground shadow-[0_10px_20px_rgba(15,23,42,0.07)]">
                  <Sparkles className="h-4 w-4" />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-5 grid gap-3 border-t border-border pt-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
          <div className="overflow-x-auto pb-1">
            <div className="flex w-max gap-2">
              {summaryLinks.map((section) => (
                <a key={section.id} href={`#${section.id}`} className="portfolio-chip">
                  {section.label}
                </a>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap gap-2 lg:justify-end">
            {sectionControls.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                onClick={() => toggleSection(key)}
                aria-pressed={visibility[key]}
                className={`portfolio-chip ${visibility[key] ? "portfolio-chip-active" : ""}`}
              >
                {visibility[key] ? (
                  <Eye className="h-3.5 w-3.5" />
                ) : (
                  <EyeOff className="h-3.5 w-3.5" />
                )}
                {label}
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          {
            icon: <Briefcase className="h-4 w-4" />,
            value: stats.projectCount,
            label: "Projects",
            detail: "Scanned repositories",
          },
          {
            icon: <GitCommit className="h-4 w-4" />,
            value: stats.totalCommits,
            label: "Total Commits",
            detail: "Across tracked periods",
          },
          {
            icon: <Award className="h-4 w-4" />,
            value: stats.skillCount,
            label: "Skills",
            detail: "Extracted capabilities",
          },
          {
            icon: <Calendar className="h-4 w-4" />,
            value: stats.activeMonths,
            label: "Active Months",
            detail: "Months with git activity",
          },
        ].map((stat) => (
          <div key={stat.label} className="portfolio-panel-subtle p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="rounded-md border border-border bg-white p-2 text-foreground">
                {stat.icon}
              </div>
              <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                {stat.label}
              </span>
            </div>
            <p className="mt-4 text-2xl font-semibold tracking-tight text-foreground">
              {stat.value.toLocaleString()}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">{stat.detail}</p>
          </div>
        ))}
      </section>

      {insightSections && (
        <section
          id="portfolio-insights"
          className={`grid gap-4 ${visibility.heatmap && visibility.skillsTimeline ? "xl:grid-cols-[minmax(0,1.18fr)_minmax(320px,0.92fr)]" : "grid-cols-1"}`}
        >
          {visibility.heatmap && (
            <article className="portfolio-panel p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                    Activity
                  </p>
                  <h3 className="mt-1 text-lg font-semibold tracking-tight text-foreground">
                    Activity Heatmap
                  </h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Monthly contribution density, compressed into a year-by-year dashboard view.
                  </p>
                </div>
                <div className="rounded-md border border-border bg-muted px-3 py-1.5 text-xs font-medium text-muted-foreground">
                  Peak: {peakActivity.label}
                </div>
              </div>

              <div className="mt-5">
                <ActivityHeatmap data={heatmapData} />
              </div>
            </article>
          )}

          {visibility.skillsTimeline && (
            <article className="portfolio-panel p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                    Skills Insights
                  </p>
                  <h3 className="mt-1 text-lg font-semibold tracking-tight text-foreground">
                    Skills Timeline
                  </h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Monthly skill adoption, arranged into compact cards that read cleanly on desktop and mobile.
                  </p>
                </div>
                <div className="rounded-md border border-border bg-muted px-3 py-1.5 text-xs font-medium text-muted-foreground">
                  {chronology?.skills.length ?? 0} periods
                </div>
              </div>

              <div className="mt-5">
                <SkillsTimeline data={chronology?.skills ?? []} />
              </div>
            </article>
          )}
        </section>
      )}

      {librarySections && (
        <section
          className={`grid gap-4 ${visibility.topProjects && visibility.allSkills ? "xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.95fr)]" : "grid-cols-1"}`}
        >
          {visibility.topProjects && (
            <article id="portfolio-projects" className="portfolio-panel p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                    Showcase
                  </p>
                  <h3 className="mt-1 text-lg font-semibold tracking-tight text-foreground">
                    Top Projects
                  </h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Ranked work surfaced with the clearest contribution and output signals.
                  </p>
                </div>
                <div className="rounded-md border border-border bg-muted px-3 py-1.5 text-xs font-medium text-muted-foreground">
                  {topProjects.length} shown
                </div>
              </div>

              {topProjects.length === 0 ? (
                <p className="mt-5 rounded-md border border-dashed border-border bg-muted/80 px-4 py-8 text-sm text-muted-foreground">
                  No projects available yet. Scan and rank your projects to see the top showcase.
                </p>
              ) : (
                <>
                <div className="mt-5 grid gap-3 2xl:grid-cols-2">
                  {topProjects.map((project, index) => {
                    const shareLabel = formatShare(project.user_commit_share);
                    const projectPathLabel = formatProjectPath(project.project_path);

                    return (
                      <article
                        key={project.id}
                        className="min-w-0 overflow-hidden rounded-md border border-border bg-muted/85 p-4 transition-colors hover:border-border hover:bg-white"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex min-w-0 items-start gap-3">
                            <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-md border border-border bg-white text-sm font-semibold text-foreground">
                              #{index + 1}
                            </div>
                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-2">
                                <h4 className="truncate text-sm font-semibold text-foreground">
                                  {project.project_name}
                                </h4>
                                {project.role && (
                                  <span className="rounded-md border border-border bg-white px-2 py-1 text-[11px] font-medium text-muted-foreground">
                                    {project.role}
                                  </span>
                                )}
                              </div>
                              <p className="mt-1 break-all text-xs leading-5 text-muted-foreground">
                                {project.primary_contributor
                                  ? `Primary contributor: ${project.primary_contributor}`
                                  : projectPathLabel}
                              </p>
                            </div>
                          </div>

                          {project.contribution_score != null && (
                            <div className="rounded-md border border-border bg-muted px-2.5 py-1.5 text-right text-xs font-semibold text-foreground">
                              {Math.round(project.contribution_score)}
                              <div className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                                score
                              </div>
                            </div>
                          )}
                        </div>

                        <div className="mt-3 flex flex-wrap gap-2">
                          {project.total_commits != null && (
                            <span className="rounded-md border border-border bg-white px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
                              {project.total_commits.toLocaleString()} commits
                            </span>
                          )}
                          {shareLabel && (
                            <span className="rounded-md border border-border bg-white px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
                              {shareLabel}
                            </span>
                          )}
                          <span className="rounded-md border border-border bg-white px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
                            {project.total_files.toLocaleString()} files
                          </span>
                          <span className="rounded-md border border-border bg-white px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
                            {project.total_lines.toLocaleString()} lines
                          </span>
                        </div>

                        <div className="mt-4 flex items-start justify-between gap-3">
                          <p className="min-w-0 flex-1 break-all text-xs leading-5 text-muted-foreground">
                            {projectPathLabel}
                          </p>
                          <Link
                            href={`/project?projectId=${project.id}`}
                            className="inline-flex flex-shrink-0 items-center gap-1 text-xs font-semibold text-foreground transition-colors hover:text-sky-800"
                          >
                            View details
                            <ArrowUpRight className="h-3.5 w-3.5" />
                          </Link>
                        </div>
                      </article>
                    );
                  })}
                </div>

                {/* Project Evolution Timeline */}
                {evolutionData.length > 0 && (
                  <div className="mt-5">
                    <div className="mb-3">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                        Evolution
                      </p>
                      <h3 className="mt-1 text-lg font-semibold tracking-tight text-foreground">
                        Project Growth Over Time
                      </h3>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Monthly commit activity showing how each project evolved.
                      </p>
                    </div>
                    <ProjectEvolution data={evolutionData} />
                  </div>
                )}
                </>
              )}
            </article>
          )}

          {visibility.allSkills && (
            <article id="portfolio-skills" className="portfolio-panel p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                    Skills Library
                  </p>
                  <h3 className="mt-1 text-lg font-semibold tracking-tight text-foreground">
                    All Skills
                  </h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {skills.length > 0
                      ? `${skills.length} skills across all projects`
                      : "No skills found yet. Scan projects to discover skills."}
                  </p>
                </div>
                {skills.length > 0 && (
                  <div className="rounded-md border border-border bg-muted px-3 py-1.5 text-xs font-medium text-muted-foreground">
                    Scrollable list
                  </div>
                )}
              </div>

              {skills.length === 0 ? (
                <p className="mt-5 rounded-md border border-dashed border-border bg-muted/80 px-4 py-8 text-sm text-muted-foreground">
                  No skills found yet. Scan projects to discover skills.
                </p>
              ) : (
                <div className="mt-5 max-h-[24rem] overflow-y-auto pr-1">
                  <div className="grid gap-2 sm:grid-cols-2">
                    {skills.map((skill) => (
                      <div
                        key={skill}
                        className="rounded-md border border-border bg-muted/85 px-3 py-2.5 text-sm font-medium text-foreground"
                      >
                        {skill}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </article>
          )}
        </section>
      )}
    </div>
  );
}
