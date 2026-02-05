"use client";

import React from "react";
import Link from "next/link";
import { ProjectDetail } from "@/types/project";
import { FileCode, Clock, FolderOpen, ExternalLink } from "lucide-react";

interface RecentScanCardProps {
  project: ProjectDetail;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-lg font-semibold text-gray-900">{value}</p>
    </div>
  );
}

export function RecentScanCard({ project }: RecentScanCardProps) {
  const scanData = project.scan_data || {};
  const summary = scanData.summary || {};
  const rawLanguages = scanData.languages;

  // Extract language names from various formats
  let languages: string[] = [];
  if (Array.isArray(rawLanguages)) {
    if (rawLanguages.length > 0 && typeof rawLanguages[0] === "object") {
      languages = rawLanguages.map((lang: any) => lang.language || lang.name).filter(Boolean);
    } else {
      languages = rawLanguages;
    }
  } else if (typeof rawLanguages === "object" && rawLanguages !== null) {
    languages = Object.keys(rawLanguages);
  } else if (project.languages) {
    languages = project.languages;
  }

  const totalFiles = summary.total_files || project.total_files || 0;
  const totalLines = summary.total_lines || project.total_lines || 0;
  const bytesProcessed = summary.bytes_processed || 0;

  const scanDate = project.scan_timestamp
    ? new Date(project.scan_timestamp).toLocaleString()
    : "Unknown";

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gray-100 rounded-lg">
            <FileCode className="h-5 w-5 text-gray-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{project.project_name}</h3>
            <p className="text-sm text-gray-500 flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {scanDate}
            </p>
          </div>
        </div>
        <Link
          href="/projects"
          className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1 transition-colors"
        >
          View All
          <ExternalLink className="h-4 w-4" />
        </Link>
      </div>

      {/* Stats */}
      <div className="p-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard label="Total Files" value={totalFiles.toLocaleString()} />
          <StatCard label="Total Lines" value={totalLines.toLocaleString()} />
          <StatCard label="Languages" value={languages.length} />
          <StatCard label="Size" value={formatBytes(bytesProcessed)} />
        </div>

        {/* Languages */}
        {languages.length > 0 && (
          <div className="mb-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Languages Detected</h4>
            <div className="flex flex-wrap gap-2">
              {languages.slice(0, 8).map((lang) => (
                <span
                  key={lang}
                  className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                >
                  {lang}
                </span>
              ))}
              {languages.length > 8 && (
                <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm">
                  +{languages.length - 8} more
                </span>
              )}
            </div>
          </div>
        )}

        {/* Project Path */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Project Path</h4>
          <div className="flex items-center gap-2 text-sm text-gray-600 font-mono bg-gray-50 p-2 rounded-lg">
            <FolderOpen className="h-4 w-4 flex-shrink-0" />
            <span className="truncate">{project.project_path}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
