"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getStoredToken } from "@/lib/auth";
import { getProjects, getProjectById, runProjectAiAnalysis } from "@/lib/api/projects";
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
import { useAiEligibility } from "@/hooks/use-ai-eligibility";

// ─── helpers ────────────────────────────────────────────────────────────────

function formatDate(ts?: string | null): string {
  if (!ts) return "Unknown date";
  try {
    return new Date(ts).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return ts;
  }
}

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
      setRunError(null);
      try {
        const res: AiAnalysisApiResponse = await runProjectAiAnalysis(
          token,
          projectId,
          force
        );
        setAnalyses((prev) => ({ ...prev, [projectId]: res.result }));
      } catch (err) {
        setRunError(
          err instanceof Error ? err.message : "AI analysis failed. Try again."
        );
      } finally {
        setRunningFor(null);
      }
    },
    [aiReady, checkEligibility]
  );

  // ── render ─────────────────────────────────────────────────────────────────
  const analysisForSelected =
    selectedId !== null ? (analyses[selectedId] ?? null) : null;
  const isRunning = runningFor === selectedId;

  return (
    <div className="p-6 space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Sparkles size={22} className="text-gray-700" />
          AI Analysis
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Run AI-powered portfolio analysis on your scanned projects.
        </p>
      </div>

      {/* Eligibility status */}
      <Card className="bg-white border border-gray-200">
        <CardHeader className="border-b border-gray-200 pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-semibold text-gray-900">
              AI Requirements
            </CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void checkEligibility()}
              disabled={eligibilityLoading}
              className="text-xs border-gray-300 h-7"
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
        <CardContent className="p-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                External Data Consent
              </p>
              <EligibilityBadge ok={externalConsent} />
            </div>
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                OpenAI API Key
              </p>
              <EligibilityBadge ok={apiKeyValid} />
            </div>
          </div>

          {eligibilityChecked && !aiReady && eligibilityMessage && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 flex items-start gap-2">
              <AlertCircle
                size={15}
                className="text-amber-600 mt-0.5 flex-shrink-0"
              />
              <p className="text-sm text-amber-800">{eligibilityMessage}</p>
            </div>
          )}

          {!eligibilityChecked && (
            <p className="text-xs text-gray-400">Checking requirements…</p>
          )}

          {eligibilityChecked && !aiReady && (
            <Link href="/settings" className="text-sm text-gray-700 underline">
              Open Settings to configure requirements
            </Link>
          )}
        </CardContent>
      </Card>

      {/* Project list + analysis panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
        {/* ── project list ─────────────────────────────── */}
        <div className="lg:col-span-1">
          <Card className="bg-white border border-gray-200">
            <CardHeader className="border-b border-gray-200 pb-3">
              <CardTitle className="text-base font-semibold text-gray-900">
                Your Projects
              </CardTitle>
              <p className="text-xs text-gray-500 mt-0.5">
                Click a project to view or run AI analysis.
              </p>
            </CardHeader>
            <CardContent className="p-0">
              {loadingProjects && (
                <div className="flex items-center justify-center py-10">
                  <Loader2 size={20} className="animate-spin text-gray-400" />
                </div>
              )}
              {projectsError && (
                <div className="p-4 text-sm text-red-600">{projectsError}</div>
              )}
              {!loadingProjects && !projectsError && projects.length === 0 && (
                <div className="p-4 text-sm text-gray-500">
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
                      className={`w-full text-left px-4 py-3 border-b border-gray-100 last:border-b-0 flex items-center justify-between gap-2 transition-colors ${
                        isSelected
                          ? "bg-gray-900 text-white"
                          : "hover:bg-gray-50 text-gray-800"
                      }`}
                    >
                      <div className="min-w-0 flex-1">
                        <p
                          className={`text-sm font-medium truncate ${
                            isSelected ? "text-white" : "text-gray-900"
                          }`}
                        >
                          {project.project_name}
                        </p>
                        <p
                          className={`text-xs mt-0.5 flex items-center gap-1 ${
                            isSelected ? "text-gray-300" : "text-gray-500"
                          }`}
                        >
                          <Calendar size={11} />
                          {formatDate(project.scan_timestamp)}
                        </p>
                      </div>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        {hasAnalysis && existing && (
                          <span className="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-medium">
                            <Sparkles size={10} />
                            AI
                          </span>
                        )}
                        <ChevronRight
                          size={14}
                          className={
                            isSelected ? "text-gray-300" : "text-gray-400"
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
            <Card className="bg-white border border-gray-200">
              <CardContent className="p-8 text-center text-gray-400">
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
              <Card className="bg-white border border-gray-200">
                <CardHeader className="border-b border-gray-200 pb-3">
                  <CardTitle className="text-base font-semibold text-gray-900">
                    {selectedProject.project_name}
                  </CardTitle>
                  <p className="text-xs text-gray-500 mt-0.5 flex items-center gap-1 flex-wrap">
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
                <CardContent className="p-4 space-y-3">
                  {runError && (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-3 flex items-start gap-2">
                      <AlertCircle
                        size={15}
                        className="text-red-500 mt-0.5 flex-shrink-0"
                      />
                      <p className="text-sm text-red-700">{runError}</p>
                    </div>
                  )}

                  {!aiReady && eligibilityChecked && (
                    <p className="text-sm text-gray-500">
                      Enable External Data consent and verify your OpenAI API
                      key in{" "}
                      <Link
                        href="/settings"
                        className="underline text-gray-700"
                      >
                        Settings
                      </Link>{" "}
                      to run AI analysis.
                    </p>
                  )}

                  {loadingDetail && !analysisForSelected ? (
                    <div className="flex items-center gap-2 text-sm text-gray-400">
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
                          className="bg-gray-900 text-white hover:bg-gray-800 disabled:opacity-60 text-sm"
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
                          className="border-gray-300 text-sm disabled:opacity-60"
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
                <Card className="bg-white border border-gray-200">
                  <CardContent className="p-8 flex flex-col items-center gap-3 text-gray-400">
                    <Loader2 size={24} className="animate-spin" />
                    <p className="text-sm">
                      Running AI analysis, this may take a moment…
                    </p>
                  </CardContent>
                </Card>
              )}

              {/* Results */}
              {analysisForSelected && !isRunning && (
                <Card className="bg-white border border-gray-200">
                  <CardHeader className="border-b border-gray-200 pb-3">
                    <CardTitle className="text-base font-semibold text-gray-900 flex items-center gap-2">
                      <Sparkles size={16} className="text-gray-700" />
                      AI Analysis Results
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-5 space-y-5">
                    {/* Overall summary */}
                    {analysisForSelected.overall_summary && (
                      <div>
                        <p className="text-sm font-semibold text-gray-700 mb-1">
                          Project Overview
                        </p>
                        <p className="text-sm text-gray-700 leading-relaxed">
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

                    {/* Legacy fallback for already-cached old-format results */}
                    {!analysisForSelected.overall_summary &&
                      !analysisForSelected.categories?.length &&
                      analysisForSelected.portfolio_overview && (
                        <div>
                          <p className="text-sm font-semibold text-gray-700 mb-1">Portfolio Overview</p>
                          <p className="text-sm text-gray-700 leading-relaxed">
                            {analysisForSelected.portfolio_overview}
                          </p>
                        </div>
                      )}

                    {!analysisForSelected.overall_summary &&
                      !analysisForSelected.categories?.length &&
                      !analysisForSelected.portfolio_overview && (
                        <p className="text-sm text-gray-400">
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
