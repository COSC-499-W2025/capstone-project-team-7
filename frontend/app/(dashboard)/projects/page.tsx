"use client";

import { useState, useEffect } from "react";
import { ProjectsTable } from "@/components/projects/projects-table";
import { getProjects, deleteProject, getProjectById } from "@/lib/api/projects";
import { ProjectMetadata, ProjectDetail } from "@/types/project";
import { Loader2, RefreshCw } from "lucide-react";
import { getStoredToken } from "@/lib/auth";
import { ProjectDetailModal } from "@/components/projects/project-detail-modal";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedProject, setSelectedProject] = useState<ProjectDetail | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

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
      const response = await getProjects(token);
      console.log("Projects fetched successfully:", response);
      console.log("First project data:", response.projects[0]);
      setProjects(response.projects);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load projects";
      console.error("Error fetching projects:", err);
      setError(errorMessage);
      
      // If it's an auth error, provide helpful message
      if (errorMessage.includes("401") || errorMessage.includes("Unauthorized") || errorMessage.includes("Invalid")) {
        setError("Session expired or invalid token. Please log in again through Settings.");
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
      const token = getAuthToken();
      
      if (!token) {
        alert("Not authenticated. Please log in through Settings.");
        return;
      }
      
      await deleteProject(token, projectId);
      
      // Remove from local state
      setProjects(prev => prev.filter(p => p.id !== projectId));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete project");
      console.error("Error deleting project:", err);
    }
  };

  const handleView = async (projectId: string) => {
    const token = getAuthToken();
    if (!token) {
      alert("Not authenticated. Please log in through Settings.");
      return;
    }

    setLoadingDetail(true);
    try {
      const projectDetail = await getProjectById(token, projectId);
      setSelectedProject(projectDetail);
      setIsModalOpen(true);
    } catch (err) {
      console.error("Failed to fetch project details:", err);
      alert(err instanceof Error ? err.message : "Failed to load project details");
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedProject(null);
  };

  if (loading) {
    return (
      <div className="p-8">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
            <span className="ml-3 text-gray-500">Loading projects...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        {/* Header */}
        <div className="px-8 py-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Projects</h1>
              <p className="mt-2 text-sm text-gray-600">
                {projects.length === 0
                  ? "No projects yet"
                  : `${projects.length} project${projects.length === 1 ? "" : "s"} saved`}
              </p>
            </div>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw size={18} className={refreshing ? "animate-spin" : ""} />
              <span className="font-medium">Refresh</span>
            </button>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="mx-8 mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error loading projects</h3>
                <p className="mt-1 text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Table */}
        <div className="p-8">
          <ProjectsTable
            projects={projects}
            onDelete={handleDelete}
            onView={handleView}
          />
        </div>
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
      />
    </div>
  );
}
