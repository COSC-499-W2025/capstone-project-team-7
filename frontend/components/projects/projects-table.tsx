"use client";

import { ProjectDetail, ProjectMetadata, ProjectScanData, type ProjectScanLanguageEntry } from "@/types/project";
import { formatDistanceToNow } from "date-fns";
import { Trash2, Eye, FolderOpen } from "lucide-react";
import { useRouter } from "next/navigation";

interface ProjectsTableProps {
  projects: ProjectMetadata[];
  onDelete: (projectId: string) => void;
  onView: (projectId: string) => void;
  rankingMode: "contribution" | "recency";
}

export function ProjectsTable({ projects, onDelete, onView, rankingMode }: ProjectsTableProps) {
  const router = useRouter();

  type ProjectWithOptionalScan = ProjectMetadata & Pick<ProjectDetail, "scan_data">;

  const hasScanData = (project: ProjectMetadata): project is ProjectWithOptionalScan => {
    return "scan_data" in project;
  };

  const languageFromEntry = (entry: ProjectScanLanguageEntry): string | null => {
    if (typeof entry.language === "string") return entry.language;
    if (typeof entry.name === "string") return entry.name;
    return null;
  };

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

  const formatContributionScore = (score?: number) => {
    if (score === undefined || score === null) return "Unranked";
    return score.toFixed(1);
  };

  // Helper to extract data from project, checking both root and scan_data.summary
  const getProjectData = (project: ProjectMetadata) => {
    const scanData: ProjectScanData = hasScanData(project) && project.scan_data ? project.scan_data : {};
    const summary = scanData.summary || {};
    
    // Extract from root first (populated by backend normalization), fallback to scan_data
    const totalFiles = project.total_files && project.total_files > 0
      ? project.total_files
      : (summary.total_files ?? 0);
    const totalLines = project.total_lines && project.total_lines > 0
      ? project.total_lines
      : (summary.total_lines ?? 0);
    
    // Extract languages from various sources
    let languages: string[] = [];
    if (project.languages && project.languages.length > 0) {
      languages = project.languages;
    } else if (scanData.languages) {
      const scanLanguages = scanData.languages;
      if (Array.isArray(scanLanguages)) {
        if (scanLanguages.every((lang) => typeof lang === "string")) {
          languages = scanLanguages;
        } else {
          languages = scanLanguages
            .map((lang) => languageFromEntry(lang as ProjectScanLanguageEntry))
            .filter((lang): lang is string => Boolean(lang));
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
        <FolderOpen className="mx-auto h-12 w-12 text-muted-foreground" />
        <h3 className="mt-4 text-lg font-medium text-foreground">No projects found</h3>
        <p className="mt-2 text-sm text-muted-foreground">Get started by scanning your first project.</p>
      </div>
    );
  }

  return (
    <div className="table-shell overflow-x-auto">
      <table className="min-w-full table-fixed" aria-label={`Projects ranked by ${rankingMode}`}>
        <thead className="bg-muted/45">
          <tr>
            <th scope="col" className="w-[18rem] px-6 py-3.5 text-left text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Project Name
            </th>
            <th scope="col" className="w-[22rem] px-6 py-3.5 text-left text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Path
            </th>
            <th scope="col" className="w-[16rem] px-6 py-3.5 text-left text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Languages
            </th>
            <th scope="col" className="w-[7rem] px-6 py-3.5 text-left text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Files
            </th>
            <th scope="col" className="w-[7rem] px-6 py-3.5 text-left text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Lines
            </th>
            <th scope="col" className="w-[9rem] px-6 py-3.5 text-left text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Role
            </th>
            <th scope="col" className="w-[10rem] px-6 py-3.5 text-left text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Contribution Score
            </th>
            <th scope="col" className="w-[10rem] px-6 py-3.5 text-left text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Scanned
            </th>
            <th scope="col" className="relative w-[7rem] px-6 py-3.5">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody className="bg-card [&_tr+tr]:border-t [&_tr+tr]:border-border/60">
          {projects.map((project) => {
            const projectData = getProjectData(project);

            return (
            <tr
              key={project.id}
              className="transition-colors hover:bg-accent/30"
            >
              <td 
                className="cursor-pointer px-6 py-[18px] align-top"
                onClick={() => router.push(`/project?projectId=${project.id}`)}
              >
                <div className="space-y-1">
                  <div className="text-sm font-semibold text-foreground underline-offset-2 hover:underline">
                    {project.project_name}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {project.primary_contributor || "Scanned project evidence"}
                  </div>
                </div>
              </td>
              <td className="px-6 py-[18px] align-top">
                <div className="max-w-[20rem] truncate text-sm text-muted-foreground" title={project.project_path}>
                  {project.project_path}
                </div>
              </td>
              <td className="px-6 py-[18px] align-top">
                <div className="flex max-w-[16rem] flex-wrap gap-1.5">
                  {projectData.languages && projectData.languages.length > 0 ? (
                    projectData.languages.slice(0, 3).map((lang) => (
                      <span
                        key={lang}
                        className="inline-flex items-center rounded-full bg-muted px-2.5 py-1 text-[11px] font-medium text-foreground"
                      >
                        {lang}
                      </span>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">None</span>
                  )}
                  {projectData.languages && projectData.languages.length > 3 && (
                    <span className="inline-flex items-center rounded-full bg-background px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
                      +{projectData.languages.length - 3}
                    </span>
                  )}
                </div>
              </td>
              <td className="px-6 py-[18px] align-top text-sm font-medium text-foreground">
                {formatNumber(projectData.totalFiles)}
              </td>
              <td className="px-6 py-[18px] align-top text-sm text-muted-foreground">
                {formatNumber(projectData.totalLines)}
              </td>
              <td className="px-6 py-[18px] align-top">
                {project.role ? (
                  <span className="inline-flex items-center rounded-full bg-background px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                    {project.role}
                  </span>
                ) : (
                  <span className="text-sm text-muted-foreground">-</span>
                )}
              </td>
              <td className="px-6 py-[18px] align-top text-sm text-muted-foreground">
                <div className="space-y-1">
                  <span className={project.contribution_score === undefined || project.contribution_score === null ? "text-muted-foreground" : "font-medium text-foreground"}>
                    {formatContributionScore(project.contribution_score)}
                  </span>
                  {project.user_commit_share != null && (
                    <div className="text-xs text-muted-foreground">
                      {Math.round(project.user_commit_share * 100)}% yours
                    </div>
                  )}
                </div>
              </td>
              <td className="px-6 py-[18px] align-top text-sm text-muted-foreground">
                {formatDate(project.created_at || project.scan_timestamp)}
              </td>
              <td className="px-6 py-[18px] text-right align-top text-sm font-medium">
                <div className="flex items-center justify-end gap-2">
                  <button
                    onClick={() => onView(project.id)}
                    className="rounded-full border border-border/70 bg-background/80 p-2 text-foreground transition-colors hover:border-primary/20 hover:bg-accent/70"
                    title="View details"
                  >
                    <Eye size={18} />
                  </button>
                  <button
                    onClick={() => onDelete(project.id)}
                    className="rounded-full border border-red-200/80 bg-red-50/80 p-2 text-destructive transition-colors hover:bg-red-100"
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
