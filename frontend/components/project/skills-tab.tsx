"use client";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { SearchInput } from "@/components/ui/search-input";
import { Spinner } from "@/components/ui/spinner";
import {
  Section,
  SectionActions,
  SectionBody,
  SectionDescription,
  SectionHeader,
  SectionHeading,
  SectionInset,
  SectionTitle,
} from "@/components/ui/section";
import {
  Check,
  AlertCircle,
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

function TierIndicator({
  tier,
  breakdown,
}: {
  tier?: SkillTier;
  breakdown?: { beginner: number; intermediate: number; advanced: number };
}) {
  const currentTier = tier && tier in TIER_CONFIG ? tier : "beginner";
  const tiers: SkillTier[] = ["beginner", "intermediate", "advanced"];
  const reachedIndex = tiers.indexOf(currentTier);

  return (
    <div className="flex items-center gap-1">
      {tiers.map((value, index) => {
        const reached = index <= reachedIndex;
        const config = TIER_CONFIG[value];
        const count = breakdown?.[value] ?? 0;
        return (
          <div
            key={value}
            title={`${config.label}: ${count} evidence`}
            className={`h-2 w-3 rounded-sm transition-colors ${reached ? config.color : "bg-background"}`}
          />
        );
      })}
      <span className="ml-1 text-xs font-medium text-muted-foreground">
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

function SaveStatus({ status }: { status: SkillHighlightProps["saveStatus"] }) {
  if (status === "success") {
    return (
      <span className="flex items-center gap-1.5 text-sm font-medium text-foreground">
        <Check size={16} />
        Saved
      </span>
    );
  }

  if (status === "error") {
    return (
      <span className="flex items-center gap-1.5 text-sm font-medium text-destructive">
        <AlertCircle size={16} />
        Save failed
      </span>
    );
  }

  return null;
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
  const hasSkills = Object.keys(skillsByCategory).length > 0;

  return (
    <div className="space-y-6">
      <Section>
        <SectionHeader>
          <SectionHeading>
            <SectionTitle>Skills Library</SectionTitle>
            <SectionDescription>
              Review detected skills, highlight the ones worth promoting, and inspect supporting evidence.
            </SectionDescription>
          </SectionHeading>
          <SectionActions>
            <SaveStatus status={highlight.saveStatus} />
            <Button
              onClick={() => highlight.save(highlight.skills)}
              disabled={highlight.isSaving}
              size="sm"
            >
              {highlight.isSaving ? (
                <>
                  <Spinner size="md" />
                  Saving...
                </>
              ) : (
                <>
                  <Check className="h-4 w-4" />
                  Save Highlights
                </>
              )}
            </Button>
          </SectionActions>
        </SectionHeader>

        <SectionBody className="space-y-5 pt-0">
          <SectionInset className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-foreground">Highlighted Skills</p>
                <p className="text-sm text-muted-foreground">
                  Skills selected for resume and portfolio emphasis.
                </p>
              </div>
              <span className="rounded-full bg-background px-3 py-1 text-xs font-semibold text-muted-foreground">
                {highlight.skills.length} selected
              </span>
            </div>

            {highlight.skills.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No skills highlighted yet. Select skills below to highlight them.
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {highlight.skills.map((skill) => (
                  <span
                    key={`highlighted-${skill}`}
                    className="inline-flex items-center gap-2 rounded-full bg-background px-3 py-1.5 text-sm font-medium text-foreground"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            )}
          </SectionInset>

          {skillsAnalysis.success === false && (
            <p className="text-sm text-muted-foreground">
              Skills analysis did not complete for this scan.
            </p>
          )}

          {skillsAnalysis.success !== false && !hasSkills && (
            <p className="text-sm text-muted-foreground">
              No skills analysis available yet. Run a scan with skills extraction enabled.
            </p>
          )}

          {hasSkills && (
            <div className="space-y-5">
              <div className="flex flex-wrap gap-2">
                <span className="rounded-full bg-foreground px-3 py-1 text-xs font-semibold text-background">
                  Total skills · {totalSkills}
                </span>
                <span className="rounded-full bg-muted px-3 py-1 text-xs font-semibold text-foreground">
                  Highlighted · {highlight.skills.length}
                </span>
                <span className="rounded-full bg-muted px-3 py-1 text-xs font-semibold text-foreground">
                  Categories · {Object.keys(skillsByCategory).length}
                </span>
              </div>

              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                {Object.entries(skillsByCategory).map(([category, skills]) => {
                  const scores = skills
                    .map((skill) => (typeof skill === "object" ? skill.proficiency_score ?? 0 : 0))
                    .filter((value) => value > 0);
                  const average =
                    scores.length > 0
                      ? scores.reduce((sum, value) => sum + value, 0) / scores.length
                      : 0;

                  return (
                    <SectionInset key={`avg-${category}`} className="space-y-2">
                      <p className="truncate text-xs font-medium text-muted-foreground">
                        {categoryLabel(category)}
                      </p>
                      <div className="h-2 w-full rounded-full bg-background">
                        <div
                          className="h-2 rounded-full bg-foreground transition-all"
                          style={{ width: `${Math.round(average * 100)}%` }}
                        />
                      </div>
                      <p className="text-xs text-muted-foreground">{Math.round(average * 100)}%</p>
                    </SectionInset>
                  );
                })}
              </div>

              <div className="flex flex-col gap-3 sm:flex-row">
                <SearchInput
                  placeholder="Search skills..."
                  value={filter.searchQuery}
                  onChange={filter.setSearchQuery}
                  onClear={() => filter.setSearchQuery("")}
                  className="sm:max-w-xs"
                />
                <select
                  value={filter.categoryFilter}
                  onChange={(event) => filter.setCategoryFilter(event.target.value)}
                  className="h-10 rounded-[14px] border border-border/70 bg-background/80 px-3 text-sm text-foreground focus:border-primary/40 focus:outline-none focus:ring-2 focus:ring-ring/35"
                >
                  <option value="all">All categories</option>
                  {Object.keys(skillsByCategory).map((category) => (
                    <option key={category} value={category}>
                      {categoryLabel(category)}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-5">
                {Object.entries(filter.filteredByCategory).map(([category, skills]) => (
                  <div key={category} className="space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="text-sm font-semibold text-foreground">
                          {categoryLabel(category)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {skills.length} skill{skills.length === 1 ? "" : "s"}
                        </p>
                      </div>
                    </div>

                    <div className="space-y-2">
                      {skills.map((skill) => {
                        const skillName = typeof skill === "string" ? skill : skill.name ?? "";
                        const isHighlighted = highlight.skills.includes(skillName);
                        const description = typeof skill === "object" ? skill.description : undefined;
                        const proficiency = typeof skill === "object" ? skill.proficiency_score ?? 0 : 0;
                        const highestTier = typeof skill === "object" ? skill.highest_tier : undefined;
                        const tierBreakdown = typeof skill === "object" ? skill.tier_breakdown : undefined;
                        const evidence = getSkillEvidence(skillName);
                        const skillKey = `${category}::${skillName}`;
                        const isExpanded = filter.expandedSkillKey === skillKey;

                        return (
                          <div
                            key={`${category}-${skillName}`}
                            className={`rounded-[18px] p-3 transition-colors ${
                              isHighlighted ? "bg-muted/75" : "bg-muted/45 hover:bg-muted/60"
                            }`}
                          >
                            <div className="flex items-start gap-3">
                              <Checkbox
                                id={`skill-${category}-${skillName}`}
                                checked={isHighlighted}
                                onChange={() => highlight.toggle(skillName)}
                                className="mt-0.5 border-border"
                              />

                              <button
                                type="button"
                                onClick={() => filter.setExpandedSkillKey(isExpanded ? null : skillKey)}
                                className="min-w-0 flex-1 text-left"
                              >
                                <span className="block text-sm font-medium text-foreground">
                                  {skillName}
                                </span>
                                {description && (
                                  <span className="mt-0.5 block text-xs text-muted-foreground">
                                    {description}
                                  </span>
                                )}
                              </button>

                              <div className="flex flex-wrap items-center justify-end gap-2">
                                {highestTier && (
                                  <TierIndicator tier={highestTier} breakdown={tierBreakdown} />
                                )}
                                {proficiency > 0 && !highestTier && (
                                  <div className="flex items-center gap-1.5">
                                    <div className="h-1.5 w-16 rounded-full bg-background">
                                      <div
                                        className="h-1.5 rounded-full bg-foreground"
                                        style={{ width: `${Math.round(proficiency * 100)}%` }}
                                      />
                                    </div>
                                    <span className="w-8 text-xs text-muted-foreground">
                                      {Math.round(proficiency * 100)}%
                                    </span>
                                  </div>
                                )}
                                {evidence.length > 0 && (
                                  <span className="rounded-full bg-background px-2 py-0.5 text-xs text-muted-foreground">
                                    {evidence.length}
                                  </span>
                                )}
                                {isHighlighted && (
                                  <Check size={16} className="text-foreground" />
                                )}
                                {evidence.length > 0 &&
                                  (isExpanded ? (
                                    <ChevronUp size={14} className="text-muted-foreground" />
                                  ) : (
                                    <ChevronDown size={14} className="text-muted-foreground" />
                                  ))}
                              </div>
                            </div>

                            {isExpanded && evidence.length > 0 && (
                              <div className="mt-3 ml-7 rounded-[14px] bg-background/80 px-4 py-3">
                                <div className="space-y-1.5">
                                  {evidence.slice(0, 5).map((item, index) => (
                                    <div
                                      key={`${item.file ?? ""}:${item.line ?? ""}:${index}`}
                                      className="flex items-start gap-2 text-xs text-muted-foreground"
                                    >
                                      <span className="mt-0.5">-</span>
                                      <div>
                                        <span>{item.description || item.type || "Evidence"}</span>
                                        {item.file && (
                                          <span className="ml-1 font-mono text-muted-foreground">
                                            {item.file}
                                            {item.line ? `:${item.line}` : ""}
                                          </span>
                                        )}
                                      </div>
                                    </div>
                                  ))}
                                  {evidence.length > 5 && (
                                    <p className="text-xs italic text-muted-foreground">
                                      + {evidence.length - 5} more evidence items
                                    </p>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </SectionBody>
      </Section>

      {skillAdoptionTimeline.length > 0 && (
        <Section>
          <SectionHeader>
            <SectionHeading>
              <SectionTitle>Skill Adoption Timeline</SectionTitle>
              <SectionDescription>When each skill first appeared in the codebase.</SectionDescription>
            </SectionHeading>
          </SectionHeader>
          <SectionBody className="pt-0">
            <div className="[&>*+*]:mt-3">
              {skillAdoptionTimeline.map((entry) => (
                <SectionInset
                  key={`${entry.skill_name}::${entry.first_used_period ?? ""}`}
                  className="flex items-center gap-4"
                >
                  <span className="w-20 shrink-0 text-xs font-mono text-muted-foreground">
                    {entry.first_used_period || "Unknown"}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">
                      {entry.skill_name}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      {categoryLabel(entry.category ?? "")}
                      {entry.file ? ` · ${entry.file}` : ""}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <div className="h-1.5 w-12 rounded-full bg-background">
                      <div
                        className="h-1.5 rounded-full bg-foreground"
                        style={{ width: `${Math.round((entry.current_proficiency ?? 0) * 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {entry.total_usage ?? 0} uses
                    </span>
                  </div>
                </SectionInset>
              ))}
            </div>
          </SectionBody>
        </Section>
      )}

      <Section>
        <SectionHeader>
          <SectionHeading>
            <SectionTitle>Skill Gap Analysis</SectionTitle>
            <SectionDescription>Compare detected skills against a target role profile.</SectionDescription>
          </SectionHeading>
        </SectionHeader>
        <SectionBody className="space-y-4 pt-0">
          <div className="flex items-center gap-3">
            <select
              className="h-10 rounded-[14px] border border-border/70 bg-background/80 px-3 text-sm text-foreground focus:border-primary/40 focus:outline-none focus:ring-2 focus:ring-ring/35"
              value={gapAnalysis.selectedRole}
              onChange={(event) => gapAnalysis.run(event.target.value)}
            >
              <option value="">Select a role...</option>
              {gapAnalysis.roles.map((role) => (
                <option key={role.key} value={role.key}>
                  {role.label}
                </option>
              ))}
            </select>
            {gapAnalysis.loading && <Spinner size={16} className="text-muted-foreground" />}
          </div>

          {gapAnalysis.error && <p className="text-sm text-destructive">{gapAnalysis.error}</p>}

          {gapAnalysis.result && (
            <div className="space-y-4">
              <SectionInset className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="font-medium text-foreground">
                    Weighted Coverage for {gapAnalysis.result.role_label}
                  </span>
                  <span className="text-muted-foreground">
                    {gapAnalysis.result.weighted_coverage_percent ?? gapAnalysis.result.coverage_percent}%
                  </span>
                </div>
                <div className="h-3 w-full rounded-full bg-background">
                  <div
                    className={`h-3 rounded-full transition-all ${
                      (gapAnalysis.result.weighted_coverage_percent ?? gapAnalysis.result.coverage_percent) >= 75
                        ? "bg-emerald-600"
                        : (gapAnalysis.result.weighted_coverage_percent ?? gapAnalysis.result.coverage_percent) >= 40
                          ? "bg-amber-500"
                          : "bg-red-500"
                    }`}
                    style={{
                      width: `${gapAnalysis.result.weighted_coverage_percent ?? gapAnalysis.result.coverage_percent}%`,
                    }}
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Critical skills are weighted 3x, recommended 2x, nice-to-have 1x.
                </p>
              </SectionInset>

              {gapAnalysis.result.matched.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
                    Matched ({gapAnalysis.result.matched.length})
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {gapAnalysis.result.matched.map((skill) => {
                      const name = typeof skill === "string" ? skill : skill.name;
                      const importance = typeof skill === "object" ? skill.importance : undefined;
                      return (
                        <span
                          key={name}
                          className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-foreground"
                        >
                          {name}
                          {importance && (
                            <span className="text-[10px] font-semibold uppercase text-muted-foreground">
                              · {importance === "nice_to_have" ? "bonus" : importance}
                            </span>
                          )}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}

              {gapAnalysis.result.missing.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
                    Missing ({gapAnalysis.result.missing.length})
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {gapAnalysis.result.missing.map((skill) => {
                      const name = typeof skill === "string" ? skill : skill.name;
                      const importance = typeof skill === "object" ? skill.importance : undefined;
                      return (
                        <span
                          key={name}
                          className="inline-flex items-center gap-1 rounded-full bg-background px-2.5 py-1 text-xs font-medium text-foreground"
                        >
                          {name}
                          {importance && (
                            <span
                              className={`text-[10px] font-semibold uppercase ${
                                importance === "critical"
                                  ? "text-red-600"
                                  : importance === "recommended"
                                    ? "text-amber-600"
                                    : "text-muted-foreground"
                              }`}
                            >
                              · {importance === "nice_to_have" ? "bonus" : importance}
                            </span>
                          )}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}

              {gapAnalysis.result.extra.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
                    Additional Skills ({gapAnalysis.result.extra.length})
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {gapAnalysis.result.extra.map((skill) => (
                      <span
                        key={skill}
                        className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-foreground"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {!gapAnalysis.selectedRole && !gapAnalysis.result && (
            <p className="text-sm text-muted-foreground">
              Select a role above to see how your project skills compare.
            </p>
          )}
        </SectionBody>
      </Section>
    </div>
  );
}
