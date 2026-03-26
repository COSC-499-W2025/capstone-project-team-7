"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getStoredToken } from "@/lib/auth";
import {
  getProjects,
  getProjectById,
  runProjectAiAnalysis,
  getProjectAiBatchStatus,
} from "@/lib/api/projects";
import type {
  ProjectMetadata,
  ProjectAiAnalysis,
  AiAnalysisApiResponse,
} from "@/types/project";
import {
  Sparkles,
  Loader2,
  RefreshCw,
  ChevronRight,
  Calendar,
  AlertCircle,
} from "lucide-react";
import { EligibilityBadge } from "@/components/ai-analysis/eligibility-badge";
import { CategoryCard } from "@/components/ai-analysis/category-card";
import { MarkdownReport } from "@/components/ai-analysis/markdown-report";
import { KeyFileSummary } from "@/components/ai-analysis/key-file-summary";
import { formatDate } from "@/components/ai-analysis/render-inline-markdown";
import { useAiEligibility } from "@/hooks/use-ai-eligibility";

// ─── main page ───────────────────────────────────────────────────────────────

export default function AiAnalysisPage() {
  // project list
  const [projects, setProjects] = useState<ProjectMetadata[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [projectsError, setProjectsError] = useState<string | null>(null);

  // selected project
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selectedProject = projects.find((p) => p.id === selectedId) ?? null;

  // per-project AI analysis results (keyed by project id)
  const [analyses, setAnalyses] = useState<Record<string, ProjectAiAnalysis | null>>({});
  // loading state when fetching existing scan_data detail
  const [loadingDetail, setLoadingDetail] = useState(false);

  // eligibility
  const {
    externalConsent,
    apiKeyValid,
    eligibilityChecked,
    eligibilityLoading,
    eligibilityMessage,
    aiReady,
    checkEligibility,
  } = useAiEligibility();

  // run-analysis state
  const [runningFor, setRunningFor] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [statusMessages, setStatusMessages] = useState<string[]>([]);
  const [batchStatus, setBatchStatus] = useState<string | null>(null);

  // ── load projects ──────────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    const token = getStoredToken();
    if (!token) {
      setProjectsError("Not authenticated. Please log in.");
      setLoadingProjects(false);
      return;
    }

    setLoadingProjects(true);
    getProjects(token)
      .then((res) => {
        if (cancelled) return;
        // sort by scan_timestamp descending (most recent first)
        const sorted = [...(res.projects ?? [])].sort((a, b) => {
          const ta = a.scan_timestamp ?? "";
          const tb = b.scan_timestamp ?? "";
          return tb.localeCompare(ta);
        });
        setProjects(sorted);
      })
      .catch((err) => {
        if (cancelled) return;
        setProjectsError(
          err instanceof Error ? err.message : "Failed to load projects"
        );
      })
      .finally(() => {
        if (!cancelled) setLoadingProjects(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // ── load existing analysis when project is selected ────────────────────────
  const handleSelectProject = useCallback(
    async (projectId: string) => {
      setSelectedId(projectId);
      setRunError(null);
      setStatusMessages([]);

      // If we already have it in state (including null = "confirmed no analysis"), skip
      if (Object.prototype.hasOwnProperty.call(analyses, projectId)) return;

      const token = getStoredToken();
      if (!token) return;

      setLoadingDetail(true);
      try {
        const detail = await getProjectById(token, projectId);
        const existing =
          (detail?.scan_data as Record<string, unknown> | null)
            ?.ai_analysis as ProjectAiAnalysis | null | undefined;
        setAnalyses((prev) => ({
          ...prev,
          [projectId]: existing ?? null,
        }));
      } catch {
        setAnalyses((prev) => ({ ...prev, [projectId]: null }));
      } finally {
        setLoadingDetail(false);
      }
    },
    [analyses]
  );

  // ── run analysis ───────────────────────────────────────────────────────────
  const handleRunAnalysis = useCallback(
    async (projectId: string, force = false) => {
      const token = getStoredToken();
      if (!token) return;

      const eligible = aiReady || (await checkEligibility());
      if (!eligible) return;

      setRunningFor(projectId);
      setBatchStatus("running");
      setRunError(null);
      setStatusMessages([]);
      try {
        const res: AiAnalysisApiResponse = await runProjectAiAnalysis(
          token,
          projectId,
          force
        );
        setAnalyses((prev) => ({ ...prev, [projectId]: res.result }));
        setStatusMessages(res.status_messages ?? []);
      } catch (err) {
        setRunError(
          err instanceof Error ? err.message : "AI analysis failed. Try again."
        );
        setStatusMessages([]);
      } finally {
        setBatchStatus(null);
        setRunningFor(null);
      }
    },
    [aiReady, checkEligibility]
  );

  useEffect(() => {
    const runningForSelected = runningFor !== null && runningFor === selectedId;
    if (!runningForSelected || !selectedId) return;

    let cancelled = false;

    const poll = async () => {
      const token = getStoredToken();
      if (!token || cancelled) return;
      try {
        const statusRes = await getProjectAiBatchStatus(token, selectedId);
        if (cancelled) return;
        setBatchStatus(statusRes.status);
        setStatusMessages(statusRes.status_messages ?? []);
      } catch {
        // Ignore transient polling errors while analysis is in progress.
      }
    };

    void poll();
    const intervalId = window.setInterval(() => {
      void poll();
    }, 900);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [runningFor, selectedId]);

  // ── render ─────────────────────────────────────────────────────────────────
  const analysisForSelected =
    selectedId !== null ? (analyses[selectedId] ?? null) : null;
  const isRunning = runningFor === selectedId;
  const useMarkdownReport =
    analysisForSelected?.render_mode === "markdown_report" &&
    typeof analysisForSelected?.markdown_report === "string" &&
    analysisForSelected.markdown_report.trim().length > 0;
  const keyFiles = (analysisForSelected?.key_files ?? [])
    .filter((file) => Boolean(file?.file_path) && Boolean(file?.summary))
    .slice(0, 3);
  const sectionHeaderClass = "border-b border-border/70 p-5 pb-4 sm:p-5 sm:pb-4";
  const sectionBodyClass = "p-5 pt-4 sm:p-5 sm:pt-4";

  return (
    <div className="page-container">
      <section className="page-card">
        <div className="page-header">
          <span className="page-kicker">AI Workspace</span>
          <h1 className="flex items-center gap-2 text-foreground">
            <Sparkles size={22} className="text-primary" />
            AI Analysis
          </h1>
          <p className="page-summary mt-3">
            Run AI-powered portfolio analysis on your scanned projects and review structured summaries, key files, and category insights in the current dashboard layout.
          </p>
        </div>
      </section>

      {/* Eligibility status */}
      <Card>
        <CardHeader className={sectionHeaderClass}>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-semibold text-foreground">
              AI Requirements
            </CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void checkEligibility()}
              disabled={eligibilityLoading}
              className="h-8 border-border text-xs"
            >
              {eligibilityLoading ? (
                <Loader2 size={12} className="animate-spin mr-1" />
              ) : (
                <RefreshCw size={12} className="mr-1" />
              )}
              Re-check
            </Button>
          </div>
        </CardHeader>
        <CardContent className={`${sectionBodyClass} space-y-4`}>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="rounded-[16px] border border-border bg-muted/60 p-4">
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                External Data Consent
              </p>
              <EligibilityBadge ok={externalConsent} />
            </div>
            <div className="rounded-[16px] border border-border bg-muted/60 p-4">
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                OpenAI API Key
              </p>
              <EligibilityBadge ok={apiKeyValid} />
            </div>
          </div>

          {eligibilityChecked && !aiReady && eligibilityMessage && (
            <div className="tone-surface-amber flex items-start gap-2 rounded-[16px] border p-4">
              <AlertCircle
                size={15}
                className="tone-copy-amber mt-0.5 flex-shrink-0"
              />
              <p className="tone-copy-amber text-sm">{eligibilityMessage}</p>
            </div>
          )}

          {!eligibilityChecked && (
            <p className="text-xs text-muted-foreground">Checking requirements…</p>
          )}

          {eligibilityChecked && !aiReady && (
            <Link href="/settings" className="text-sm text-foreground underline underline-offset-4">
              Open Settings to configure requirements
            </Link>
          )}
        </CardContent>
      </Card>

      {/* Project list + analysis panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
        {/* ── project list ─────────────────────────────── */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader className={sectionHeaderClass}>
              <CardTitle className="text-base font-semibold text-foreground">
                Your Projects
              </CardTitle>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Click a project to view or run AI analysis.
              </p>
            </CardHeader>
            <CardContent className="p-0">
              {loadingProjects && (
                <div className="flex items-center justify-center py-10">
                  <Loader2 size={20} className="animate-spin text-muted-foreground" />
                </div>
              )}
              {projectsError && (
                <div className="p-4 text-sm text-red-600">{projectsError}</div>
              )}
              {!loadingProjects && !projectsError && projects.length === 0 && (
                <div className="p-4 text-sm text-muted-foreground">
                  No projects found. Upload and scan a project first.
                </div>
              )}
              {!loadingProjects &&
                projects.map((project) => {
                  const existing = analyses[project.id];
                  const hasAnalysis =
                    existing != null &&
                    Object.prototype.hasOwnProperty.call(analyses, project.id);
                  const isSelected = selectedId === project.id;

                  return (
                    <button
                      key={project.id}
                      onClick={() => void handleSelectProject(project.id)}
                      className={`flex w-full items-center justify-between gap-2 border-b border-border/70 px-4 py-3 text-left transition-colors last:border-b-0 ${
                        isSelected
                          ? "bg-primary text-primary-foreground"
                          : "text-foreground hover:bg-muted/60"
                      }`}
                    >
                      <div className="min-w-0 flex-1">
                        <p
                          className={`text-sm font-medium truncate ${
                            isSelected ? "text-primary-foreground" : "text-foreground"
                          }`}
                        >
                          {project.project_name}
                        </p>
                        <p
                          className={`text-xs mt-0.5 flex items-center gap-1 ${
                            isSelected ? "text-primary-foreground/80" : "text-muted-foreground"
                          }`}
                        >
                          <Calendar size={11} />
                          {formatDate(project.scan_timestamp)}
                        </p>
                      </div>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        {hasAnalysis && existing && (
                          <span className="tone-pill tone-pill-emerald inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[11px] font-medium">
                            <Sparkles size={10} />
                            AI
                          </span>
                        )}
                        <ChevronRight
                          size={14}
                          className={
                            isSelected ? "text-primary-foreground/75" : "text-muted-foreground"
                          }
                        />
                      </div>
                    </button>
                  );
                })}
            </CardContent>
          </Card>
        </div>

        {/* ── analysis panel ────────────────────────────── */}
        <div className="lg:col-span-2 space-y-4">
          {!selectedProject && (
            <Card>
              <CardContent className="flex flex-col items-center gap-3 p-8 text-center text-muted-foreground">
                <Sparkles size={32} className="mx-auto mb-3 opacity-40" />
                <p className="text-sm">
                  Select a project from the list to view or run AI analysis.
                </p>
              </CardContent>
            </Card>
          )}

          {selectedProject && (
            <>
              {/* Controls card */}
              <Card>
                <CardHeader className={sectionHeaderClass}>
                  <CardTitle className="text-base font-semibold text-foreground">
                    {selectedProject.project_name}
                  </CardTitle>
                  <p className="mt-0.5 flex flex-wrap items-center gap-1 text-xs text-muted-foreground">
                    <Calendar size={11} />
                    Scanned {formatDate(selectedProject.scan_timestamp)}
                    {selectedProject.languages &&
                      selectedProject.languages.length > 0 && (
                        <span className="ml-2">
                          · {selectedProject.languages.slice(0, 4).join(", ")}
                        </span>
                      )}
                  </p>
                </CardHeader>
                <CardContent className={`${sectionBodyClass} space-y-3`}>
                  {runError && (
                    <div className="flex items-start gap-2 rounded-[16px] border border-red-500/25 bg-red-500/12 p-4">
                      <AlertCircle
                        size={15}
                        className="mt-0.5 flex-shrink-0 text-red-300"
                      />
                      <p className="text-sm text-red-200">{runError}</p>
                    </div>
                  )}

                  {(isRunning || statusMessages.length > 0) && (
                    <div className="tone-surface-blue rounded-[16px] border p-4">
                      <p className="tone-copy-blue mb-2 text-xs font-semibold uppercase tracking-wide">
                        Batch Progress {isRunning && batchStatus ? `(${batchStatus})` : ""}
                      </p>
                      <ul className="space-y-1 max-h-40 overflow-auto pr-1">
                        {statusMessages.map((msg, idx) => (
                          <li key={`${idx}-${msg}`} className="tone-copy-blue text-sm">
                            {msg}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {!aiReady && eligibilityChecked && (
                    <p className="text-sm text-muted-foreground">
                      Enable External Data consent and verify your OpenAI API
                      key in{" "}
                      <Link
                        href="/settings"
                        className="text-foreground underline underline-offset-4"
                      >
                        Settings
                      </Link>{" "}
                      to run AI analysis.
                    </p>
                  )}

                  {loadingDetail && !analysisForSelected ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 size={14} className="animate-spin" />
                      Loading project data…
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 flex-wrap">
                      {!analysisForSelected && (
                        <Button
                          onClick={() =>
                            void handleRunAnalysis(selectedProject.id, false)
                          }
                          disabled={!aiReady || isRunning}
                          className="text-sm disabled:opacity-60"
                        >
                          {isRunning ? (
                            <>
                              <Loader2
                                size={14}
                                className="animate-spin mr-1.5"
                              />
                              Running…
                            </>
                          ) : (
                            <>
                              <Sparkles size={14} className="mr-1.5" />
                              Run AI Analysis
                            </>
                          )}
                        </Button>
                      )}
                      {analysisForSelected && (
                        <Button
                          variant="outline"
                          onClick={() =>
                            void handleRunAnalysis(selectedProject.id, true)
                          }
                          disabled={!aiReady || isRunning}
                          className="border-border text-sm disabled:opacity-60"
                        >
                          {isRunning ? (
                            <>
                              <Loader2
                                size={14}
                                className="animate-spin mr-1.5"
                              />
                              Re-running…
                            </>
                          ) : (
                            <>
                              <RefreshCw size={14} className="mr-1.5" />
                              Re-run Analysis
                            </>
                          )}
                        </Button>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Loading state while LLM runs */}
              {isRunning && !analysisForSelected && (
                <Card>
                  <CardContent className="flex flex-col items-center gap-3 p-8 text-muted-foreground">
                    <Loader2 size={24} className="animate-spin" />
                    <p className="text-sm">
                      Running AI analysis, streaming backend batch status above…
                    </p>
                  </CardContent>
                </Card>
              )}

              {/* Results */}
              {analysisForSelected && !isRunning && (
                <Card>
                  <CardHeader className={sectionHeaderClass}>
                    <CardTitle className="flex items-center gap-2 text-base font-semibold text-foreground">
                      <Sparkles size={16} className="text-primary" />
                      AI Analysis Results
                    </CardTitle>
                  </CardHeader>
                  <CardContent className={`${sectionBodyClass} space-y-5`}>
                    {useMarkdownReport ? (
                      <div className="space-y-4">
                        <div className="dashboard-card-subtle space-y-4 border border-border/70 p-5">
                          <div className="flex items-center justify-between mb-4">
                            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                              Batch AI Report
                            </p>
                            <span className="rounded-full border border-border bg-card/85 px-2 py-1 text-xs text-muted-foreground">
                              Markdown View
                            </span>
                          </div>
                          <MarkdownReport markdown={analysisForSelected.markdown_report as string} />
                        </div>

                        {keyFiles.length > 0 && (
                          <div className="dashboard-card-subtle border border-border/70 p-5">
                            <div className="mb-3">
                              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                Key Files
                              </p>
                            </div>
                            <div className="space-y-3">
                              {keyFiles.map((file, idx) => (
                                <details
                                  key={`${file.file_path}-${idx}`}
                                  className="group rounded-[16px] border border-border bg-muted/50 open:border-border open:bg-card/90"
                                >
                                  <summary className="cursor-pointer select-none list-none px-4 py-3 flex items-center justify-between">
                                    <span className="break-all pr-3 text-sm font-medium text-foreground">
                                      {file.file_path}
                                    </span>
                                    <span className="text-xs text-muted-foreground group-open:text-foreground">
                                      Expand
                                    </span>
                                  </summary>
                                  <div className="border-t border-border/70 px-4 pb-4 pt-3">
                                    <KeyFileSummary text={file.summary as string} keyPrefix={`kf-${idx}`} />
                                  </div>
                                </details>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <>
                        {/* Overall summary */}
                        {analysisForSelected.overall_summary && (
                          <div>
                            <p className="mb-1 text-sm font-semibold text-foreground">
                              Project Overview
                            </p>
                            <p className="text-sm leading-relaxed text-muted-foreground">
                              {analysisForSelected.overall_summary}
                            </p>
                          </div>
                        )}

                        {/* Per-category cards */}
                        {analysisForSelected.categories && analysisForSelected.categories.length > 0 && (
                          <div className="grid gap-4 md:grid-cols-2">
                            {analysisForSelected.categories.map((cat) => (
                              <CategoryCard key={cat.category} cat={cat} />
                            ))}
                          </div>
                        )}
                      </>
                    )}

                    {/* Legacy fallback for already-cached old-format results */}
                    {!analysisForSelected.overall_summary &&
                      !analysisForSelected.categories?.length &&
                      analysisForSelected.portfolio_overview && (
                        <div>
                          <p className="mb-1 text-sm font-semibold text-foreground">Portfolio Overview</p>
                          <p className="text-sm leading-relaxed text-muted-foreground">
                            {analysisForSelected.portfolio_overview}
                          </p>
                        </div>
                      )}

                    {!analysisForSelected.overall_summary &&
                      !analysisForSelected.categories?.length &&
                      !analysisForSelected.portfolio_overview && (
                        <p className="text-sm text-muted-foreground">
                          No analysis data returned. Try re-running.
                        </p>
                      )}
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
