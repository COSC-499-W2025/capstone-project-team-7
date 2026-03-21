"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { SearchInput } from "@/components/ui/search-input";
import {
  Check,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import type {
  ProjectSkillCategoryItem,
  ProjectSkillCategoryEntry,
  SkillEvidenceItem,
  SkillAdoptionEntry,
  RoleProfile,
  SkillGapAnalysis,
  SkillTier,
} from "@/types/project";

const TIER_CONFIG: Record<SkillTier, { label: string; color: string }> = {
  beginner: { label: "Beginner", color: "bg-muted-foreground" },
  intermediate: { label: "Intermediate", color: "bg-foreground" },
  advanced: { label: "Advanced", color: "bg-foreground" },
};

function TierIndicator({ tier, breakdown }: { tier?: SkillTier; breakdown?: { beginner: number; intermediate: number; advanced: number } }) {
  const currentTier = tier && tier in TIER_CONFIG ? tier : "beginner";
  const tiers: SkillTier[] = ["beginner", "intermediate", "advanced"];
  const reachedIndex = tiers.indexOf(currentTier);

  return (
    <div className="flex items-center gap-1">
      {tiers.map((t, i) => {
        const reached = i <= reachedIndex;
        const cfg = TIER_CONFIG[t];
        const count = breakdown?.[t] ?? 0;
        return (
          <div
            key={t}
            title={`${cfg.label}: ${count} evidence`}
            className={`h-2 w-3 rounded-sm transition-colors ${reached ? cfg.color : "bg-muted"}`}
          />
        );
      })}
      <span className={`ml-1 text-xs font-medium ${
        currentTier === "advanced" ? "text-foreground" : currentTier === "intermediate" ? "text-foreground" : "text-muted-foreground"
      }`}>
        {TIER_CONFIG[currentTier].label}
      </span>
    </div>
  );
}

export interface SkillHighlightProps {
  skills: string[];
  saveStatus: "idle" | "success" | "error";
  isSaving: boolean;
  save: (skills: string[]) => void;
  toggle: (skillName: string) => void;
}

export interface SkillFilterProps {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  categoryFilter: string;
  setCategoryFilter: (filter: string) => void;
  filteredByCategory: Record<string, Array<ProjectSkillCategoryItem>>;
  expandedSkillKey: string | null;
  setExpandedSkillKey: (key: string | null) => void;
}

export interface SkillGapAnalysisProps {
  roles: RoleProfile[];
  selectedRole: string;
  result: SkillGapAnalysis | null;
  loading: boolean;
  error: string | null;
  run: (role: string) => void;
}

interface SkillsTabProps {
  highlight: SkillHighlightProps;
  filter: SkillFilterProps;
  gapAnalysis: SkillGapAnalysisProps;
  skillsAnalysis: { success?: boolean };
  skillsByCategory: Record<string, ProjectSkillCategoryEntry[]>;
  totalSkills: number;
  categoryLabel: (key: string) => string;
  getSkillEvidence: (skillName: string) => SkillEvidenceItem[];
  skillAdoptionTimeline: SkillAdoptionEntry[];
}

export function SkillsTab({
  highlight,
  filter,
  gapAnalysis,
  skillsAnalysis,
  skillsByCategory,
  totalSkills,
  categoryLabel,
  getSkillEvidence,
  skillAdoptionTimeline,
}: SkillsTabProps) {
  return (
    <div className="space-y-6">
      {/* Highlighted Skills Section */}
      <Card className="bg-card border-2 border-border rounded-md">
        <CardHeader className="border-b border-border">
          <div className="flex items-center justify-between">
            <CardTitle className="text-xl font-bold text-foreground">
              Highlighted Skills
            </CardTitle>
            {highlight.saveStatus === "success" && (
              <span className="flex items-center gap-1.5 text-sm text-muted-foreground font-medium">
                <Check size={16} />
                Saved
              </span>
            )}
            {highlight.saveStatus === "error" && (
              <span className="flex items-center gap-1.5 text-sm text-destructive font-medium">
                <AlertCircle size={16} />
                Save failed
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Select skills you want to emphasize on your resume or portfolio
          </p>
        </CardHeader>
        <CardContent className="p-6">
          {highlight.skills.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No skills highlighted yet. Select skills below to highlight them.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {highlight.skills.map((skill) => (
                <span
                  key={`highlighted-${skill}`}
                  className="px-3 py-1.5 rounded-md bg-muted text-foreground border border-border text-sm font-medium flex items-center gap-2"
                >
                  {skill}
                </span>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* All Skills with Selection */}
      <Card className="bg-card border-2 border-border rounded-md">
        <CardHeader className="border-b border-border">
          <div className="flex items-center justify-between">
            <CardTitle className="text-xl font-bold text-foreground">
              Select Skills to Highlight
            </CardTitle>
            <Button
              onClick={() => highlight.save(highlight.skills)}
              disabled={highlight.isSaving}
              size="sm"
              className="bg-foreground hover:bg-foreground/90"
            >
              {highlight.isSaving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Check className="mr-2 h-4 w-4" />
                  Save Highlights
                </>
              )}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-6 space-y-4">
          {skillsAnalysis.success === false && (
            <p className="text-sm text-muted-foreground">
              Skills analysis did not complete for this scan.
            </p>
          )}

          {skillsAnalysis.success !== false &&
            Object.keys(skillsByCategory).length === 0 && (
              <p className="text-sm text-muted-foreground">
                No skills analysis available yet. Run a scan with skills extraction enabled.
              </p>
            )}

          {Object.keys(skillsByCategory).length > 0 && (
            <div className="space-y-6">
              <div className="flex flex-wrap gap-3">
                <span className="px-3 py-1 rounded-md bg-foreground text-background text-xs font-semibold">
                  Total skills · {totalSkills}
                </span>
                <span className="px-3 py-1 rounded-md bg-muted text-foreground border border-border text-xs font-semibold">
                  Highlighted · {highlight.skills.length}
                </span>
                <span className="px-3 py-1 rounded-md bg-muted text-foreground border border-border text-xs font-semibold">
                  Categories · {Object.keys(skillsByCategory).length}
                </span>
              </div>

              {/* Category average proficiency bars */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(skillsByCategory).map(([category, skills]) => {
                  const items = skills;
                  const scores = items
                    .map((s) => (typeof s === "object" ? s.proficiency_score ?? 0 : 0))
                    .filter((v) => v > 0);
                  const avg = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
                  return (
                    <div key={`avg-${category}`} className="bg-muted rounded-md p-3">
                      <p className="text-xs font-medium text-muted-foreground truncate">{categoryLabel(category)}</p>
                      <div className="mt-1.5 w-full bg-muted rounded-md h-2">
                        <div
                          className="bg-foreground h-2 rounded-md transition-all"
                          style={{ width: `${Math.round(avg * 100)}%` }}
                        />
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">{Math.round(avg * 100)}%</p>
                    </div>
                  );
                })}
              </div>

              {/* Search and filter */}
              <div className="flex flex-col sm:flex-row gap-3">
                <SearchInput
                  placeholder="Search skills..."
                  value={filter.searchQuery}
                  onChange={filter.setSearchQuery}
                  onClear={() => filter.setSearchQuery("")}
                  className="sm:max-w-xs"
                />
                <select
                  value={filter.categoryFilter}
                  onChange={(e) => filter.setCategoryFilter(e.target.value)}
                  className="text-sm border border-border rounded-md px-3 py-2 bg-background focus:outline-none focus:ring-2 focus:ring-foreground"
                >
                  <option value="all">All categories</option>
                  {Object.keys(skillsByCategory).map((cat) => (
                    <option key={cat} value={cat}>{categoryLabel(cat)}</option>
                  ))}
                </select>
              </div>

              {Object.entries(filter.filteredByCategory).map(([category, skills]) => (
                <div key={category} className="rounded-md bg-muted/70 p-4">
                  <p className="text-sm font-semibold text-foreground mb-3">
                    {categoryLabel(category)}
                  </p>
                  <div className="space-y-2">
                    {skills.map(
                      (skill) => {
                        const skillName = typeof skill === "string" ? skill : skill.name ?? "";
                        const isHighlighted = highlight.skills.includes(skillName);
                        const description = typeof skill === "object" ? skill.description : undefined;
                        const profScore = typeof skill === "object" ? skill.proficiency_score ?? 0 : 0;
                        const highestTier = typeof skill === "object" ? skill.highest_tier : undefined;
                        const tierBreakdown = typeof skill === "object" ? skill.tier_breakdown : undefined;
                        const evidence = getSkillEvidence(skillName);
                        const skillKey = `${category}::${skillName}`;
                        const isExpanded = filter.expandedSkillKey === skillKey;

                        return (
                          <div
                            key={`${category}-${skillName}`}
                            className={`rounded-md transition-colors ${
                              isHighlighted
                                ? "bg-muted ring-1 ring-border"
                                : "bg-background/80 hover:bg-background"
                            }`}
                          >
                            <div className="flex items-center gap-3 p-2">
                              <Checkbox
                                id={`skill-${category}-${skillName}`}
                                checked={isHighlighted}
                                onChange={() => highlight.toggle(skillName)}
                                className="border-border"
                              />
                              <button
                                type="button"
                                onClick={() => filter.setExpandedSkillKey(isExpanded ? null : skillKey)}
                                className="flex-1 text-left"
                              >
                                <span className="text-sm font-medium text-foreground">
                                  {skillName}
                                </span>
                                {description && (
                                  <span className="block text-xs text-muted-foreground mt-0.5">
                                    {description}
                                  </span>
                                )}
                              </button>
                              <div className="flex items-center gap-2">
                                {/* Tier depth indicator */}
                                {highestTier && (
                                  <TierIndicator tier={highestTier} breakdown={tierBreakdown} />
                                )}
                                {/* Proficiency bar */}
                                {profScore > 0 && !highestTier && (
                                  <div className="flex items-center gap-1.5">
                                    <div className="w-16 bg-muted rounded-md h-1.5">
                                      <div
                                        className={`h-1.5 rounded-full ${
                                          profScore >= 0.8 ? "bg-foreground" : profScore >= 0.6 ? "bg-foreground" : profScore >= 0.4 ? "bg-muted-foreground" : "bg-muted-foreground"
                                        }`}
                                        style={{ width: `${Math.round(profScore * 100)}%` }}
                                      />
                                    </div>
                                    <span className="text-xs text-muted-foreground w-8">{Math.round(profScore * 100)}%</span>
                                  </div>
                                )}
                                {evidence.length > 0 && (
                                  <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded-md">
                                    {evidence.length}
                                  </span>
                                )}
                                {isHighlighted && (
                                  <Check size={16} className="text-foreground" />
                                )}
                                {evidence.length > 0 && (
                                  isExpanded ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />
                                )}
                              </div>
                            </div>
                            {/* Evidence panel */}
                            {isExpanded && evidence.length > 0 && (
                              <div className="mx-2 mb-2 rounded-md border-l-2 border-border bg-background px-8 py-2.5 space-y-1.5">
                                {evidence.slice(0, 5).map((ev, idx) => (
                                  <div key={`${ev.file ?? ""}:${ev.line ?? ""}:${idx}`} className="text-xs text-muted-foreground flex items-start gap-2">
                                    <span className="text-muted-foreground mt-0.5">-</span>
                                    <div>
                                      <span>{ev.description || ev.type || "Evidence"}</span>
                                      {ev.file && (
                                        <span className="ml-1 text-muted-foreground font-mono">
                                          {ev.file}{ev.line ? `:${ev.line}` : ""}
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                ))}
                                {evidence.length > 5 && (
                                  <p className="text-xs text-muted-foreground italic">
                                    + {evidence.length - 5} more evidence items
                                  </p>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      }
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Skill Adoption Timeline */}
      {skillAdoptionTimeline.length > 0 && (
        <Card className="bg-card border-2 border-border rounded-md">
          <CardHeader className="border-b border-border">
            <CardTitle className="text-xl font-bold text-foreground">
              Skill Adoption Timeline
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              When each skill was first detected in the codebase
            </p>
          </CardHeader>
          <CardContent className="p-6">
            <div className="space-y-3">
              {skillAdoptionTimeline.map((entry) => (
                <div
                  key={`${entry.skill_name}::${entry.first_used_period ?? ""}`}
                  className="flex items-center gap-4 py-2 border-b border-border last:border-0"
                >
                  <span className="text-xs font-mono text-gray-400 w-20 shrink-0">
                    {entry.first_used_period || "Unknown"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">
                      {entry.skill_name}
                    </p>
                    <p className="text-xs text-muted-foreground truncate">
                      {categoryLabel(entry.category ?? "")}
                      {entry.file ? ` · ${entry.file}` : ""}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <div className="w-12 bg-muted rounded-md h-1.5">
                      <div
                        className="bg-foreground h-1.5 rounded-md"
                        style={{ width: `${Math.round((entry.current_proficiency ?? 0) * 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {entry.total_usage ?? 0} uses
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Gap Analysis */}
      <Card className="bg-card border-2 border-border rounded-md">
        <CardHeader className="border-b border-border">
          <CardTitle className="text-xl font-bold text-foreground">
            Skill Gap Analysis
          </CardTitle>
          <p className="text-sm text-muted-foreground mt-1">
            Compare detected skills against a target role profile
          </p>
        </CardHeader>
        <CardContent className="p-6 space-y-4">
          <div className="flex items-center gap-3">
            <select
              className="border border-border rounded-md px-3 py-2 text-sm bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-400"
              value={gapAnalysis.selectedRole}
              onChange={(e) => gapAnalysis.run(e.target.value)}
            >
              <option value="">Select a role...</option>
              {gapAnalysis.roles.map((r) => (
                <option key={r.key} value={r.key}>
                  {r.label}
                </option>
              ))}
            </select>
            {gapAnalysis.loading && (
              <Loader2 size={16} className="animate-spin text-gray-400" />
            )}
          </div>

          {gapAnalysis.error && (
            <p className="text-sm text-destructive">{gapAnalysis.error}</p>
          )}

          {gapAnalysis.result && (
            <div className="space-y-4">
              {/* Weighted coverage bar */}
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="font-medium text-gray-900">
                    Weighted Coverage for {gapAnalysis.result.role_label}
                  </span>
                  <span className="text-gray-500">
                    {gapAnalysis.result.weighted_coverage_percent ?? gapAnalysis.result.coverage_percent}%
                  </span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full transition-all ${
                      (gapAnalysis.result.weighted_coverage_percent ?? gapAnalysis.result.coverage_percent) >= 75
                        ? "bg-emerald-600"
                        : (gapAnalysis.result.weighted_coverage_percent ?? gapAnalysis.result.coverage_percent) >= 40
                          ? "bg-amber-500"
                          : "bg-red-500"
                    }`}
                    style={{ width: `${gapAnalysis.result.weighted_coverage_percent ?? gapAnalysis.result.coverage_percent}%` }}
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Critical skills are weighted 3x, recommended 2x, nice-to-have 1x
                </p>
              </div>

              {/* Matched skills with importance badges */}
              {gapAnalysis.result.matched.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                    Matched ({gapAnalysis.result.matched.length})
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {gapAnalysis.result.matched.map((s) => {
                      const name = typeof s === "string" ? s : s.name;
                      const importance = typeof s === "object" ? s.importance : undefined;
                      return (
                        <span
                          key={name}
                          className="px-2.5 py-1 rounded-md bg-muted text-foreground border border-border text-xs font-medium inline-flex items-center gap-1"
                        >
                          {name}
                          {importance && (
                            <span className={`text-[10px] font-semibold uppercase ${
                              importance === "critical" ? "text-foreground" : importance === "recommended" ? "text-muted-foreground" : "text-muted-foreground"
                            }`}>
                              · {importance === "nice_to_have" ? "bonus" : importance}
                            </span>
                          )}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Missing skills with importance badges */}
              {gapAnalysis.result.missing.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                    Missing ({gapAnalysis.result.missing.length})
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {gapAnalysis.result.missing.map((s) => {
                      const name = typeof s === "string" ? s : s.name;
                      const importance = typeof s === "object" ? s.importance : undefined;
                      return (
                        <span
                          key={name}
                          className={`px-2.5 py-1 rounded-full text-xs font-medium inline-flex items-center gap-1 ${
                            importance === "critical" ? "bg-muted text-foreground border border-border" : importance === "recommended" ? "bg-muted text-foreground border border-border" : "bg-muted text-muted-foreground border border-border"
                          }`}
                        >
                          {name}
                          {importance && (
                            <span className={`text-[10px] font-semibold uppercase ${
                              importance === "critical" ? "text-red-600" : importance === "recommended" ? "text-amber-600" : "text-gray-400"
                            }`}>
                              · {importance === "nice_to_have" ? "bonus" : importance}
                            </span>
                          )}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Extra skills */}
              {gapAnalysis.result.extra.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                    Additional Skills ({gapAnalysis.result.extra.length})
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {gapAnalysis.result.extra.map((s) => (
                      <span
                        key={s}
                        className="px-2.5 py-1 rounded-md bg-muted text-foreground border border-border text-xs font-medium"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {!gapAnalysis.selectedRole && !gapAnalysis.result && (
            <p className="text-sm text-gray-400">
              Select a role above to see how your project skills compare.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
