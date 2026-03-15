"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  User,
  Briefcase,
  GitCommit,
  Award,
  Calendar,
  Trophy,
  Loader2,
  Search,
} from "lucide-react";
import { getPublicPortfolio } from "@/lib/api/portfolio";
import type { PublicPortfolioResponse } from "@/types/portfolio";
import { ActivityHeatmap } from "@/components/portfolio/activity-heatmap";
import { SkillsTimeline } from "@/components/portfolio/skills-timeline";

export default function PublicPortfolioPage() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [data, setData] = useState<PublicPortfolioResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [skillFilter, setSkillFilter] = useState("");

  useEffect(() => {
    if (!token) {
      setError("No portfolio token provided.");
      setLoading(false);
      return;
    }
    let cancelled = false;
    getPublicPortfolio(token)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load portfolio");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [token]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center max-w-md px-6">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-200 flex items-center justify-center">
            <User size={28} className="text-gray-400" />
          </div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">Portfolio Not Found</h1>
          <p className="text-sm text-gray-500">
            {error || "This portfolio does not exist or is no longer public."}
          </p>
        </div>
      </div>
    );
  }

  const { profile, settings, skills_timeline, top_projects, heatmap_data, all_skills } = data;

  const totalCommits = skills_timeline.reduce((sum, s) => sum + s.commits, 0);
  const activeMonths = skills_timeline.length;
  const filteredSkills = skillFilter
    ? all_skills.filter((s) => s.toLowerCase().includes(skillFilter.toLowerCase()))
    : all_skills;

  return (
    <div className="max-w-5xl mx-auto px-6 py-10 space-y-8">
      {/* Profile header */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl p-8 text-white">
        <div className="flex items-center gap-5">
          <div className="w-20 h-20 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0 overflow-hidden">
            {profile.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={profile.avatar_url}
                alt="avatar"
                className="w-full h-full object-cover rounded-full"
              />
            ) : (
              <User size={32} className="text-white/80" />
            )}
          </div>
          <div>
            <h1 className="text-2xl font-bold">
              {profile.display_name || "Portfolio"}
            </h1>
            {profile.career_title && (
              <p className="text-white/80 text-sm mt-0.5">{profile.career_title}</p>
            )}
            {profile.education && (
              <p className="text-white/70 text-xs mt-0.5">{profile.education}</p>
            )}
            {profile.bio && (
              <p className="text-white/70 text-sm mt-2">{profile.bio}</p>
            )}
          </div>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { icon: <Briefcase size={18} />, value: top_projects.length, label: "Top Projects" },
          { icon: <GitCommit size={18} />, value: totalCommits, label: "Total Commits" },
          { icon: <Award size={18} />, value: all_skills.length, label: "Skills" },
          { icon: <Calendar size={18} />, value: activeMonths, label: "Active Months" },
        ].map((stat) => (
          <div
            key={stat.label}
            className="bg-white border border-gray-200 rounded-lg p-4 flex items-center gap-3"
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
      {settings.show_heatmap && heatmap_data.length > 0 && (
        <section className="bg-white border border-gray-200 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Calendar size={18} className="text-indigo-600" />
            Activity Heatmap
          </h2>
          <ActivityHeatmap data={heatmap_data} />
        </section>
      )}

      {/* Skills Timeline */}
      {settings.show_skills_timeline && skills_timeline.length > 0 && (
        <section className="bg-white border border-gray-200 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Award size={18} className="text-indigo-600" />
            Skills Timeline
          </h2>
          <SkillsTimeline data={skills_timeline} />
        </section>
      )}

      {/* Top Projects */}
      {settings.show_top_projects && top_projects.length > 0 && (
        <section className="bg-white border border-gray-200 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Trophy size={18} className="text-indigo-600" />
            Top Projects
          </h2>
          <div className="grid gap-4 md:grid-cols-3">
            {top_projects.map((project, idx) => (
              <div
                key={idx}
                className="border border-gray-200 rounded-lg p-4"
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
                <h3 className="font-semibold text-gray-900 text-sm mb-1 truncate">
                  {project.project_name}
                </h3>
                <div className="flex flex-wrap gap-1 mt-2">
                  {project.total_commits != null && (
                    <span className="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                      {project.total_commits} commits
                    </span>
                  )}
                  {project.user_commit_share != null && (
                    <span className="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                      {Math.round(project.user_commit_share * 100)}% contribution
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* All Skills with search filter */}
      {settings.show_all_skills && all_skills.length > 0 && (
        <section className="bg-white border border-gray-200 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Award size={18} className="text-indigo-600" />
              Skills
            </h2>
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Filter skills..."
                value={skillFilter}
                onChange={(e) => setSkillFilter(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {filteredSkills.map((skill) => (
              <span
                key={skill}
                className="px-2.5 py-1 text-xs font-medium bg-indigo-50 text-indigo-700 rounded-full border border-indigo-100"
              >
                {skill}
              </span>
            ))}
            {filteredSkills.length === 0 && (
              <p className="text-sm text-gray-400 italic">No skills match your filter.</p>
            )}
          </div>
        </section>
      )}

      {/* Footer */}
      <footer className="text-center text-xs text-gray-400 py-4">
        Built with Lumen
      </footer>
    </div>
  );
}
