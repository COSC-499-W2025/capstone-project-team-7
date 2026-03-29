"use client";

import { useState, useEffect, useCallback } from "react";
import { getStoredToken } from "@/lib/auth";
import { getJobs, getSavedJobs, saveJob, unsaveJob, updateJobStatus, scrapeJobs, triggerAiMatch, getScrapeHistory } from "@/lib/api/jobs";
import { useJobBoardStore } from "@/lib/stores/job-board-store";
import type { JobBoardTab } from "@/lib/stores/job-board-store";
import type { UserJob, ApplicationStatus, JobSource, JobFilters as JobFiltersType } from "@/types/job";
import { RefreshCw, Search, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/ui/empty-state";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Section,
  SectionActions,
  SectionBody,
  SectionHeader,
  SectionHeading,
  SectionTitle,
  SectionDescription,
} from "@/components/ui/section";
import { LoadingState } from "@/components/ui/loading-state";
import { JobCard } from "@/components/jobs/job-card";
import { JobFilterPanel } from "@/components/jobs/job-filters";
import { JobDetailModal } from "@/components/jobs/job-detail-modal";
import { ScrapeModal } from "@/components/jobs/scrape-modal";
import { SavedJobsView } from "@/components/jobs/saved-jobs-view";
import { ScrapeHistoryView } from "@/components/jobs/scrape-history-view";

