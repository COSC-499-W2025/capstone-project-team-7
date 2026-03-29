"use client";

import { useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { RotateCcw } from "lucide-react";
import { formatPeriodLabel } from "@/lib/format-utils";
import type { SkillProgressionMap } from "@/types/project";
import { Button } from "@/components/ui/button";

const SKILL_COLORS = [
  "hsl(214, 86%, 56%)",  // blue (primary)
  "hsl(142, 71%, 45%)",  // green
  "hsl(330, 81%, 60%)",  // pink
  "hsl(38, 92%, 50%)",   // amber
  "hsl(262, 83%, 58%)",  // purple
  "hsl(187, 85%, 43%)",  // cyan
  "hsl(12, 76%, 61%)",   // coral
  "hsl(161, 75%, 41%)",  // teal
];

interface SkillProgressionChartProps {
  skillProgression: SkillProgressionMap;
}

export function SkillProgressionChart({
  skillProgression,
}: SkillProgressionChartProps) {
  // Rank skills by total evidence and pick the top ones by default
  const rankedSkills = useMemo(() => {
    return Object.entries(skillProgression)
      .map(([name, points]) => ({ name, total: points.length }))
      .sort((a, b) => b.total - a.total);
  }, [skillProgression]);

  const allSkillNames = useMemo(
    () => rankedSkills.map((s) => s.name),
    [rankedSkills]
  );

  const [activeSkills, setActiveSkills] = useState<Set<string>>(() => {
    return new Set(allSkillNames.slice(0, 5));
  });

  // Build chart data: one row per period, one column per active skill
  const chartData = useMemo(() => {
    // Collect all periods and per-skill evidence counts per period
    const periodMap = new Map<string, Record<string, number>>();

    for (const skillName of activeSkills) {
      const points = skillProgression[skillName];
      if (!points) continue;
      // Count evidence entries per period (not cumulative)
      const periodCounts = new Map<string, number>();
      for (const pt of points) {
        periodCounts.set(pt.period, (periodCounts.get(pt.period) ?? 0) + 1);
      }
      for (const [period, count] of periodCounts) {
        const row = periodMap.get(period) ?? {};
        row[skillName] = count;
        periodMap.set(period, row);
      }
    }

    return Array.from(periodMap.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([period, skills]) => ({
        period,
        label: formatPeriodLabel(period),
        ...skills,
      }));
  }, [skillProgression, activeSkills]);

  const toggleSkill = (skillName: string) => {
    setActiveSkills((prev) => {
      const next = new Set(prev);
      if (next.has(skillName)) {
        if (next.size > 1) next.delete(skillName);
      } else {
        next.add(skillName);
      }
      return next;
    });
  };

  if (allSkillNames.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No skill progression data available.
      </p>
    );
  }

  const activeList = allSkillNames.filter((n) => activeSkills.has(n));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {activeSkills.size > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setActiveSkills(new Set())}
            className="h-7 text-xs gap-1 text-muted-foreground hover:text-foreground"
          >
            <RotateCcw size={12} />
            Deselect all
          </Button>
        )}
        {allSkillNames.map((name, i) => {
          const isActive = activeSkills.has(name);
          const color = SKILL_COLORS[i % SKILL_COLORS.length];
          return (
            <button
              key={name}
              type="button"
              onClick={() => toggleSkill(name)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
                isActive
                  ? "text-white"
                  : "bg-background text-muted-foreground opacity-50 hover:opacity-75"
              }`}
              style={isActive ? { backgroundColor: color } : undefined}
            >
              {name}
            </button>
          );
        })}
      </div>

      {chartData.length > 0 ? (
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--border))"
              />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false}
                axisLine={{ stroke: "hsl(var(--border))" }}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false}
                axisLine={{ stroke: "hsl(var(--border))" }}
                label={{
                  value: "Evidence count",
                  angle: -90,
                  position: "insideLeft",
                  offset: 10,
                  style: {
                    fontSize: 12,
                    fill: "hsl(var(--muted-foreground))",
                    textAnchor: "middle",
                  },
                }}
                width={58}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (!active || !payload?.length) return null;
                  return (
                    <div className="rounded-lg border border-border bg-card px-3 py-2 text-sm shadow-md">
                      <p className="mb-1 font-semibold text-foreground">
                        {label}
                      </p>
                      {payload.map((entry) => (
                        <p
                          key={entry.dataKey as string}
                          className="flex items-center gap-2"
                        >
                          <span
                            className="inline-block h-2.5 w-2.5 rounded-full"
                            style={{ backgroundColor: entry.color }}
                          />
                          <span className="text-muted-foreground">
                            {entry.dataKey as string}:{" "}
                            <span className="font-medium text-foreground">
                              {entry.value}
                            </span>
                          </span>
                        </p>
                      ))}
                    </div>
                  );
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
              />
              {activeList.map((skillName) => {
                const colorIdx = allSkillNames.indexOf(skillName);
                const color = SKILL_COLORS[colorIdx % SKILL_COLORS.length];
                return (
                  <Line
                    key={skillName}
                    type="monotone"
                    dataKey={skillName}
                    name={skillName}
                    stroke={color}
                    strokeWidth={2}
                    dot={{ r: 4, fill: color, stroke: "hsl(var(--background))", strokeWidth: 2 }}
                    activeDot={{ r: 6, fill: color, stroke: "hsl(var(--background))", strokeWidth: 2 }}
                    connectNulls
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          Select at least one skill to see progression data.
        </p>
      )}
    </div>
  );
}
