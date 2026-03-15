"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Briefcase,
  GitCommit,
  Award,
  Calendar,
  User,
  Eye,
  EyeOff,
  Trophy,
  Globe,
  Link as LinkIcon,
  Check,
  Loader2,
} from "lucide-react";
import { getStoredToken } from "@/lib/auth";
import { getPortfolioSettings, publishPortfolio } from "@/lib/api/portfolio";
import type { PortfolioChronology, PortfolioSettings } from "@/types/portfolio";
import type { ProjectMetadata } from "@/types/project";
import type { UserProfile } from "@/lib/api.types";
import { ActivityHeatmap } from "@/components/portfolio/activity-heatmap";
import { SkillsTimeline } from "@/components/portfolio/skills-timeline";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface PortfolioOverviewProps {
  profile: UserProfile | null;
  chronology: PortfolioChronology | null;
  projects: ProjectMetadata[];
  skills: string[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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
    chronology?.skills.reduce((sum, s) => sum + s.commits, 0) ?? 0;
  const activeMonths = chronology?.skills.length ?? 0;
  return { totalCommits, activeMonths, projectCount, skillCount };
}

function getTopProjects(projects: ProjectMetadata[], limit = 3): ProjectMetadata[] {
  const withScore = projects.filter(
    (p) => p.contribution_score != null && p.contribution_score > 0,
  );
  if (withScore.length > 0) {
    return [...withScore]
      .sort((a, b) => (b.contribution_score ?? 0) - (a.contribution_score ?? 0))
      .slice(0, limit);
  }
  return [...projects]
    .sort(
      (a, b) =>
        new Date(b.created_at ?? 0).getTime() - new Date(a.created_at ?? 0).getTime(),
    )
    .slice(0, limit);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

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

  // Publish state
  const [pubSettings, setPubSettings] = useState<PortfolioSettings | null>(null);
  const [publishing, setPublishing] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) return;
    getPortfolioSettings(token)
      .then(setPubSettings)
      .catch(() => {});
  }, []);

  const handleTogglePublish = useCallback(async () => {
    const token = getStoredToken();
    if (!token) return;
    setPublishing(true);
    try {
      const newPublic = !pubSettings?.is_public;
      const result = await publishPortfolio(token, newPublic);
      setPubSettings((prev) => prev
        ? { ...prev, is_public: result.is_public, share_token: result.share_token }
        : null,
      );
    } catch {
      // silently fail
    } finally {
      setPublishing(false);
    }
  }, [pubSettings?.is_public]);

  const handleCopyLink = useCallback(() => {
    if (!pubSettings?.share_token) return;
    const url = `${window.location.origin}/p?token=${pubSettings.share_token}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [pubSettings?.share_token]);

  const toggleSection = useCallback((key: keyof SectionVisibility) => {
    setVisibility((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const stats = computeStats(chronology, projects.length, skills.length);
  const topProjects = getTopProjects(projects, 3);
  const heatmapData = (chronology?.skills ?? []).map((s) => ({
    period: s.period_label,
    commits: s.commits,
  }));

  return (
    <div className="space-y-6">
      {/* Publish bar + Visibility toggles */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <button
            onClick={handleTogglePublish}
            disabled={publishing}
            className={`px-3 py-1.5 text-xs font-medium rounded-md flex items-center gap-1.5 transition-colors cursor-pointer ${
              pubSettings?.is_public
                ? "bg-green-50 text-green-700 border border-green-200"
                : "bg-gray-100 text-gray-600 border border-gray-200"
            }`}
          >
            {publishing ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <Globe size={12} />
            )}
            {pubSettings?.is_public ? "Public" : "Private"}
          </button>
          {pubSettings?.is_public && pubSettings.share_token && (
            <button
              onClick={handleCopyLink}
              className="px-3 py-1.5 text-xs font-medium rounded-md flex items-center gap-1.5 bg-indigo-50 text-indigo-600 border border-indigo-200 transition-colors cursor-pointer"
            >
              {copied ? <Check size={12} /> : <LinkIcon size={12} />}
              {copied ? "Copied!" : "Copy Link"}
            </button>
          )}
        </div>
        <div className="flex items-center gap-1">
        {(
          [
            ["heatmap", "Heatmap"],
            ["skillsTimeline", "Timeline"],
            ["topProjects", "Projects"],
            ["allSkills", "Skills"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => toggleSection(key)}
            className={`px-2 py-1 text-xs rounded-md flex items-center gap-1 transition-colors cursor-pointer ${
              visibility[key]
                ? "bg-indigo-50 text-indigo-600"
                : "bg-gray-100 text-gray-400"
            }`}
          >
            {visibility[key] ? <Eye size={12} /> : <EyeOff size={12} />}
            {label}
          </button>
        ))}
        </div>
      </div>

      {/* Profile header */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl p-6 text-white">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0 overflow-hidden">
            {profile?.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={profile.avatar_url}
                alt="avatar"
                className="w-full h-full object-cover rounded-full"
              />
            ) : (
              <User size={28} className="text-white/80" />
            )}
          </div>
          <div>
            <h2 className="text-xl font-bold">
              {profile?.display_name || profile?.email || "Portfolio"}
            </h2>
            {profile?.career_title && (
              <p className="text-white/80 text-sm">{profile.career_title}</p>
            )}
            {profile?.education && (
              <p className="text-white/70 text-xs mt-0.5">{profile.education}</p>
            )}
          </div>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { icon: <Briefcase size={18} />, value: stats.projectCount, label: "Projects" },
          { icon: <GitCommit size={18} />, value: stats.totalCommits, label: "Total Commits" },
          { icon: <Award size={18} />, value: stats.skillCount, label: "Skills" },
          { icon: <Calendar size={18} />, value: stats.activeMonths, label: "Active Months" },
        ].map((stat) => (
          <div
            key={stat.label}
            className="bg-gray-50 border border-gray-200 rounded-lg p-4 flex items-center gap-3"
          >
            <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center flex-shrink-0">
              {stat.icon}
            </div>
            <div>
              <div className="text-xl font-bold text-gray-900">{stat.value.toLocaleString()}</div>
              <div className="text-xs text-gray-500">{stat.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Activity Heatmap */}
      {visibility.heatmap && (
        <section className="bg-gray-50 border border-gray-200 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Calendar size={18} className="text-indigo-600" />
            Activity Heatmap
          </h3>
          <ActivityHeatmap data={heatmapData} />
        </section>
      )}

      {/* Skills Timeline */}
      {visibility.skillsTimeline && (
        <section className="bg-gray-50 border border-gray-200 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Award size={18} className="text-indigo-600" />
            Skills Timeline
          </h3>
          <SkillsTimeline data={chronology?.skills ?? []} />
        </section>
      )}

      {/* Top Projects */}
      {visibility.topProjects && (
        <section className="bg-gray-50 border border-gray-200 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Trophy size={18} className="text-indigo-600" />
            Top Projects
          </h3>
          {topProjects.length === 0 ? (
            <p className="text-sm text-gray-400 italic">
              No projects available yet. Scan and rank your projects to see the top showcase.
            </p>
          ) : (
            <div className="grid gap-4 md:grid-cols-3">
              {topProjects.map((project, idx) => (
                <div
                  key={project.id}
                  className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between mb-2">
                    <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">
                      #{idx + 1}
                    </span>
                    {project.contribution_score != null && (
                      <span className="text-xs text-gray-400">
                        Score: {Math.round(project.contribution_score)}
                      </span>
                    )}
                  </div>
                  <h4 className="font-semibold text-gray-900 text-sm mb-1 truncate">
                    {project.project_name}
                  </h4>
                  {project.primary_contributor && (
                    <p className="text-xs text-gray-500 mb-2">
                      Contributor: {project.primary_contributor}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-1 mt-2">
                    {project.total_commits != null && (
                      <span className="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                        {project.total_commits} commits
                      </span>
                    )}
                    {project.user_commit_share != null && (
                      <span className="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                        {Math.round(project.user_commit_share * 100)}% yours
                      </span>
                    )}
                  </div>
                  <div className="mt-3">
                    <Link
                      href={`/project?projectId=${project.id}`}
                      className="text-xs text-indigo-600 hover:underline"
                    >
                      View details
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* All Skills */}
      {visibility.allSkills && (
        <section className="bg-gray-50 border border-gray-200 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Award size={18} className="text-indigo-600" />
            All Skills
          </h3>
          {skills.length === 0 ? (
            <p className="text-sm text-gray-400 italic">
              No skills extracted yet. Scan projects to discover skills.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {skills.map((skill) => (
                <span
                  key={skill}
                  className="px-2.5 py-1 text-xs font-medium bg-indigo-50 text-indigo-700 rounded-full border border-indigo-100"
                >
                  {skill}
                </span>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
