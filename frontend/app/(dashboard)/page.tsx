"use client";

import { useState, useEffect } from "react";
import { Plus, Loader2, FolderOpen } from "lucide-react";
import { ScanDialog } from "@/components/scan/scan-dialog";
import { RecentScanCard } from "@/components/scan/recent-scan-card";
import { getProjects, getProjectById } from "@/lib/api/projects";
import { getStoredToken } from "@/lib/auth";
import type { ProjectDetail } from "@/types/project";

export default function HomePage() {
  const [scanDialogOpen, setScanDialogOpen] = useState(false);
  const [recentProject, setRecentProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRecentProject = async () => {
    const token = getStoredToken();
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      setError(null);
      const response = await getProjects(token);
      
      if (response.projects && response.projects.length > 0) {
        // Get the most recent project (first in list, assuming sorted by date)
        const mostRecent = response.projects[0];
        
        // Fetch full details for this project
        const details = await getProjectById(token, mostRecent.id);
        setRecentProject(details);
      }
    } catch (err) {
      console.error("Failed to fetch recent project:", err);
      setError(err instanceof Error ? err.message : "Failed to load recent scan");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecentProject();
  }, []);

  // Refresh recent project when scan dialog closes (after a successful scan)
  const handleScanDialogChange = (open: boolean) => {
    setScanDialogOpen(open);
    if (!open) {
      // Refresh after dialog closes in case a new scan was completed
      setTimeout(() => {
        fetchRecentProject();
      }, 500);
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="flex items-center justify-between">
          <h1 className="text-4xl font-bold text-gray-900 tracking-tight">Dashboard</h1>
          <button
            onClick={() => setScanDialogOpen(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors shadow-sm"
          >
            <Plus size={20} />
            <span className="font-medium">New Scan</span>
          </button>
        </div>
      </div>

      {/* Recent Scan Section */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Scan</h2>
        
        {loading ? (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
              <span className="ml-3 text-gray-500">Loading recent scan...</span>
            </div>
          </div>
        ) : error ? (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
            <div className="text-center py-8">
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          </div>
        ) : recentProject ? (
          <RecentScanCard project={recentProject} />
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
            <div className="text-center py-8">
              <div className="inline-flex items-center justify-center w-12 h-12 bg-gray-100 rounded-full mb-4">
                <FolderOpen className="h-6 w-6 text-gray-400" />
              </div>
              <p className="text-gray-600 mb-2">No scans yet</p>
              <p className="text-sm text-gray-500">
                Click "New Scan" to analyze your first project
              </p>
            </div>
          </div>
        )}
      </div>

      <ScanDialog open={scanDialogOpen} onOpenChange={handleScanDialogChange} />
    </div>
  );
}
