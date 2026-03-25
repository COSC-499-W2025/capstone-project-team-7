"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  User,
  Briefcase,
  GitCommit,
  Award,
  Calendar,
  Trophy,
  Search,
} from "lucide-react";
import { getPublicPortfolio } from "@/lib/api/portfolio";
import type { PublicPortfolioResponse } from "@/types/portfolio";
import { ActivityHeatmap } from "@/components/portfolio/activity-heatmap";
import { SkillsTimeline } from "@/components/portfolio/skills-timeline";
import { LoadingState } from "@/components/ui/loading-state";
import { EmptyState } from "@/components/ui/empty-state";

export default function PublicPortfolioPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center px-6"><div className="w-full max-w-5xl"><LoadingState message="Loading portfolio..." /></div></div>}>
      <PublicPortfolioContent />
    </Suspense>
  );
}

function PublicPortfolioContent() {
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
      <div className="flex min-h-screen items-center justify-center px-6">
        <div className="w-full max-w-5xl">
          <LoadingState message="Loading portfolio..." />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <EmptyState
          title="Portfolio Not Found"
          description={error || "This portfolio does not exist or is no longer public."}
        />
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
    <div className="max-w-6xl mx-auto px-6 py-10 space-y-8">
      {/* Profile header */}
      <div className="page-card overflow-hidden">
        <div className="page-header bg-primary text-primary-foreground">
        <div className="flex items-center gap-5">
          <div className="w-20 h-20 rounded-full bg-white/15 flex items-center justify-center flex-shrink-0 overflow-hidden">
            {profile.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={profile.avatar_url}
                alt="avatar"
                className="w-full h-full object-cover rounded-full"
              />
            ) : (
              <User size={32} className="text-primary-foreground/80" />
            )}
          </div>
          <div>
            <h1 className="text-2xl font-bold">
              {profile.display_name || "Portfolio"}
            </h1>
            {profile.career_title && (
              <p className="text-primary-foreground/80 text-sm mt-0.5">{profile.career_title}</p>
            )}
            {profile.education && (
              <p className="text-primary-foreground/80 text-xs mt-0.5">{profile.education}</p>
            )}
            {profile.bio && (
              <p className="text-primary-foreground/80 text-sm mt-2">{profile.bio}</p>
            )}
          </div>
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
            className="bg-card border-2 border-border rounded-md p-4 flex items-center gap-3"
          >
            <div className="w-9 h-9 rounded-md bg-muted text-foreground flex items-center justify-center flex-shrink-0">
              {stat.icon}
            </div>
            <div>
              <div className="text-xl font-bold text-foreground">{stat.value.toLocaleString()}</div>
              <div className="text-xs text-muted-foreground">{stat.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Activity Heatmap */}
      {settings.show_heatmap && heatmap_data.length > 0 && (
        <section className="bg-card border-2 border-border rounded-md p-6">
          <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
            <Calendar size={18} className="text-muted-foreground" />
            Activity Heatmap
          </h2>
          <ActivityHeatmap data={heatmap_data} />
        </section>
      )}

      {/* Skills Timeline */}
      {settings.show_skills_timeline && skills_timeline.length > 0 && (
        <section className="bg-card border-2 border-border rounded-md p-6">
          <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
            <Award size={18} className="text-muted-foreground" />
            Skills Timeline
          </h2>
          <SkillsTimeline data={skills_timeline} />
        </section>
      )}

      {/* Top Projects */}
      {settings.show_top_projects && top_projects.length > 0 && (
        <section className="bg-card border-2 border-border rounded-md p-6">
          <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
            <Trophy size={18} className="text-muted-foreground" />
            Top Projects
          </h2>
          <div className="grid gap-4 md:grid-cols-3">
            {top_projects.map((project, idx) => (
              <div
                key={idx}
                className="border-2 border-border rounded-md p-4"
              >
                <div className="flex items-start justify-between mb-2">
                  <span className="text-xs font-bold text-foreground bg-muted border border-border px-2 py-0.5 rounded-md">
                    #{idx + 1}
                  </span>
                  {project.contribution_score != null && (
                    <span className="text-xs text-muted-foreground">
                      Score: {Math.round(project.contribution_score)}
                    </span>
                  )}
                </div>
                <h3 className="font-semibold text-foreground text-sm mb-1 truncate">
                  {project.project_name}
                </h3>
                <div className="flex flex-wrap gap-1 mt-2">
                  {project.total_commits != null && (
                    <span className="text-[10px] bg-muted text-muted-foreground px-1.5 py-0.5 rounded-md">
                      {project.total_commits} commits
                    </span>
                  )}
                  {project.user_commit_share != null && (
                    <span className="text-[10px] bg-muted text-muted-foreground px-1.5 py-0.5 rounded-md">
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
        <section className="bg-card border-2 border-border rounded-md p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
              <Award size={18} className="text-muted-foreground" />
              Skills
            </h2>
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="Filter skills..."
                value={skillFilter}
                onChange={(e) => setSkillFilter(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs border-2 border-border rounded-md focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {filteredSkills.map((skill) => (
              <span
                key={skill}
                className="px-2.5 py-1 text-xs font-medium bg-muted text-foreground rounded-md border border-border"
              >
                {skill}
              </span>
            ))}
            {filteredSkills.length === 0 && (
              <p className="text-sm text-muted-foreground italic">No skills match your filter.</p>
            )}
          </div>
        </section>
      )}

      {/* Footer */}
      <footer className="text-center text-xs text-muted-foreground py-4">
        Built with Lumen
      </footer>
    </div>
  );
}
