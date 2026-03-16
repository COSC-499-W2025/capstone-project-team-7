"use client";

import type { ProjectMetadata } from "@/types/project";
import { formatDistanceToNow } from "date-fns";
import { ArrowUpRight, Eye, FolderOpen, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";

interface ProjectsTableProps {
  projects: ProjectMetadata[];
  onDelete: (projectId: string) => void;
  onView: (projectId: string) => void;
  rankingMode: "contribution" | "recency";
}

type ProjectSummary = {
  totalFiles: number;
  totalLines: number;
  languages: string[];
};

function formatDate(dateString?: string) {
  if (!dateString) return "N/A";
  try {
    return formatDistanceToNow(new Date(dateString), { addSuffix: true });
  } catch {
    return dateString;
  }
}

function formatNumber(num?: number) {
  if (num === undefined || num === null) return "0";
  return num.toLocaleString();
}

function formatContributionScore(score?: number) {
  if (score === undefined || score === null) return "Unranked";
  return score.toFixed(1);
}

function getProjectData(project: ProjectMetadata): ProjectSummary {
  const scanData = (project as ProjectMetadata & { scan_data?: Record<string, unknown> | null }).scan_data ?? {};
  const summary =
    scanData && typeof scanData === "object" && !Array.isArray(scanData)
      ? ((scanData as Record<string, unknown>).summary as Record<string, unknown> | undefined) ?? {}
      : {};

  const totalFiles =
    typeof project.total_files === "number" && project.total_files > 0
      ? project.total_files
      : typeof summary.total_files === "number"
        ? summary.total_files
        : 0;
  const totalLines =
    typeof project.total_lines === "number" && project.total_lines > 0
      ? project.total_lines
      : typeof summary.total_lines === "number"
        ? summary.total_lines
        : 0;

  let languages: string[] = [];
  if (Array.isArray(project.languages) && project.languages.length > 0) {
    languages = project.languages;
  } else if (scanData && typeof scanData === "object" && !Array.isArray(scanData)) {
    const rawLanguages = (scanData as Record<string, unknown>).languages;
    if (Array.isArray(rawLanguages)) {
      languages = rawLanguages
        .map((lang) => {
          if (typeof lang === "string") return lang;
          if (lang && typeof lang === "object") {
            const record = lang as Record<string, unknown>;
            if (typeof record.language === "string") return record.language;
            if (typeof record.name === "string") return record.name;
          }
          return null;
        })
        .filter((lang): lang is string => Boolean(lang));
    } else if (rawLanguages && typeof rawLanguages === "object") {
      languages = Object.keys(rawLanguages);
    }
  }

  return {
    totalFiles,
    totalLines,
    languages,
  };
}

function renderPill(
  label: string,
  value: string,
  tone: "neutral" | "accent" | "success" = "neutral",
) {
  const toneClass =
    tone === "accent"
      ? "border-sky-200 bg-sky-50 text-sky-700"
      : tone === "success"
        ? "border-emerald-200 bg-emerald-50 text-emerald-700"
        : "border-slate-200 bg-slate-50 text-slate-700";

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium ${toneClass}`}
    >
      <span className="text-slate-500">{label}</span>
      <span className="text-current">{value}</span>
    </span>
  );
}

export function ProjectsTable({ projects, onDelete, onView, rankingMode }: ProjectsTableProps) {
  const router = useRouter();

  if (projects.length === 0) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50/80 px-8 py-16 text-center">
        <FolderOpen className="mx-auto h-12 w-12 text-slate-400" />
        <h3 className="mt-4 text-lg font-semibold text-slate-900">No projects found</h3>
        <p className="mt-2 text-sm text-slate-500">Scan a project to start building your project library.</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_10px_40px_rgba(15,23,42,0.04)]">
      <div className="overflow-x-auto">
        <table className="min-w-[1200px] w-full border-collapse">
          <thead className="bg-slate-50/90">
            <tr className="border-b border-slate-200">
              <th scope="col" className="w-[44%] px-6 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                Project
              </th>
              <th scope="col" className="w-[26%] px-6 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                Summary
              </th>
              <th scope="col" className="w-[16%] px-6 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                Status
              </th>
              <th scope="col" className="w-[10%] px-6 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                Last Scan
              </th>
              <th scope="col" className="w-[6%] px-6 py-4 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {projects.map((project) => {
              const projectData = getProjectData(project);
              const lastScan = project.created_at || project.scan_timestamp;

              return (
                <tr
                  key={project.id}
                  className="group transition-colors hover:bg-slate-50/80"
                >
                  <td className="px-6 py-5 align-top">
                    <div className="space-y-3">
                      <button
                        type="button"
                        onClick={() => router.push(`/project?projectId=${project.id}`)}
                        className="inline-flex items-center gap-2 text-left"
                      >
                        <span className="text-base font-semibold tracking-tight text-slate-950 transition-colors group-hover:text-slate-700">
                          {project.project_name}
                        </span>
                        <ArrowUpRight className="h-4 w-4 text-slate-400 transition-colors group-hover:text-slate-600" />
                      </button>
                      <p
                        className="max-w-xl truncate text-sm text-slate-500"
                        title={project.project_path}
                      >
                        {project.project_path}
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {projectData.languages.length > 0 ? (
                          <>
                            {projectData.languages.slice(0, 4).map((lang) => (
                              <span
                                key={lang}
                                className="inline-flex items-center rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700"
                              >
                                {lang}
                              </span>
                            ))}
                            {projectData.languages.length > 4 && (
                              <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                                +{projectData.languages.length - 4}
                              </span>
                            )}
                          </>
                        ) : (
                          <span className="text-sm text-slate-400">No languages detected</span>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-5 align-top">
                    <div className="grid grid-cols-3 gap-3">
                      <div className="min-w-[96px] rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3">
                        <p className="text-[11px] font-medium text-slate-500">Files</p>
                        <p className="mt-1 text-base font-semibold text-slate-950">
                          {formatNumber(projectData.totalFiles)}
                        </p>
                      </div>
                      <div className="min-w-[96px] rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3">
                        <p className="text-[11px] font-medium text-slate-500">Lines</p>
                        <p className="mt-1 text-base font-semibold text-slate-950">
                          {formatNumber(projectData.totalLines)}
                        </p>
                      </div>
                      <div className="min-w-[96px] rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3">
                        <p className="text-[11px] font-medium text-slate-500">Languages</p>
                        <p className="mt-1 text-base font-semibold text-slate-950">
                          {formatNumber(projectData.languages.length)}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-5 align-top">
                    <div className="flex max-w-[220px] flex-wrap gap-2">
                      {project.role
                        ? renderPill("Role", project.role, "success")
                        : renderPill("Role", "Unset")}
                      {renderPill(
                        rankingMode === "contribution" ? "Rank" : "Score",
                        formatContributionScore(project.contribution_score),
                        rankingMode === "contribution" ? "accent" : "neutral",
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-5 align-top">
                    <div className="space-y-1">
                      <p className="text-sm font-medium text-slate-900">{formatDate(lastScan)}</p>
                      {lastScan && (
                        <p className="text-xs text-slate-500">
                          {new Date(lastScan).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-5 align-top">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => onView(project.id)}
                        className="rounded-full border border-slate-200 bg-white p-2 text-slate-600 transition-colors hover:border-slate-300 hover:bg-slate-100 hover:text-slate-900"
                        title="View details"
                      >
                        <Eye size={17} />
                      </button>
                      <button
                        onClick={() => onDelete(project.id)}
                        className="rounded-full border border-red-200 bg-white p-2 text-red-600 transition-colors hover:bg-red-50 hover:text-red-700"
                        title="Delete project"
                      >
                        <Trash2 size={17} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
