import React from "react";
import {
  Sparkles,
  Code2,
  GitBranch,
  FileText,
  Image as ImageIcon,
  BookOpen,
  Lightbulb,
} from "lucide-react";
import type { ProjectAiAnalysisCategory } from "@/types/project";

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  code_analysis:     <Code2 size={15} />,
  git_analysis:      <GitBranch size={15} />,
  pdf_analysis:      <FileText size={15} />,
  document_analysis: <BookOpen size={15} />,
  media_analysis:    <ImageIcon size={15} />,
  skills_analysis:   <Lightbulb size={15} />,
  skills_progress:   <Lightbulb size={15} />,
};

export function CategoryCard({ cat }: { cat: ProjectAiAnalysisCategory }) {
  const icon = CATEGORY_ICONS[cat.category] ?? <Sparkles size={15} />;
  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 p-4 space-y-2">
      <p className="text-sm font-semibold text-gray-800 flex items-center gap-1.5">
        {icon} {cat.label}
      </p>
      {cat.summary && (
        <p className="text-sm text-gray-600 leading-relaxed">{cat.summary}</p>
      )}
      {cat.insights && cat.insights.length > 0 && (
        <ul className="space-y-1 list-disc list-inside text-sm text-gray-700">
          {cat.insights.map((ins, i) => (
            <li key={i}>{ins}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
