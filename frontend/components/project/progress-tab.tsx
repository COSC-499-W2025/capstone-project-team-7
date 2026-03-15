"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { formatPeriodLabel } from "@/lib/format-utils";
import type {
  SkillProgressPeriod,
  SkillProgressSummary,
} from "@/types/project";

interface ProgressTabProps {
  skillsTimeline: SkillProgressPeriod[];
  topSkills: Array<[string, number]>;
  skillsLoading: boolean;
  skillsNote: string | null;
  skillsSummary: SkillProgressSummary | null;
  summaryLoading: boolean;
  handleGenerateSummary: () => void;
}

export function ProgressTab({
  skillsTimeline,
  topSkills,
  skillsLoading,
  skillsNote,
  skillsSummary,
  summaryLoading,
  handleGenerateSummary,
}: ProgressTabProps) {
  return (
    <div className="space-y-6">
      <Card className="bg-white border border-gray-200">
        <CardHeader className="border-b border-gray-200">
          <CardTitle className="text-xl font-bold text-gray-900">
            Skill Progression Timeline
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6 space-y-4">
          {skillsLoading && (
            <p className="text-sm text-gray-500">
              Loading skill progression…
            </p>
          )}
          {!skillsLoading && skillsTimeline.length === 0 && (
            <p className="text-sm text-gray-500">
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
                      className="px-3 py-1 rounded-full bg-gray-900 text-white text-xs font-semibold"
                    >
                      {skill} · {count}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-gray-400">
                    No top skills yet.
                  </span>
                )}
              </div>

              <div className="grid gap-4">
                {skillsTimeline.map((period) => (
                  <div
                    key={period.period_label}
                    className="rounded-xl border border-gray-200 p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h4 className="text-base font-semibold text-gray-900">
                          {formatPeriodLabel(period.period_label)}
                        </h4>
                        <p className="text-xs text-gray-500">
                          {period.period_label}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2 text-xs font-semibold">
                        <span className="px-2.5 py-1 rounded-full bg-gray-900 text-white">
                          {period.commits} commits
                        </span>
                        <span className="px-2.5 py-1 rounded-full bg-gray-100 text-gray-700">
                          {period.skill_count} skills
                        </span>
                        <span className="px-2.5 py-1 rounded-full bg-gray-100 text-gray-700">
                          {period.tests_changed} tests
                        </span>
                        <span className="px-2.5 py-1 rounded-full bg-gray-100 text-gray-700">
                          {period.contributors} contributors
                        </span>
                      </div>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-2">
                      {period.activity_types.length > 0 ? (
                        period.activity_types.map((type) => (
                          <span
                            key={type}
                            className="px-2.5 py-1 rounded-full bg-gray-50 text-gray-600 text-xs font-semibold border border-gray-200"
                          >
                            {type}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-gray-400">
                          No activity labels
                        </span>
                      )}
                    </div>

                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                      <div>
                        <p className="text-xs font-semibold text-gray-500 uppercase">
                          Top skills
                        </p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {period.top_skills.length > 0 ? (
                            period.top_skills.map((skill) => (
                              <span
                                key={skill}
                                className="px-2.5 py-1 rounded-full bg-gray-900 text-white text-xs"
                              >
                                {skill}
                              </span>
                            ))
                          ) : (
                            <span className="text-xs text-gray-400">
                              No skills recorded
                            </span>
                          )}
                        </div>
                      </div>

                      <div>
                        <p className="text-xs font-semibold text-gray-500 uppercase">
                          Languages
                        </p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {Object.keys(period.period_languages).length > 0 ? (
                            Object.entries(period.period_languages).map(
                              ([lang, count]) => (
                                <span
                                  key={lang}
                                  className="px-2.5 py-1 rounded-full bg-gray-100 text-gray-700 text-xs"
                                >
                                  {lang} · {count}
                                </span>
                              )
                            )
                          ) : (
                            <span className="text-xs text-gray-400">
                              No language data
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                      <div>
                        <p className="text-xs font-semibold text-gray-500 uppercase">
                          Recent commits
                        </p>
                        <ul className="mt-2 space-y-1 text-sm text-gray-700">
                          {period.commit_messages
                            .slice(0, 4)
                            .map((msg, index) => (
                              <li
                                key={`${period.period_label}-commit-${index}`}
                                className="truncate"
                              >
                                {msg}
                              </li>
                            ))}
                          {period.commit_messages.length === 0 && (
                            <li className="text-xs text-gray-400">
                              No commit messages recorded.
                            </li>
                          )}
                        </ul>
                      </div>

                      <div>
                        <p className="text-xs font-semibold text-gray-500 uppercase">
                          Files touched
                        </p>
                        <ul className="mt-2 space-y-1 text-sm text-gray-700">
                          {period.top_files.slice(0, 4).map((file, index) => (
                            <li
                              key={`${period.period_label}-file-${index}`}
                              className="truncate"
                            >
                              {file}
                            </li>
                          ))}
                          {period.top_files.length === 0 && (
                            <li className="text-xs text-gray-400">
                              No file highlights recorded.
                            </li>
                          )}
                        </ul>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="bg-white border border-gray-200">
        <CardHeader className="border-b border-gray-200 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-xl font-bold text-gray-900">
              AI Summary
            </CardTitle>
            <p className="text-xs text-gray-500 mt-1">
              Summarize skill growth from the timeline.
            </p>
          </div>
          <button
            onClick={handleGenerateSummary}
            disabled={summaryLoading}
            className="px-3 py-2 text-xs font-semibold rounded-md bg-gray-900 text-white disabled:opacity-60"
          >
            {summaryLoading
              ? "Generating…"
              : skillsSummary
              ? "Regenerate"
              : "Generate"}
          </button>
        </CardHeader>
        <CardContent className="p-6 space-y-4">
          {skillsNote && <p className="text-sm text-gray-500">{skillsNote}</p>}
          {skillsSummary && (
            <div className="space-y-4">
              <div>
                <p className="text-sm font-semibold text-gray-700">Overview</p>
                <p className="text-sm text-gray-700 mt-1">
                  {skillsSummary.overview}
                </p>
                {skillsSummary.validation_warning && (
                  <p className="text-xs text-amber-600 mt-2">
                    {skillsSummary.validation_warning}
                  </p>
                )}
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <p className="text-sm font-semibold text-gray-700">
                    Timeline highlights
                  </p>
                  <ul className="mt-2 space-y-1 text-sm text-gray-700 list-disc list-inside">
                    {skillsSummary.timeline.map((item, index) => (
                      <li key={`timeline-${index}`}>{item}</li>
                    ))}
                    {skillsSummary.timeline.length === 0 && (
                      <li className="text-xs text-gray-400">
                        No timeline highlights.
                      </li>
                    )}
                  </ul>
                </div>

                <div>
                  <p className="text-sm font-semibold text-gray-700">
                    Skills focus
                  </p>
                  <ul className="mt-2 space-y-1 text-sm text-gray-700 list-disc list-inside">
                    {skillsSummary.skills_focus.map((item, index) => (
                      <li key={`skills-${index}`}>{item}</li>
                    ))}
                    {skillsSummary.skills_focus.length === 0 && (
                      <li className="text-xs text-gray-400">
                        No skill focus notes.
                      </li>
                    )}
                  </ul>
                </div>
              </div>

              <div>
                <p className="text-sm font-semibold text-gray-700">
                  Suggested next steps
                </p>
                <ul className="mt-2 space-y-1 text-sm text-gray-700 list-disc list-inside">
                  {skillsSummary.suggested_next_steps.map((item, index) => (
                    <li key={`steps-${index}`}>{item}</li>
                  ))}
                  {skillsSummary.suggested_next_steps.length === 0 && (
                    <li className="text-xs text-gray-400">
                      No suggestions yet.
                    </li>
                  )}
                </ul>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
