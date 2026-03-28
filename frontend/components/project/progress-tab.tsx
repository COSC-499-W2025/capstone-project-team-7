"use client";

import { Button } from "@/components/ui/button";
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
import { formatPeriodLabel } from "@/lib/format-utils";
import { SkillProgressionChart } from "@/components/project/skill-progression-chart";
import type {
  SkillProgressPeriod,
  SkillProgressSummary,
  SkillProgressionMap,
} from "@/types/project";

interface ProgressTabProps {
  skillsTimeline: SkillProgressPeriod[];
  topSkills: Array<[string, number]>;
  skillsLoading: boolean;
  skillsNote: string | null;
  skillsSummary: SkillProgressSummary | null;
  summaryLoading: boolean;
  handleGenerateSummary: () => void;
  skillProgression: SkillProgressionMap;
}

export function ProgressTab({
  skillsTimeline,
  topSkills,
  skillsLoading,
  skillsNote,
  skillsSummary,
  summaryLoading,
  handleGenerateSummary,
  skillProgression,
}: ProgressTabProps) {
  return (
    <div className="space-y-6">
      {Object.keys(skillProgression).length > 0 && (
        <Section>
          <SectionHeader>
            <SectionHeading>
              <SectionTitle>Skill Progression</SectionTitle>
              <SectionDescription>
                Track how skill activity changed over time. Click skills to toggle them on or off.
              </SectionDescription>
            </SectionHeading>
          </SectionHeader>
          <SectionBody className="pt-0">
            <SkillProgressionChart skillProgression={skillProgression} />
          </SectionBody>
        </Section>
      )}

      <Section>
        <SectionHeader>
          <SectionHeading>
            <SectionTitle>Skill Progression Timeline</SectionTitle>
            <SectionDescription>Track how skills, languages, and activity changed over time.</SectionDescription>
          </SectionHeading>
        </SectionHeader>
        <SectionBody className="space-y-4 pt-0">
          {skillsLoading && <p className="text-sm text-muted-foreground">Loading skill progression…</p>}
          {!skillsLoading && skillsTimeline.length === 0 && (
            <p className="text-sm text-muted-foreground">
              {skillsNote || "No skill progression timeline available yet."}
            </p>
          )}

          {skillsTimeline.length > 0 && (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                {topSkills.length > 0 ? (
                  topSkills.map(([skill, count]) => (
                    <span
                      key={skill}
                      className="rounded-full bg-foreground px-3 py-1 text-xs font-semibold text-background"
                    >
                      {skill} · {count}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-muted-foreground">No top skills yet.</span>
                )}
              </div>

              <div className="grid gap-4">
                {skillsTimeline.map((period) => (
                  <SectionInset key={period.period_label} className="space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h4 className="text-base font-semibold text-foreground">
                          {formatPeriodLabel(period.period_label)}
                        </h4>
                        <p className="text-xs text-muted-foreground">{period.period_label}</p>
                      </div>
                      <div className="flex flex-wrap gap-2 text-xs font-semibold">
                        <span className="rounded-full bg-foreground px-2.5 py-1 text-background">
                          {period.commits} commits
                        </span>
                        <span className="rounded-full bg-background px-2.5 py-1 text-muted-foreground">
                          {period.skill_count} skills
                        </span>
                        <span className="rounded-full bg-background px-2.5 py-1 text-muted-foreground">
                          {period.tests_changed} tests
                        </span>
                        <span className="rounded-full bg-background px-2.5 py-1 text-muted-foreground">
                          {period.contributors} contributors
                        </span>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {period.activity_types.length > 0 ? (
                        period.activity_types.map((type) => (
                          <span
                            key={type}
                            className="rounded-full bg-background px-2.5 py-1 text-xs font-semibold text-muted-foreground"
                          >
                            {type}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-muted-foreground">No activity labels</span>
                      )}
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                          Top skills
                        </p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {period.top_skills.length > 0 ? (
                            period.top_skills.map((skill) => (
                              <span
                                key={skill}
                                className="rounded-full bg-foreground px-2.5 py-1 text-xs text-background"
                              >
                                {skill}
                              </span>
                            ))
                          ) : (
                            <span className="text-xs text-muted-foreground">No skills recorded</span>
                          )}
                        </div>
                      </div>

                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                          Languages
                        </p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {Object.keys(period.period_languages).length > 0 ? (
                            Object.entries(period.period_languages).map(([lang, count]) => (
                              <span
                                key={lang}
                                className="rounded-full bg-background px-2.5 py-1 text-xs text-muted-foreground"
                              >
                                {lang} · {count}
                              </span>
                            ))
                          ) : (
                            <span className="text-xs text-muted-foreground">No language data</span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                          Recent commits
                        </p>
                        <ul className="mt-2 space-y-1 text-sm text-foreground">
                          {period.commit_messages.slice(0, 4).map((msg, index) => (
                            <li key={`${period.period_label}-commit-${index}`} className="truncate">
                              {msg}
                            </li>
                          ))}
                          {period.commit_messages.length === 0 && (
                            <li className="text-xs text-muted-foreground">No commit messages recorded.</li>
                          )}
                        </ul>
                      </div>

                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                          Files touched
                        </p>
                        <ul className="mt-2 space-y-1 text-sm text-foreground">
                          {period.top_files.slice(0, 4).map((file, index) => (
                            <li key={`${period.period_label}-file-${index}`} className="truncate">
                              {file}
                            </li>
                          ))}
                          {period.top_files.length === 0 && (
                            <li className="text-xs text-muted-foreground">No file highlights recorded.</li>
                          )}
                        </ul>
                      </div>
                    </div>
                  </SectionInset>
                ))}
              </div>
            </div>
          )}
        </SectionBody>
      </Section>

      <Section>
        <SectionHeader>
          <SectionHeading>
            <SectionTitle>AI Summary</SectionTitle>
            <SectionDescription>Summarize skill growth from the timeline.</SectionDescription>
          </SectionHeading>
          <SectionActions>
            <Button onClick={handleGenerateSummary} disabled={summaryLoading} size="sm">
              {summaryLoading ? "Generating…" : skillsSummary ? "Regenerate" : "Generate"}
            </Button>
          </SectionActions>
        </SectionHeader>
        <SectionBody className="space-y-4 pt-0">
          {skillsNote && <p className="text-sm text-muted-foreground">{skillsNote}</p>}
          {skillsSummary && (
            <div className="space-y-4">
              <div>
                <p className="text-sm font-semibold text-foreground">Overview</p>
                <p className="mt-1 text-sm text-foreground">{skillsSummary.overview}</p>
                {skillsSummary.validation_warning && (
                  <p className="mt-2 text-xs text-amber-600">{skillsSummary.validation_warning}</p>
                )}
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <p className="text-sm font-semibold text-foreground">Timeline highlights</p>
                  <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-foreground">
                    {skillsSummary.timeline.map((item, index) => (
                      <li key={`timeline-${index}`}>{item}</li>
                    ))}
                    {skillsSummary.timeline.length === 0 && (
                      <li className="text-xs text-muted-foreground">No timeline highlights.</li>
                    )}
                  </ul>
                </div>

                <div>
                  <p className="text-sm font-semibold text-foreground">Skills focus</p>
                  <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-foreground">
                    {skillsSummary.skills_focus.map((item, index) => (
                      <li key={`skills-${index}`}>{item}</li>
                    ))}
                    {skillsSummary.skills_focus.length === 0 && (
                      <li className="text-xs text-muted-foreground">No skill focus notes.</li>
                    )}
                  </ul>
                </div>
              </div>

              <div>
                <p className="text-sm font-semibold text-foreground">Suggested next steps</p>
                <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-foreground">
                  {skillsSummary.suggested_next_steps.map((item, index) => (
                    <li key={`steps-${index}`}>{item}</li>
                  ))}
                  {skillsSummary.suggested_next_steps.length === 0 && (
                    <li className="text-xs text-muted-foreground">No suggestions yet.</li>
                  )}
                </ul>
              </div>
            </div>
          )}
        </SectionBody>
      </Section>
    </div>
  );
}
