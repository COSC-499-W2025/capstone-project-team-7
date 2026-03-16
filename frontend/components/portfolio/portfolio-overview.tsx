"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  Award,
  Briefcase,
  Calendar,
  Eye,
  EyeOff,
  GitCommit,
  Sparkles,
  Trophy,
  User,
} from "lucide-react";
import type { PortfolioChronology } from "@/types/portfolio";
import type { ProjectMetadata } from "@/types/project";
import type { UserProfile } from "@/lib/api.types";
import { ActivityHeatmap } from "@/components/portfolio/activity-heatmap";
import { SkillsTimeline } from "@/components/portfolio/skills-timeline";

interface PortfolioOverviewProps {
  profile: UserProfile | null;
  chronology: PortfolioChronology | null;
  projects: ProjectMetadata[];
  skills: string[];
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
  const [year, month] = label.split("-");
  const yearValue = Number.parseInt(year, 10) || 0;
  const monthValue = Number.parseInt(month, 10) || 0;
  return yearValue * 100 + monthValue;
}

function formatPeriodLabel(label: string | null | undefined): string {
  if (!label) {
    return "No activity yet";
  }

  const [year, month] = label.split("-");
  const monthIndex = Number.parseInt(month, 10);
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

  return `${months[monthIndex] || month} ${year}`;
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
}: PortfolioOverviewProps) {
  const [visibility, setVisibility] = useState<SectionVisibility>({
    heatmap: true,
    skillsTimeline: true,
    topProjects: true,
    allSkills: true,
  });

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
            <div className="flex h-16 w-16 flex-shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-slate-200 bg-slate-100">
              {profile?.avatar_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={profile.avatar_url}
                  alt="avatar"
                  className="h-full w-full object-cover"
                />
              ) : (
                <User className="h-7 w-7 text-slate-500" />
              )}
            </div>

            <div className="min-w-0 space-y-3">
              <div className="space-y-1">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-700">
                  Portfolio Dashboard
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-2xl font-semibold tracking-tight text-slate-950">
                    {profile?.display_name || profile?.email || "Portfolio"}
                  </h2>
                  <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-medium text-slate-600">
                    Compact overview
                  </span>
                </div>
                {profile?.career_title && (
                  <p className="text-sm font-medium text-slate-700">
                    {profile.career_title}
                  </p>
                )}
                {(profile?.education || profile?.email) && (
                  <p className="text-sm text-slate-500">
                    {profile?.education || profile?.email}
                  </p>
                )}
              </div>

              <p className="max-w-2xl text-sm leading-6 text-slate-600">
                Project output, contribution activity, and extracted skills are grouped
                into a tighter dashboard so the strongest signals are visible quickly.
              </p>

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
            <div className="portfolio-panel-subtle p-3.5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Top Project
                  </p>
                  <p className="mt-1 truncate text-sm font-semibold text-slate-950">
                    {leadProject?.project_name || "No ranked project yet"}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {leadProject?.contribution_score != null
                      ? `Score ${Math.round(leadProject.contribution_score)}`
                      : "Contribution ranking appears here once available."}
                  </p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-2 text-sky-700">
                  <Trophy className="h-4 w-4" />
                </div>
              </div>
            </div>

            <div className="portfolio-panel-subtle p-3.5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Peak Activity
                  </p>
                  <p className="mt-1 text-sm font-semibold text-slate-950">
                    {peakActivity.label}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {peakActivity.commits > 0
                      ? `${peakActivity.commits.toLocaleString()} commits in the busiest period`
                      : "Scan git history to surface your busiest period."}
                  </p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-2 text-sky-700">
                  <GitCommit className="h-4 w-4" />
                </div>
              </div>
            </div>

            <div className="portfolio-panel-subtle p-3.5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Skills Coverage
                  </p>
                  <p className="mt-1 text-sm font-semibold text-slate-950">
                    {skills.length > 0 ? `${skills.length} tracked skills` : "Awaiting extraction"}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {skills.length > 0
                      ? "Skill signals stay grouped with timeline activity for faster review."
                      : "Run project scans to populate the skills library."}
                  </p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-2 text-sky-700">
                  <Sparkles className="h-4 w-4" />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-5 grid gap-3 border-t border-slate-200 pt-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
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
              <div className="rounded-xl border border-slate-200 bg-white p-2 text-sky-700">
                {stat.icon}
              </div>
              <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                {stat.label}
              </span>
            </div>
            <p className="mt-4 text-2xl font-semibold tracking-tight text-slate-950">
              {stat.value.toLocaleString()}
            </p>
            <p className="mt-1 text-xs text-slate-500">{stat.detail}</p>
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
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                    Activity
                  </p>
                  <h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">
                    Activity Heatmap
                  </h3>
                  <p className="mt-1 text-sm text-slate-500">
                    Monthly contribution density, compressed into a year-by-year dashboard view.
                  </p>
                </div>
                <div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-500">
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
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                    Skills Insights
                  </p>
                  <h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">
                    Skills Timeline
                  </h3>
                  <p className="mt-1 text-sm text-slate-500">
                    Monthly skill adoption, arranged into compact cards that read cleanly on desktop and mobile.
                  </p>
                </div>
                <div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-500">
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
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                    Showcase
                  </p>
                  <h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">
                    Top Projects
                  </h3>
                  <p className="mt-1 text-sm text-slate-500">
                    Ranked work surfaced with the clearest contribution and output signals.
                  </p>
                </div>
                <div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-500">
                  {topProjects.length} shown
                </div>
              </div>

              {topProjects.length === 0 ? (
                <p className="mt-5 rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-8 text-sm text-slate-500">
                  No projects available yet. Scan and rank your projects to see the top showcase.
                </p>
              ) : (
                <div className="mt-5 grid gap-3 2xl:grid-cols-2">
                  {topProjects.map((project, index) => {
                    const shareLabel = formatShare(project.user_commit_share);

                    return (
                      <article
                        key={project.id}
                        className="min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-slate-50/85 p-4 transition-colors hover:border-slate-300 hover:bg-white"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex min-w-0 items-start gap-3">
                            <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-sm font-semibold text-slate-700">
                              #{index + 1}
                            </div>
                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-2">
                                <h4 className="truncate text-sm font-semibold text-slate-950">
                                  {project.project_name}
                                </h4>
                                {project.role && (
                                  <span className="rounded-full border border-slate-200 bg-white px-2 py-1 text-[11px] font-medium text-slate-500">
                                    {project.role}
                                  </span>
                                )}
                              </div>
                              <p className="mt-1 break-all text-xs leading-5 text-slate-500">
                                {project.primary_contributor
                                  ? `Primary contributor: ${project.primary_contributor}`
                                  : project.project_path}
                              </p>
                            </div>
                          </div>

                          {project.contribution_score != null && (
                            <div className="rounded-xl border border-sky-100 bg-sky-50 px-2.5 py-1.5 text-right text-xs font-semibold text-sky-700">
                              {Math.round(project.contribution_score)}
                              <div className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.18em] text-sky-500">
                                score
                              </div>
                            </div>
                          )}
                        </div>

                        <div className="mt-3 flex flex-wrap gap-2">
                          {project.total_commits != null && (
                            <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-600">
                              {project.total_commits.toLocaleString()} commits
                            </span>
                          )}
                          {shareLabel && (
                            <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-600">
                              {shareLabel}
                            </span>
                          )}
                          <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-600">
                            {project.total_files.toLocaleString()} files
                          </span>
                          <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-600">
                            {project.total_lines.toLocaleString()} lines
                          </span>
                        </div>

                        <div className="mt-4 flex items-start justify-between gap-3">
                          <p className="min-w-0 flex-1 break-all text-xs leading-5 text-slate-400">
                            {project.project_path}
                          </p>
                          <Link
                            href={`/project?projectId=${project.id}`}
                            className="inline-flex flex-shrink-0 items-center gap-1 text-xs font-semibold text-sky-700 transition-colors hover:text-sky-800"
                          >
                            View details
                            <ArrowUpRight className="h-3.5 w-3.5" />
                          </Link>
                        </div>
                      </article>
                    );
                  })}
                </div>
              )}
            </article>
          )}

          {visibility.allSkills && (
            <article id="portfolio-skills" className="portfolio-panel p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                    Skills Library
                  </p>
                  <h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">
                    All Skills
                  </h3>
                  <p className="mt-1 text-sm text-slate-500">
                    {skills.length > 0
                      ? `${skills.length} skills across all projects`
                      : "No skills found yet. Scan projects to discover skills."}
                  </p>
                </div>
                {skills.length > 0 && (
                  <div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-500">
                    Scrollable list
                  </div>
                )}
              </div>

              {skills.length === 0 ? (
                <p className="mt-5 rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-8 text-sm text-slate-500">
                  No skills found yet. Scan projects to discover skills.
                </p>
              ) : (
                <div className="mt-5 max-h-[24rem] overflow-y-auto pr-1">
                  <div className="grid gap-2 sm:grid-cols-2">
                    {skills.map((skill) => (
                      <div
                        key={skill}
                        className="rounded-2xl border border-slate-200 bg-slate-50/85 px-3 py-2.5 text-sm font-medium text-slate-700"
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
