"use client";

import { useState } from "react";
import { ProjectMetadata } from "@/types/project";
import { formatDistanceToNow } from "date-fns";
import { Trash2, Eye, FolderOpen, GripVertical, ArrowUp, ArrowDown } from "lucide-react";
import { useRouter } from "next/navigation";

interface ProjectsTableProps {
  projects: ProjectMetadata[];
  onDelete: (projectId: string) => void;
  onView: (projectId: string) => void;
  onReorder: (fromIndex: number, toIndex: number) => void;
}

export function ProjectsTable({ projects, onDelete, onView, onReorder }: ProjectsTableProps) {
  const router = useRouter();
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragOverId, setDragOverId] = useState<string | null>(null);

  const formatDate = (dateString?: string) => {
    if (!dateString) return "N/A";
    try {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true });
    } catch {
      return dateString;
    }
  };

  const formatNumber = (num?: number) => {
    if (num === undefined || num === null) return "0";
    return num.toLocaleString();
  };

  // Helper to extract data from project, checking both root and scan_data.summary
  const getProjectData = (project: ProjectMetadata) => {
    const scanData = (project as any).scan_data || {};
    const summary = scanData.summary || {};
    
    // Extract from root first (populated by backend normalization), fallback to scan_data
    const totalFiles = project.total_files || summary.total_files || 0;
    const totalLines = project.total_lines || summary.total_lines || 0;
    
    // Extract languages from various sources
    let languages: string[] = [];
    if (project.languages && project.languages.length > 0) {
      languages = project.languages;
    } else if (scanData.languages) {
      const scanLanguages = scanData.languages;
      if (Array.isArray(scanLanguages)) {
        if (scanLanguages.length > 0 && typeof scanLanguages[0] === 'object') {
          languages = scanLanguages.map((lang: any) => lang.language || lang.name).filter(Boolean);
        } else {
          languages = scanLanguages;
        }
      } else if (typeof scanLanguages === 'object') {
        languages = Object.keys(scanLanguages);
      }
    }
    
    return {
      totalFiles,
      totalLines,
      languages
    };
  };

  if (projects.length === 0) {
    return (
      <div className="text-center py-16">
        <FolderOpen className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-4 text-lg font-medium text-gray-900">No projects found</h3>
        <p className="mt-2 text-sm text-gray-500">Get started by scanning your first project.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th scope="col" className="w-14 px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              <span className="sr-only">Reorder</span>
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Project Name
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Path
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Languages
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Files
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Lines
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Role
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Scanned
            </th>
            <th scope="col" className="relative px-6 py-3">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {projects.map((project, index) => {
            const projectData = getProjectData(project);
            const canMoveUp = index > 0;
            const canMoveDown = index < projects.length - 1;
            
            return (
            <tr
              key={project.id}
              draggable
              onDragStart={(event) => {
                event.dataTransfer.setData("text/plain", project.id);
                event.dataTransfer.effectAllowed = "move";
                setDraggingId(project.id);
              }}
              onDragOver={(event) => {
                event.preventDefault();
                setDragOverId(project.id);
              }}
              onDrop={(event) => {
                event.preventDefault();
                const sourceId = event.dataTransfer.getData("text/plain");
                const fromIndex = projects.findIndex((p) => p.id === sourceId);
                const toIndex = projects.findIndex((p) => p.id === project.id);
                if (fromIndex >= 0 && toIndex >= 0 && fromIndex !== toIndex) {
                  onReorder(fromIndex, toIndex);
                }
                setDraggingId(null);
                setDragOverId(null);
              }}
              onDragEnd={() => {
                setDraggingId(null);
                setDragOverId(null);
              }}
              className={`transition-colors ${dragOverId === project.id ? "bg-blue-50" : "hover:bg-gray-50"} ${draggingId === project.id ? "opacity-60" : ""}`}
            >
              <td className="px-3 py-4 whitespace-nowrap">
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    title="Reorder project"
                    aria-label={`Reorder ${project.project_name}`}
                    className="text-gray-500 hover:text-gray-700 p-1 rounded hover:bg-gray-100"
                    onKeyDown={(event) => {
                      if (event.key === "ArrowUp" && canMoveUp) {
                        event.preventDefault();
                        onReorder(index, index - 1);
                      }
                      if (event.key === "ArrowDown" && canMoveDown) {
                        event.preventDefault();
                        onReorder(index, index + 1);
                      }
                    }}
                  >
                    <GripVertical size={16} />
                  </button>
                  <div className="flex flex-col">
                    <button
                      type="button"
                      title="Move up"
                      aria-label={`Move ${project.project_name} up`}
                      disabled={!canMoveUp}
                      onClick={() => onReorder(index, index - 1)}
                      className="text-gray-500 hover:text-gray-700 p-0.5 rounded hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <ArrowUp size={12} />
                    </button>
                    <button
                      type="button"
                      title="Move down"
                      aria-label={`Move ${project.project_name} down`}
                      disabled={!canMoveDown}
                      onClick={() => onReorder(index, index + 1)}
                      className="text-gray-500 hover:text-gray-700 p-0.5 rounded hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <ArrowDown size={12} />
                    </button>
                  </div>
                </div>
              </td>
              <td 
                className="px-6 py-4 whitespace-nowrap cursor-pointer"
                onClick={() => router.push(`/project?projectId=${project.id}`)}
              >
                <div className="text-sm font-medium text-blue-600 hover:text-blue-800 hover:underline">
                  {project.project_name}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-gray-500 max-w-xs truncate" title={project.project_path}>
                  {project.project_path}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex flex-wrap gap-1">
                  {projectData.languages && projectData.languages.length > 0 ? (
                    projectData.languages.slice(0, 3).map((lang) => (
                      <span
                        key={lang}
                        className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
                      >
                        {lang}
                      </span>
                    ))
                  ) : (
                    <span className="text-sm text-gray-400">None</span>
                  )}
                  {projectData.languages && projectData.languages.length > 3 && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                      +{projectData.languages.length - 3}
                    </span>
                  )}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {formatNumber(projectData.totalFiles)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {formatNumber(projectData.totalLines)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                {project.role ? (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    {project.role}
                  </span>
                ) : (
                  <span className="text-sm text-gray-400">-</span>
                )}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {formatDate(project.created_at || project.scan_timestamp)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <div className="flex items-center justify-end gap-2">
                  <button
                    onClick={() => onView(project.id)}
                    className="text-blue-600 hover:text-blue-900 p-1.5 rounded hover:bg-blue-50 transition-colors"
                    title="View details"
                  >
                    <Eye size={18} />
                  </button>
                  <button
                    onClick={() => onDelete(project.id)}
                    className="text-red-600 hover:text-red-900 p-1.5 rounded hover:bg-red-50 transition-colors"
                    title="Delete project"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </td>
            </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
