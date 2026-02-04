"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ProjectDetail } from "@/types/project";
import { useState } from "react";
import { 
  FileCode, 
  Code2, 
  GitBranch, 
  Sparkles, 
  FileText, 
  Image, 
  Video 
} from "lucide-react";

interface ProjectDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  project: ProjectDetail | null;
}

type TabId = "overview" | "files" | "languages" | "git" | "skills" | "documents" | "media";

export function ProjectDetailModal({ isOpen, onClose, project }: ProjectDetailModalProps) {
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  if (!project) return null;

  const scanData = project.scan_data || {};
  const files = scanData.files || [];
  
  // Handle languages as either array or object
  let languagesData: Record<string, any> = {};
  const rawLanguages = scanData.languages;
  if (rawLanguages && typeof rawLanguages === 'object') {
    if (Array.isArray(rawLanguages)) {
      // Convert array of language names to object format
      rawLanguages.forEach((lang: string) => {
        languagesData[lang] = { files: 0, lines: 0 };
      });
    } else {
      languagesData = rawLanguages;
    }
  }
  
  const gitAnalysis = scanData.git_analysis || {};
  const skillsAnalysis = scanData.skills_analysis || {};
  const documentsAnalysis = scanData.documents_analysis || [];
  const mediaAnalysis = scanData.media_analysis || [];

  // Simplified view - just overview
  const tabs = [
    { id: "overview" as TabId, label: "Project Details", icon: FileCode },
  ];

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-5xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold">{project.project_name}</DialogTitle>
          <p className="text-sm text-gray-500">{project.project_path}</p>
        </DialogHeader>

        {/* Simplified header - no tabs */}
        <div className="border-b border-gray-200 px-6 py-3">
          <h3 className="text-lg font-semibold text-gray-900">Project Overview</h3>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === "overview" && <OverviewTab project={project} />}
          {activeTab === "files" && <FilesTab files={files} />}
          {activeTab === "languages" && <LanguagesTab languages={languagesData} />}
          {activeTab === "git" && <GitTab gitAnalysis={gitAnalysis} />}
          {activeTab === "skills" && <SkillsTab skillsAnalysis={skillsAnalysis} />}
          {activeTab === "documents" && <DocumentsTab documents={documentsAnalysis} />}
          {activeTab === "media" && <MediaTab media={mediaAnalysis} />}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Overview Tab
function OverviewTab({ project }: { project: ProjectDetail }) {
  const scanData = project.scan_data || {};
  const summary = scanData.summary || {};
  const rawLanguages = scanData.languages;
  
  // Extract language names from various formats
  let languages: string[] = [];
  if (Array.isArray(rawLanguages)) {
    if (rawLanguages.length > 0 && typeof rawLanguages[0] === 'object') {
      // Array of objects with 'language' field
      languages = rawLanguages.map((lang: any) => lang.language || lang.name).filter(Boolean);
    } else {
      // Array of strings
      languages = rawLanguages;
    }
  } else if (typeof rawLanguages === 'object' && rawLanguages !== null) {
    // Object keyed by language name
    languages = Object.keys(rawLanguages);
  } else if (project.languages) {
    languages = project.languages;
  }
  
  const totalFiles = summary.total_files || project.total_files || 0;
  const totalLines = summary.total_lines || project.total_lines || 0;
  const bytesProcessed = summary.bytes_processed || 0;
  
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total Files" value={totalFiles.toLocaleString()} />
        <StatCard label="Total Lines" value={totalLines.toLocaleString()} />
        <StatCard label="Languages" value={languages.length} />
        <StatCard label="Size" value={formatBytes(bytesProcessed)} />
      </div>

      {languages.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold mb-2">Languages Detected</h3>
          <div className="flex flex-wrap gap-2">
            {languages.map((lang) => (
              <span
                key={lang}
                className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
              >
                {lang}
              </span>
            ))}
          </div>
        </div>
      )}

      <div>
        <h3 className="text-sm font-semibold mb-2">Project Path</h3>
        <p className="text-sm text-gray-600 font-mono bg-gray-50 p-2 rounded">{project.project_path}</p>
      </div>
      
      {project.scan_timestamp && (
        <div>
          <h3 className="text-sm font-semibold mb-2">Scanned</h3>
          <p className="text-sm text-gray-600">{new Date(project.scan_timestamp).toLocaleString()}</p>
        </div>
      )}
    </div>
  );
}

// Files Tab
function FilesTab({ files }: { files: any[] }) {
  if (files.length === 0) {
    return <EmptyState message="No files found" />;
  }

  return (
    <div className="space-y-2">
      {files.slice(0, 100).map((file, idx) => (
        <div
          key={idx}
          className="p-3 bg-gray-50 rounded border border-gray-200 hover:bg-gray-100 transition-colors"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{file.path || file.file_path}</p>
              {file.language && (
                <span className="text-xs text-gray-500">{file.language}</span>
              )}
            </div>
            <div className="text-right ml-4">
              {file.lines && <p className="text-xs text-gray-500">{file.lines} lines</p>}
              {file.size_bytes && (
                <p className="text-xs text-gray-500">{formatBytes(file.size_bytes)}</p>
              )}
            </div>
          </div>
        </div>
      ))}
      {files.length > 100 && (
        <p className="text-sm text-gray-500 text-center py-2">
          Showing first 100 of {files.length} files
        </p>
      )}
    </div>
  );
}