export default function JobsPage() {
  const store = useJobBoardStore();
  const {
    jobs,
    jobsCount,
    jobsLoading,
    jobsError,
    filters,
    page,
    pageSize,
    activeTab,
    selectedJob,
    detailOpen,
    savedJobs,
    savedJobsLoading,
    scrapeHistory,
    setJobs,
    setJobsLoading,
    setJobsError,
    setFilters,
    resetFilters,
    setPage,
    setActiveTab,
    setSelectedJob,
    setDetailOpen,
    setSavedJobs,
    setSavedJobsLoading,
    updateJobInList,
    removeJobFromSaved,
    setScrapeHistory,
  } = store;

  const [refreshing, setRefreshing] = useState(false);
  const [scrapeModalOpen, setScrapeModalOpen] = useState(false);
  const [initialLoaded, setInitialLoaded] = useState(false);
  const [scraping, setScraping] = useState(false);
  const [lastScrapeResult, setLastScrapeResult] = useState<{ jobs_found: number; jobs_new: number } | null>(null);
  const [aiMatchLoading, setAiMatchLoading] = useState(false);

  const getAuthToken = useCallback(() => getStoredToken(), []);

  // ---------------------------------------------------------------------------
  // Fetch discover jobs
  // ---------------------------------------------------------------------------
  const fetchJobs = useCallback(async () => {
    const token = getAuthToken();
    if (!token) {
      setJobsError("Not authenticated. Please log in through Settings.");
      setJobsLoading(false);
      return;
    }

    setJobsLoading(true);
    setJobsError(null);
    try {
      const response = await getJobs(token, filters, page, pageSize);
      setJobs(response.jobs, response.count);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      if (msg.includes("401") || msg.includes("Unauthorized")) {
        setJobsError("Session expired or invalid token. Please log in again through Settings.");
      } else {
        setJobsError("Failed to load jobs. Please try again.");
      }
    } finally {
      setJobsLoading(false);
      setRefreshing(false);
    }
  }, [getAuthToken, filters, page, pageSize, setJobs, setJobsLoading, setJobsError]);

  // ---------------------------------------------------------------------------
  // Fetch saved jobs
  // ---------------------------------------------------------------------------
  const fetchSavedJobs = useCallback(
    async (statusFilter?: string) => {
      const token = getAuthToken();
      if (!token) return;
      setSavedJobsLoading(true);
      try {
        const data = await getSavedJobs(token, statusFilter);
        setSavedJobs(data.jobs);
      } catch (err) {
        console.error("Failed to fetch saved jobs:", err);
      } finally {
        setSavedJobsLoading(false);
      }
    },
    [getAuthToken, setSavedJobs, setSavedJobsLoading],
  );

  // ---------------------------------------------------------------------------
  // Fetch scrape history
  // ---------------------------------------------------------------------------
  const fetchScrapeHistory = useCallback(async () => {
    const token = getAuthToken();
    if (!token) return;
    try {
      const data = await getScrapeHistory(token);
      setScrapeHistory(data);
    } catch (err) {
      console.error("Failed to fetch scrape history:", err);
    }
  }, [getAuthToken, setScrapeHistory]);

  // ---------------------------------------------------------------------------
  // Initial load
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!initialLoaded) {
      setInitialLoaded(true);
      void fetchJobs();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------------------------------------------------------------------------
  // Re-fetch when filters or page change (after initial load)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (initialLoaded) {
      void fetchJobs();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, page]);

  // ---------------------------------------------------------------------------
  // Fetch data when switching tabs
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (activeTab === "saved") {
      void fetchSavedJobs("saved");
    } else if (activeTab === "applied") {
      void fetchSavedJobs();
    } else if (activeTab === "history") {
      void fetchScrapeHistory();
    }
  }, [activeTab, fetchSavedJobs, fetchScrapeHistory]);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------
  const handleRefresh = () => {
    setRefreshing(true);
    if (activeTab === "discover") {
      void fetchJobs();
    } else if (activeTab === "saved") {
      void fetchSavedJobs("saved").finally(() => setRefreshing(false));
    } else if (activeTab === "applied") {
      void fetchSavedJobs().finally(() => setRefreshing(false));
    } else {
      void fetchScrapeHistory().finally(() => setRefreshing(false));
    }
  };

  const handleViewJob = (job: UserJob) => {
    setSelectedJob(job);
    setDetailOpen(true);
  };

  const handleSaveJob = async (jobId: string) => {
    const token = getAuthToken();
    if (!token) return;
    try {
      const saved = await saveJob(token, jobId);
      updateJobInList(jobId, { status: saved.status, keyword_match_score: saved.keyword_match_score, matched_skills: saved.matched_skills, missing_skills: saved.missing_skills });
    } catch (err) {
      console.error("Failed to save job:", err);
    }
  };

  const handleUnsaveJob = async (jobId: string) => {
    const token = getAuthToken();
    if (!token) return;
    try {
      await unsaveJob(token, jobId);
      removeJobFromSaved(jobId);
    } catch (err) {
      console.error("Failed to unsave job:", err);
    }
  };

  const handleStatusChange = async (jobId: string, status: ApplicationStatus, notes?: string) => {
    const token = getAuthToken();
    if (!token) return;
    try {
      const updated = await updateJobStatus(token, jobId, { status, notes });
      updateJobInList(jobId, { status: updated.status });
    } catch (err) {
      console.error("Failed to update job status:", err);
    }
  };

  const handleAiMatch = async (jobId: string) => {
    const token = getAuthToken();
    if (!token) return;
    setAiMatchLoading(true);
    try {
      const result = await triggerAiMatch(token, jobId);
      updateJobInList(jobId, {
        ai_match_score: result.ai_match_score,
        ai_match_summary: result.ai_match_summary,
        matched_skills: result.matched_skills,
        missing_skills: result.missing_skills,
      });
      // Refresh the selected job if it's the one being matched
      if (selectedJob && selectedJob.job_id === jobId) {
        setSelectedJob({
          ...selectedJob,
          ai_match_score: result.ai_match_score,
          ai_match_summary: result.ai_match_summary,
          matched_skills: result.matched_skills,
          missing_skills: result.missing_skills,
        });
      }
    } catch (err) {
      console.error("Failed to trigger AI match:", err);
    } finally {
      setAiMatchLoading(false);
    }
  };

  const handleScrape = async (source: JobSource, query: string, location: string, limit: number) => {
    const token = getAuthToken();
    if (!token) return;
    setScraping(true);
    setLastScrapeResult(null);
    try {
      const result = await scrapeJobs(token, { source, search_query: query, location: location || undefined, limit });
      setLastScrapeResult({ jobs_found: result.jobs_found, jobs_new: result.jobs_new });
    } catch (err) {
      console.error("Failed to scrape jobs:", err);
    } finally {
      setScraping(false);
    }
  };

  const handleScrapeModalClose = (open: boolean) => {
    if (!open) {
      setScrapeModalOpen(false);
      // Refresh jobs if we scraped something
      if (lastScrapeResult) {
        setLastScrapeResult(null);
        void fetchJobs();
      }
    }
  };

  const handleTabChange = (value: string) => {
    setActiveTab(value as JobBoardTab);
  };

  const totalPages = Math.max(1, Math.ceil(jobsCount / pageSize));

  const savedJobIds = new Set(savedJobs.map((j) => j.job_id));

  // Filter applied jobs (status beyond "saved")
  const appliedJobs = savedJobs.filter(
    (j) => j.status === "applied" || j.status === "interviewing" || j.status === "offer" || j.status === "rejected",
  );
  const savedOnlyJobs = savedJobs.filter((j) => j.status === "saved");

  // ---------------------------------------------------------------------------
  // Initial loading screen
  // ---------------------------------------------------------------------------
  if (!initialLoaded || (jobsLoading && jobs.length === 0 && activeTab === "discover")) {
    return (
      <div className="page-container">
        <div className="mx-auto w-full max-w-[1500px]">
          <LoadingState message="Loading job board..." />
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* Hero header */}
      <section className="page-card page-hero">
        <div className="page-header">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl">
              <p className="page-kicker">Career</p>
              <h1 className="text-foreground">Job Board</h1>
              <p className="page-summary">
                Discover jobs matched to your skills, track applications, and manage your job search in one place.
              </p>
              <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
                <span>{jobsCount} job{jobsCount === 1 ? "" : "s"} found</span>
                <span>{savedJobs.length} saved</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button onClick={() => setScrapeModalOpen(true)} variant="default">
                <Search size={18} />
                <span className="font-medium">Scrape Jobs</span>
              </Button>
              <Button onClick={handleRefresh} disabled={refreshing || jobsLoading} variant="outline">
                {refreshing ? <Spinner size={18} /> : <RefreshCw size={18} />}
                <span className="font-medium">Refresh</span>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Error banner */}
      {jobsError && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4">
          <p className="text-sm text-red-400">{jobsError}</p>
        </div>
      )}

      {/* Tab navigation */}
      <Tabs defaultValue={activeTab} onValueChange={handleTabChange}>
        <TabsList>
          <TabsTrigger value="discover">Discover</TabsTrigger>
          <TabsTrigger value="saved">Saved</TabsTrigger>
          <TabsTrigger value="applied">Applied</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        {/* ---- Discover tab ---- */}
        <TabsContent value="discover">
          <div className="flex flex-col gap-6 lg:flex-row">
            {/* Filter sidebar */}
            <aside className="w-full shrink-0 lg:w-64">
              <Section>
                <SectionHeader>
                  <SectionHeading>
                    <SectionTitle>Filters</SectionTitle>
                  </SectionHeading>
                  <SectionActions>
                    <Button variant="ghost" size="sm" onClick={resetFilters}>
                      Reset
                    </Button>
                  </SectionActions>
                </SectionHeader>
                <SectionBody>
                  <JobFilterPanel
                    filters={filters}
                    onFiltersChange={(f) => setFilters(f)}
                    onReset={resetFilters}
                  />
                </SectionBody>
              </Section>
            </aside>

            {/* Job cards grid */}
            <div className="min-w-0 flex-1">
              {jobsLoading ? (
                <div className="flex items-center justify-center py-20">
                  <Spinner size="xl" className="text-muted-foreground" />
                </div>
              ) : jobs.length === 0 ? (
                <EmptyState
                  title="No jobs found"
                  description="Try adjusting your filters or scrape new jobs to populate the board."
                  onRetry={() => void fetchJobs()}
                />
              ) : (
                <>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                    {jobs.map((userJob) => (
                      <JobCard
                        key={userJob.id || userJob.job_id}
                        userJob={userJob}
                        isSaved={savedJobIds.has(userJob.job_id)}
                        onView={() => handleViewJob(userJob)}
                        onSave={() => void handleSaveJob(userJob.job_id)}
                        onUnsave={() => void handleUnsaveJob(userJob.job_id)}
                      />
                    ))}
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="mt-6 flex items-center justify-center gap-4">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={page <= 1}
                        onClick={() => setPage(page - 1)}
                      >
                        <ChevronLeft size={16} />
                        Previous
                      </Button>
                      <span className="text-sm text-muted-foreground">
                        Page {page} of {totalPages}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={page >= totalPages}
                        onClick={() => setPage(page + 1)}
                      >
                        Next
                        <ChevronRight size={16} />
                      </Button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </TabsContent>

        {/* ---- Saved tab ---- */}
        <TabsContent value="saved">
          <Section>
            <SectionHeader>
              <SectionHeading>
                <SectionTitle>Saved Jobs</SectionTitle>
                <SectionDescription>
                  Jobs you bookmarked for later. Save interesting listings to review and apply when ready.
                </SectionDescription>
              </SectionHeading>
            </SectionHeader>
            <SectionBody>
              {savedJobsLoading ? (
                <div className="flex items-center justify-center py-16">
                  <Spinner size="xl" className="text-muted-foreground" />
                </div>
              ) : savedOnlyJobs.length === 0 ? (
                <EmptyState
                  title="No saved jobs yet"
                  description="Browse the Discover tab and bookmark jobs you're interested in."
                  variant="plain"
                />
              ) : (
                <SavedJobsView
                  jobs={savedOnlyJobs}
                  loading={savedJobsLoading}
                  onView={handleViewJob}
                  onStatusChange={handleStatusChange}
                  onUnsave={(jobId) => void handleUnsaveJob(jobId)}
                />
              )}
            </SectionBody>
          </Section>
        </TabsContent>

        {/* ---- Applied tab ---- */}
        <TabsContent value="applied">
          <Section>
            <SectionHeader>
              <SectionHeading>
                <SectionTitle>Applications</SectionTitle>
                <SectionDescription>
                  Track jobs where you have applied, are interviewing, or received an offer.
                </SectionDescription>
              </SectionHeading>
            </SectionHeader>
            <SectionBody>
              {savedJobsLoading ? (
                <div className="flex items-center justify-center py-16">
                  <Spinner size="xl" className="text-muted-foreground" />
                </div>
              ) : appliedJobs.length === 0 ? (
                <EmptyState
                  title="No applications yet"
                  description="Once you mark a saved job as applied, it will appear here."
                  variant="plain"
                />
              ) : (
                <SavedJobsView
                  jobs={appliedJobs}
                  loading={savedJobsLoading}
                  onView={handleViewJob}
                  onStatusChange={handleStatusChange}
                  onUnsave={(jobId) => void handleUnsaveJob(jobId)}
                />
              )}
            </SectionBody>
          </Section>
        </TabsContent>

        {/* ---- History tab ---- */}
        <TabsContent value="history">
          <Section>
            <SectionHeader>
              <SectionHeading>
                <SectionTitle>Scrape History</SectionTitle>
                <SectionDescription>
                  Past scrape runs showing source, query, and how many new jobs were found.
                </SectionDescription>
              </SectionHeading>
            </SectionHeader>
            <SectionBody>
              {scrapeHistory.length === 0 ? (
                <EmptyState
                  title="No scrape history"
                  description="Run your first job scrape to see results here."
                  variant="plain"
                />
              ) : (
                <ScrapeHistoryView runs={scrapeHistory} loading={false} />
              )}
            </SectionBody>
          </Section>
        </TabsContent>
      </Tabs>

      {/* Job detail modal */}
      <JobDetailModal
        userJob={selectedJob}
        open={detailOpen}
        onOpenChange={(open) => {
          setDetailOpen(open);
          if (!open) setSelectedJob(null);
        }}
        onSave={(jobId) => void handleSaveJob(jobId)}
        onUnsave={(jobId) => void handleUnsaveJob(jobId)}
        onStatusChange={handleStatusChange}
        onAiMatch={(jobId) => void handleAiMatch(jobId)}
        aiMatchLoading={aiMatchLoading}
      />

      {/* Scrape modal */}
      <ScrapeModal
        open={scrapeModalOpen}
        onOpenChange={handleScrapeModalClose}
        onScrape={handleScrape}
        scraping={scraping}
        lastResult={lastScrapeResult}
      />
    </div>
  );
}
