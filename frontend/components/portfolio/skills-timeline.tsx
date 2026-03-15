"use client";

import React, { useMemo } from "react";
import type { SkillsTimelineItem } from "@/types/portfolio";

interface SkillsTimelineProps {
  data: SkillsTimelineItem[];
}

function formatPeriod(label: string): string {
  const [year, month] = label.split("-");
  const months = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];
  const m = parseInt(month, 10);
  return `${months[m] || month} ${year}`;
}

export const SkillsTimeline: React.FC<SkillsTimelineProps> = ({ data }) => {
  const maxCommits = useMemo(
    () => Math.max(1, ...data.map((d) => d.commits)),
    [data],
  );

  if (data.length === 0) {
    return (
      <div className="text-sm text-gray-400 italic py-4">
        No skills timeline data available yet. Scan projects with git history to see skill progression.
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
      {data.map((item) => {
        const barWidth = Math.max(4, (item.commits / maxCommits) * 100);
        return (
          <div key={item.period_label} className="group">
            <div className="flex items-center gap-3">
              {/* Period label */}
              <div className="w-20 flex-shrink-0 text-xs text-gray-500 text-right">
                {formatPeriod(item.period_label)}
              </div>

              {/* Commit bar */}
              <div className="flex-1 flex items-center gap-2">
                <div className="flex-1 h-5 bg-gray-100 rounded overflow-hidden">
                  <div
                    className="h-full bg-indigo-500 rounded transition-all duration-300"
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
                <span className="text-xs text-gray-400 w-8 text-right flex-shrink-0">
                  {item.commits}
                </span>
              </div>
            </div>

            {/* Skill badges */}
            {item.skills.length > 0 && (
              <div className="ml-[92px] mt-1 flex flex-wrap gap-1">
                {item.skills.slice(0, 8).map((skill) => (
                  <span
                    key={skill}
                    className="inline-block px-1.5 py-0.5 text-[10px] font-medium bg-indigo-50 text-indigo-600 rounded"
                  >
                    {skill}
                  </span>
                ))}
                {item.skills.length > 8 && (
                  <span className="text-[10px] text-gray-400">
                    +{item.skills.length - 8} more
                  </span>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
