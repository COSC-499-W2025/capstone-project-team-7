"use client";

import { Filter, RotateCcw } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { JobFilters } from "@/types/job";

interface JobFiltersProps {
  filters: JobFilters;
  onFiltersChange: (filters: Partial<JobFilters>) => void;
  onReset: () => void;
}

const DATE_PRESETS = [
  { label: "All", value: "" },
  { label: "Last 24h", value: "24h" },
  { label: "Last Week", value: "7d" },
  { label: "Last Month", value: "30d" },
] as const;

function getPostedAfterDate(preset: string): string | undefined {
  if (!preset) return undefined;
  const now = new Date();
  switch (preset) {
    case "24h":
      now.setDate(now.getDate() - 1);
      break;
    case "7d":
      now.setDate(now.getDate() - 7);
      break;
    case "30d":
      now.setDate(now.getDate() - 30);
      break;
    default:
      return undefined;
  }
  return now.toISOString();
}

function getActivePreset(postedAfter?: string): string {
  if (!postedAfter) return "";
  const posted = new Date(postedAfter).getTime();
  const now = Date.now();
  const diffHours = (now - posted) / (1000 * 60 * 60);
  if (diffHours <= 25) return "24h";
  if (diffHours <= 169) return "7d";
  if (diffHours <= 745) return "30d";
  return "";
}

export function JobFilterPanel({ filters, onFiltersChange, onReset }: JobFiltersProps) {
  const activePreset = getActivePreset(filters.posted_after);

  return (
    <div className="flex flex-col gap-5">
      {/* Search */}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="filter-search">Search</Label>
        <Input
          id="filter-search"
          placeholder="Title or company..."
          value={filters.search ?? ""}
          onChange={(e) => onFiltersChange({ search: e.target.value || undefined })}
        />
      </div>

      {/* Source */}
      <div className="flex flex-col gap-1.5">
        <Label>Source</Label>
        <Select
          value={filters.source ?? "all"}
          onValueChange={(val) =>
            onFiltersChange({ source: val === "all" ? undefined : (val as JobFilters["source"]) })
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="All sources" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="linkedin">LinkedIn</SelectItem>
            <SelectItem value="indeed">Indeed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Remote */}
      <div className="flex items-center justify-between gap-2">
        <Label htmlFor="filter-remote">Remote Only</Label>
        <Switch
          id="filter-remote"
          checked={filters.is_remote ?? false}
          onCheckedChange={(checked) =>
            onFiltersChange({ is_remote: checked || undefined })
          }
        />
      </div>

      {/* Job Type */}
      <div className="flex flex-col gap-1.5">
        <Label>Job Type</Label>
        <Select
          value={filters.job_type ?? "all"}
          onValueChange={(val) =>
            onFiltersChange({ job_type: val === "all" ? undefined : (val as JobFilters["job_type"]) })
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="All types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="full-time">Full-time</SelectItem>
            <SelectItem value="part-time">Part-time</SelectItem>
            <SelectItem value="internship">Internship</SelectItem>
            <SelectItem value="contract">Contract</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Experience Level */}
      <div className="flex flex-col gap-1.5">
        <Label>Experience Level</Label>
        <Select
          value={filters.experience_level ?? "all"}
          onValueChange={(val) =>
            onFiltersChange({
              experience_level: val === "all" ? undefined : (val as JobFilters["experience_level"]),
            })
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="All levels" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="entry">Entry</SelectItem>
            <SelectItem value="mid">Mid</SelectItem>
            <SelectItem value="senior">Senior</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Salary Range */}
      <div className="flex flex-col gap-1.5">
        <Label>Salary Range</Label>
        <div className="flex items-center gap-2">
          <Input
            type="number"
            placeholder="Min"
            value={filters.salary_min ?? ""}
            onChange={(e) =>
              onFiltersChange({
                salary_min: e.target.value ? Number(e.target.value) : undefined,
              })
            }
          />
          <span className="text-xs text-muted-foreground">-</span>
          <Input
            type="number"
            placeholder="Max"
            value={filters.salary_max ?? ""}
            onChange={(e) =>
              onFiltersChange({
                salary_max: e.target.value ? Number(e.target.value) : undefined,
              })
            }
          />
        </div>
      </div>

      {/* Posted Date Presets */}
      <div className="flex flex-col gap-1.5">
        <Label>Posted</Label>
        <div className="grid grid-cols-4 gap-1">
          {DATE_PRESETS.map((preset) => (
            <button
              key={preset.value}
              type="button"
              onClick={() =>
                onFiltersChange({ posted_after: getPostedAfterDate(preset.value) })
              }
              className={`rounded-lg px-2 py-1.5 text-xs font-medium transition-colors ${
                activePreset === preset.value
                  ? "bg-primary/15 text-primary border border-primary/30"
                  : "bg-card border border-border/60 text-muted-foreground hover:bg-accent/70 hover:text-foreground"
              }`}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Reset */}
      <Button variant="ghost" size="sm" onClick={onReset} className="mt-1 w-full">
        <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
        Reset Filters
      </Button>
    </div>
  );
}