// Languages Tab
function LanguagesTab({ languages }: { languages: Record<string, any> }) {
  const entries = Object.entries(languages);
  
  if (entries.length === 0) {
    return <EmptyState message="No language data available" />;
  }

  return (
    <div className="space-y-4">
      {entries.map(([lang, data]) => (
        <div key={lang} className="p-4 bg-gray-50 rounded border border-gray-200">
          <h3 className="font-semibold text-lg mb-2">{lang}</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {data.files && <StatCard label="Files" value={data.files} />}
            {data.lines && <StatCard label="Lines" value={data.lines.toLocaleString()} />}
            {data.bytes && <StatCard label="Size" value={formatBytes(data.bytes)} />}
            {data.percentage && <StatCard label="Percentage" value={`${data.percentage.toFixed(1)}%`} />}
          </div>
        </div>
      ))}
    </div>
  );
}

// Git Tab
function GitTab({ gitAnalysis }: { gitAnalysis: any }) {
  if (!gitAnalysis || Object.keys(gitAnalysis).length === 0) {
    return <EmptyState message="No git analysis available" />;
  }

  const commits = gitAnalysis.commits || [];
  const contributors = gitAnalysis.contributors || [];

  return (
    <div className="space-y-6">
      {contributors.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold mb-3">Contributors</h3>
          <div className="space-y-2">
            {contributors.map((contributor: any, idx: number) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <span className="font-medium">{contributor.name || contributor.email}</span>
                <span className="text-sm text-gray-600">{contributor.commits} commits</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {commits.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold mb-3">Recent Commits</h3>
          <div className="space-y-2">
            {commits.slice(0, 20).map((commit: any, idx: number) => (
              <div key={idx} className="p-3 bg-gray-50 rounded border border-gray-200">
                <p className="text-sm font-medium">{commit.message || commit.subject}</p>
                <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                  <span>{commit.author || commit.author_name}</span>
                  {commit.date && <span>{new Date(commit.date).toLocaleDateString()}</span>}
                  {commit.hash && <span className="font-mono">{commit.hash.substring(0, 7)}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Skills Tab
function SkillsTab({ skillsAnalysis }: { skillsAnalysis: any }) {
  if (!skillsAnalysis || !skillsAnalysis.skills) {
    return <EmptyState message="No skills analysis available" />;
  }

  const skills = skillsAnalysis.skills;
  const categories = Object.keys(skills);

  return (
    <div className="space-y-4">
      {categories.map((category) => (
        <div key={category} className="p-4 bg-gray-50 rounded border border-gray-200">
          <h3 className="font-semibold text-lg mb-3 capitalize">{category.replace(/_/g, " ")}</h3>
          <div className="flex flex-wrap gap-2">
            {skills[category].map((skill: string, idx: number) => (
              <span
                key={idx}
                className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// Documents Tab
function DocumentsTab({ documents }: { documents: any[] }) {
  if (documents.length === 0) {
    return <EmptyState message="No documents analyzed" />;
  }

  return (
    <div className="space-y-3">
      {documents.map((doc, idx) => (
        <div key={idx} className="p-4 bg-gray-50 rounded border border-gray-200">
          <h4 className="font-medium mb-2">{doc.file_name || doc.path}</h4>
          {doc.summary && <p className="text-sm text-gray-700 mb-2">{doc.summary}</p>}
          {doc.content && (
            <p className="text-xs text-gray-600 line-clamp-3">{doc.content}</p>
          )}
        </div>
      ))}
    </div>
  );
}

// Media Tab
function MediaTab({ media }: { media: any[] }) {
  if (media.length === 0) {
    return <EmptyState message="No media files analyzed" />;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {media.map((item, idx) => (
        <div key={idx} className="p-4 bg-gray-50 rounded border border-gray-200">
          <div className="flex items-start gap-3">
            {item.type === "image" ? <Image size={20} /> : <Video size={20} />}
            <div className="flex-1">
              <h4 className="font-medium text-sm">{item.file_name || item.path}</h4>
              {item.analysis && <p className="text-xs text-gray-600 mt-1">{item.analysis}</p>}
              {item.metadata && (
                <div className="mt-2 text-xs text-gray-500">
                  {item.metadata.duration && <span>Duration: {item.metadata.duration}s</span>}
                  {item.metadata.resolution && <span className="ml-2">{item.metadata.resolution}</span>}
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// Helper Components
function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="p-3 bg-white border border-gray-200 rounded">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-12">
      <p className="text-gray-500">{message}</p>
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}
