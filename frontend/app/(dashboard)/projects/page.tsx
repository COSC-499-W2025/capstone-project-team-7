"use client";

import { useState, useEffect, useRef } from "react";
import { ProjectsTable } from "@/components/projects/projects-table";
import { getProjects, deleteProject, getProjectById, getSelection, saveSelection } from "@/lib/api/projects";
import { ProjectMetadata, ProjectDetail } from "@/types/project";
import { Loader2, RefreshCw } from "lucide-react";
import { getStoredToken } from "@/lib/auth";
import { ProjectDetailModal } from "@/components/projects/project-detail-modal";
import { formatOperationError } from "@/lib/error-utils";
import { Button } from "@/components/ui/button";

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
      
      // Debug logging
      console.log("Projects page - Token check:", token ? "Token found" : "No token");
      console.log("Projects page - Token length:", token?.length);
      
      if (!token) {
        setError("Not authenticated. Please log in through Settings.");
        setLoading(false);
        setRefreshing(false);
        return;
      }
      
      console.log("Fetching projects with token...");
      const [response, selection] = await Promise.all([
        getProjects(token),
        getSelection(token).catch(() => null),
      ]);
      const nextMode: ProjectsSortMode = selection?.sort_mode ?? "recency";
      const orderedProjects = sortProjects(response.projects, nextMode);
      setRankingMode(nextMode);
      console.log("Projects fetched successfully:", response);
      console.log("First project data:", orderedProjects[0]);
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

  if (loading) {
    return (
      <div className="page-container">
        <div className="page-card p-8">
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <span className="ml-3 text-muted-foreground">Loading projects...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <section className="page-card page-hero">
        <div className="page-header">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="page-kicker">Evidence Library</p>
              <h1 className="text-foreground">Projects</h1>
              <p className="page-summary">
                Ranked project evidence, contribution metadata, and scan coverage in one sortable view.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <span className="dashboard-chip">{projects.length} project{projects.length === 1 ? "" : "s"}</span>
                <span className="dashboard-chip">Ranked by {rankingMode}</span>
                {rankingSaveStatus === "saved" && <span className="dashboard-chip">Preference saved</span>}
              </div>
            </div>

            <Button
              onClick={handleRefresh}
              disabled={refreshing || savingRankingMode}
              variant="outline"
            >
              <RefreshCw size={18} className={refreshing ? "animate-spin" : ""} />
              <span className="font-medium">Refresh</span>
            </Button>
          </div>
        </div>
      </section>

      {error && (
        <div className="alert alert-error">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-800" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error loading projects</h3>
              <p className="mt-1 text-sm text-red-800">{error}</p>
            </div>
          </div>
        </div>
      )}

      <section className="page-card page-body">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-4 rounded-[20px] border border-border/80 bg-muted/45 p-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                Ranking Controls
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                Switch the ordering without changing any project data.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <label htmlFor="projects-ranking-mode" className="text-sm font-medium text-foreground">
              Ranking
              </label>
              <select
                id="projects-ranking-mode"
                data-testid="projects-ranking-mode"
                value={rankingMode}
                onChange={(event) => handleRankingModeChange(event.target.value as ProjectsSortMode)}
                disabled={savingRankingMode}
                className="h-11 rounded-[14px] border border-border bg-card px-3.5 py-2 text-sm text-foreground shadow-[inset_0_1px_0_rgba(255,255,255,0.75),0_8px_18px_rgba(15,23,42,0.04)] focus:border-primary/40 focus:outline-none focus:ring-2 focus:ring-ring/40"
              >
                <option value="recency">Recency</option>
                <option value="contribution">Contribution</option>
              </select>
              {savingRankingMode && (
                <p className="text-sm text-muted-foreground">Saving ranking preference...</p>
              )}
              {!savingRankingMode && rankingSaveStatus === "saved" && (
                <p className="text-sm text-foreground">Ranking preference saved.</p>
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

      {/* Loading overlay when fetching project details */}
      {loadingDetail && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card rounded-md border-2 border-border p-4 flex items-center gap-3">
            <Loader2 className="h-6 w-6 animate-spin text-foreground" />
            <span className="text-foreground">Loading project details...</span>
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
