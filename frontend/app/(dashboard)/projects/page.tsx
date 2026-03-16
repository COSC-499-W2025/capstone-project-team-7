"use client";

import { useState, useEffect, useMemo, useRef } from "react";
import { ProjectsTable } from "@/components/projects/projects-table";
import { getProjects, deleteProject, getProjectById, getSelection, saveSelection } from "@/lib/api/projects";
import { ProjectMetadata, ProjectDetail } from "@/types/project";
import { BarChart3, FolderKanban, Languages, Loader2, RefreshCw } from "lucide-react";
import { getStoredToken } from "@/lib/auth";
import { ProjectDetailModal } from "@/components/projects/project-detail-modal";
import { formatOperationError } from "@/lib/error-utils";

type ProjectsSortMode = "contribution" | "recency";

function getRecencyTimestamp(project: ProjectMetadata): number {
  const raw = project.created_at ?? project.scan_timestamp;
  if (!raw) return 0;
  const parsed = new Date(raw).getTime();
  return Number.isFinite(parsed) ? parsed : 0;
}

function sortProjects(projects: ProjectMetadata[], mode: ProjectsSortMode): ProjectMetadata[] {
  const sorted = [...projects];

  if (mode === "contribution") {
    sorted.sort((a, b) => {
      const aScore = a.contribution_score;
      const bScore = b.contribution_score;
      const aMissing = aScore === null || aScore === undefined;
      const bMissing = bScore === null || bScore === undefined;

      if (aMissing && bMissing) {
        return getRecencyTimestamp(b) - getRecencyTimestamp(a);
      }
      if (aMissing) return 1;
      if (bMissing) return -1;

      return bScore - aScore;
    });
    return sorted;
  }

  sorted.sort((a, b) => getRecencyTimestamp(b) - getRecencyTimestamp(a));
  return sorted;
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectMetadata[]>([]);
  const [rankingMode, setRankingMode] = useState<ProjectsSortMode>("recency");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedProject, setSelectedProject] = useState<ProjectDetail | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [savingRankingMode, setSavingRankingMode] = useState(false);
  const [rankingSaveStatus, setRankingSaveStatus] = useState<"saved" | null>(null);
  const rankingSaveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (rankingSaveTimeoutRef.current) {
        clearTimeout(rankingSaveTimeoutRef.current);
      }
    },
    [],
  );

  // Get auth token using the same method as Settings page
  const getAuthToken = () => {
    return getStoredToken(); // Uses "auth_access_token" key
  };

  const fetchProjects = async () => {
    try {
      setError(null);
      const token = getAuthToken();

      if (!token) {
        setError("Not authenticated. Please log in through Settings.");
        setLoading(false);
        setRefreshing(false);
        return;
      }

      const [response, selection] = await Promise.all([
        getProjects(token),
        getSelection(token).catch(() => null),
      ]);
      const nextMode: ProjectsSortMode = selection?.sort_mode ?? "recency";
      const orderedProjects = sortProjects(response.projects, nextMode);
      setRankingMode(nextMode);
      setProjects(orderedProjects);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "";
      console.error("Error fetching projects:", err);

      // If it's an auth error, provide helpful message
      if (errorMessage.includes("401") || errorMessage.includes("Unauthorized") || errorMessage.includes("Invalid")) {
        setError("Session expired or invalid token. Please log in again through Settings.");
      } else {
        setError(
          formatOperationError(
            "load projects",
            err,
            "Failed to load projects. Please refresh the page or try again in a moment.",
          ),
        );
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchProjects();
  };

  const handleDelete = async (projectId: string) => {
    if (!confirm("Are you sure you want to delete this project? This action cannot be undone.")) {
      return;
    }

    try {
      setError(null);
      const token = getAuthToken();
      
      if (!token) {
        setError("You are not authenticated. Please log in through Settings to delete projects.");
        return;
      }
      
      await deleteProject(token, projectId);
      
      // Remove from local state
      setProjects(prev => prev.filter(p => p.id !== projectId));
    } catch (err) {
      setError(
        formatOperationError(
          "delete project",
          err,
          "Failed to delete this project. Please try again.",
        ),
      );
      console.error("Error deleting project:", err);
    }
  };

  const handleView = async (projectId: string) => {
    setError(null);
    const token = getAuthToken();
    if (!token) {
      setError("You are not authenticated. Please log in through Settings to view project details.");
      return;
    }

    setLoadingDetail(true);
    try {
      const projectDetail = await getProjectById(token, projectId);
      setSelectedProject(projectDetail);
      setIsModalOpen(true);
    } catch (err) {
      console.error("Failed to fetch project details:", err);
      setError(
        formatOperationError(
          "load project details",
          err,
          "Failed to load project details. Please try again.",
        ),
      );
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedProject(null);
  };

  const handleProjectUpdate = async () => {
    // Refresh the selected project's details after thumbnail update
    if (selectedProject) {
      const token = getAuthToken();
      if (token) {
        try {
          const updatedProject = await getProjectById(token, selectedProject.id);
          setSelectedProject(updatedProject);
        } catch (err) {
          console.error("Failed to refresh project details:", err);
        }
      }
    }
  };

  const handleRoleUpdate = (projectId: string, newRole: string) => {
    setSelectedProject((prev) =>
      prev ? { ...prev, role: newRole } : prev
    );
    setProjects((prev) =>
      prev.map((p) => (p.id === projectId ? { ...p, role: newRole } : p))
    );
  };

  const persistRankingMode = async (sortMode: ProjectsSortMode) => {
    const token = getAuthToken();
    if (!token) {
      return;
    }

    setSavingRankingMode(true);
    setRankingSaveStatus(null);
    try {
      await saveSelection(token, {
        sort_mode: sortMode,
      });
      setRankingSaveStatus("saved");
      if (rankingSaveTimeoutRef.current) {
        clearTimeout(rankingSaveTimeoutRef.current);
      }
      rankingSaveTimeoutRef.current = setTimeout(() => {
        setRankingSaveStatus(null);
      }, 2000);
    } catch (err) {
      setError(
        formatOperationError(
          "save ranking preference",
          err,
          "Failed to save ranking preference. Your selection may be temporary.",
        ),
      );
      setRankingSaveStatus(null);
    } finally {
      setSavingRankingMode(false);
    }
  };

  const handleRankingModeChange = (mode: ProjectsSortMode) => {
    if (mode === rankingMode) {
      return;
    }

    setRankingMode(mode);
    setProjects((prevProjects) => sortProjects(prevProjects, mode));
    void persistRankingMode(mode);
  };

  const projectSummary = useMemo(() => {
    const totals = projects.reduce(
      (acc, project) => {
        acc.files += typeof project.total_files === "number" ? project.total_files : 0;
        acc.lines += typeof project.total_lines === "number" ? project.total_lines : 0;
        if (Array.isArray(project.languages)) {
          project.languages.forEach((language) => acc.languages.add(language));
        }
        if (typeof project.contribution_score === "number") {
          acc.scoredCount += 1;
          acc.scoreTotal += project.contribution_score;
        }
        return acc;
      },
      {
        files: 0,
        lines: 0,
        scoredCount: 0,
        scoreTotal: 0,
        languages: new Set<string>(),
      },
    );

    const mostRecentProject = [...projects].sort(
      (a, b) => getRecencyTimestamp(b) - getRecencyTimestamp(a),
    )[0];

    return {
      totalProjects: projects.length,
      totalFiles: totals.files,
      totalLines: totals.lines,
      uniqueLanguages: totals.languages.size,
      averageScore:
        totals.scoredCount > 0 ? (totals.scoreTotal / totals.scoredCount).toFixed(1) : "Unranked",
      mostRecentLabel:
        mostRecentProject?.created_at || mostRecentProject?.scan_timestamp
          ? new Date(mostRecentProject.created_at ?? mostRecentProject.scan_timestamp ?? "").toLocaleDateString()
          : "No scans yet",
    };
  }, [projects]);

  if (loading) {
    return (
      <div className="mx-auto max-w-[1440px] p-6 lg:p-8">
        <div className="rounded-[28px] border border-slate-200 bg-white px-8 py-20 shadow-[0_18px_60px_rgba(15,23,42,0.06)]">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            <span className="ml-3 text-sm font-medium text-slate-500">Loading projects...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1440px] p-6 lg:p-8">
      <div className="space-y-6">
        <section className="rounded-[32px] border border-slate-200 bg-[linear-gradient(135deg,rgba(248,250,252,0.96),rgba(255,255,255,0.98))] p-8 shadow-[0_18px_60px_rgba(15,23,42,0.06)]">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-2xl">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                Project Library
              </p>
              <h1 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">Projects</h1>
              <p className="mt-3 text-sm leading-6 text-slate-600">
                A cleaner view of your scanned work, with the key metrics surfaced early and full
                analysis one click away.
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <button
                onClick={handleRefresh}
                disabled={refreshing || savingRankingMode}
                className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <RefreshCw size={18} className={refreshing ? "animate-spin" : ""} />
                <span>Refresh</span>
              </button>
            </div>
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-3xl border border-slate-200 bg-white/90 p-5">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Projects</p>
                <FolderKanban className="h-4 w-4 text-slate-400" />
              </div>
              <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
                {projectSummary.totalProjects}
              </p>
              <p className="mt-1 text-sm text-slate-500">
                {projectSummary.totalProjects === 1 ? "Saved project" : "Saved projects"}
              </p>
            </div>
            <div className="rounded-3xl border border-slate-200 bg-white/90 p-5">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Tracked Files</p>
                <BarChart3 className="h-4 w-4 text-slate-400" />
              </div>
              <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
                {projectSummary.totalFiles.toLocaleString()}
              </p>
              <p className="mt-1 text-sm text-slate-500">
                {projectSummary.totalLines.toLocaleString()} lines across all projects
              </p>
            </div>
            <div className="rounded-3xl border border-slate-200 bg-white/90 p-5">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Languages</p>
                <Languages className="h-4 w-4 text-slate-400" />
              </div>
              <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
                {projectSummary.uniqueLanguages}
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Avg contribution score {projectSummary.averageScore}
              </p>
            </div>
            <div className="rounded-3xl border border-slate-200 bg-white/90 p-5">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Most Recent</p>
                <RefreshCw className="h-4 w-4 text-slate-400" />
              </div>
              <p className="mt-3 text-xl font-semibold tracking-tight text-slate-950">
                {projectSummary.mostRecentLabel}
              </p>
              <p className="mt-1 text-sm text-slate-500">Newest saved scan date</p>
            </div>
          </div>
        </section>

        {error && (
          <div className="rounded-3xl border border-red-200 bg-red-50 px-5 py-4">
            <h3 className="text-sm font-semibold text-red-800">Error loading projects</h3>
            <p className="mt-1 text-sm text-red-700">{error}</p>
          </div>
        )}

        <section className="rounded-[32px] border border-slate-200 bg-white p-6 shadow-[0_18px_60px_rgba(15,23,42,0.05)]">
          <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-xl font-semibold tracking-tight text-slate-950">Scanned projects</h2>
              <p className="mt-1 text-sm text-slate-500">
                {projects.length === 0
                  ? "No projects saved yet"
                  : `${projects.length} project${projects.length === 1 ? "" : "s"} in your current workspace`}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <label htmlFor="projects-ranking-mode" className="text-sm font-medium text-slate-700">
                Sort by
              </label>
              <select
                id="projects-ranking-mode"
                data-testid="projects-ranking-mode"
                value={rankingMode}
                onChange={(event) => handleRankingModeChange(event.target.value as ProjectsSortMode)}
                disabled={savingRankingMode}
                className="rounded-full border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:border-slate-400 focus:outline-none"
              >
                <option value="recency">Recency</option>
                <option value="contribution">Contribution</option>
              </select>
              {savingRankingMode && (
                <p className="text-sm text-slate-500">Saving ranking preference...</p>
              )}
              {!savingRankingMode && rankingSaveStatus === "saved" && (
                <p className="text-sm text-emerald-700">Ranking preference saved.</p>
              )}
            </div>
          </div>

          <ProjectsTable
            projects={projects}
            onDelete={handleDelete}
            onView={handleView}
            rankingMode={rankingMode}
          />
        </section>
      </div>

      {/* Loading overlay when fetching project details */}
      {loadingDetail && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4 flex items-center gap-3">
            <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            <span className="text-gray-700">Loading project details...</span>
          </div>
        </div>
      )}

      {/* Project Detail Modal */}
      <ProjectDetailModal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        project={selectedProject}
        onProjectUpdate={handleProjectUpdate}
        token={getAuthToken()}
        onRoleUpdate={handleRoleUpdate}
      />
    </div>
  );
}
