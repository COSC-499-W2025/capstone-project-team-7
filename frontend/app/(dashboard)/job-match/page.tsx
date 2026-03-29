"use client";

import React, { useCallback, useState } from "react";
import type { JobListing, JobSearchPayload, UserJobProfile } from "@/lib/api";
import { useJobMatch } from "@/hooks/use-job-match";
import { JobSearchForm } from "@/components/job-match/job-search-form";
import { JobResultsList } from "@/components/job-match/job-results-list";
import { JobCard } from "@/components/job-match/job-card";
import { Target, AlertCircle, Search, Bookmark, Loader2 } from "lucide-react";

type Tab = "search" | "saved";

export default function JobMatchPage() {
  const {
    results, total, loading, error, searchJobs, explainJob, explaining,
    savedJobs, savedLoading, saveJob, unsaveJob, isJobSaved,
  } = useJobMatch();
  const [lastProfile, setLastProfile] = useState<UserJobProfile | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("search");

  const handleSearch = useCallback(
    (search: JobSearchPayload, profile: UserJobProfile, resumeId?: string) => {
      setLastProfile(profile);
      searchJobs(search, profile, resumeId);
    },
    [searchJobs],
  );

  const handleSave = useCallback((job: JobListing) => { saveJob(job); }, [saveJob]);
  const handleUnsave = useCallback((jobId: string) => { unsaveJob(jobId); }, [unsaveJob]);

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Target size={24} />
          Job Match
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Search for jobs and see how well they match your profile. Select a resume
          for AI-powered scoring, or save jobs you&apos;re interested in.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-xl bg-muted/50 p-1">
        <button
          type="button"
          onClick={() => setActiveTab("search")}
          className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "search"
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Search size={14} />
          Search
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("saved")}
          className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "saved"
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Bookmark size={14} />
          My Jobs
          {savedJobs.length > 0 && (
            <span className="ml-1 rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary">
              {savedJobs.length}
            </span>
          )}
        </button>
      </div>

      {/* Search tab */}
      {activeTab === "search" && (
        <>
          <JobSearchForm onSearch={handleSearch} loading={loading} />

          {error && (
            <div className="flex items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          <JobResultsList
            results={results}
            total={total}
            profile={lastProfile}
            onExplain={explainJob}
            explaining={explaining}
            isJobSaved={isJobSaved}
            onSave={handleSave}
            onUnsave={handleUnsave}
          />
        </>
      )}

      {/* Saved / My Jobs tab */}
      {activeTab === "saved" && (
        <div className="space-y-4">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-foreground">
            <Bookmark size={20} />
            My Saved Jobs
            {savedJobs.length > 0 && (
              <span className="text-sm font-normal text-muted-foreground">
                ({savedJobs.length} job{savedJobs.length !== 1 ? "s" : ""})
              </span>
            )}
          </h2>

          {savedLoading && (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <Loader2 size={20} className="animate-spin mr-2" />
              Loading saved jobs…
            </div>
          )}

          {!savedLoading && savedJobs.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground text-sm">
              <Bookmark size={32} className="mb-2 opacity-40" />
              <p>No saved jobs yet.</p>
              <p className="text-xs mt-1">
                Search for jobs and click the Save button to bookmark them here.
              </p>
            </div>
          )}

          <div className="grid gap-3">
            {savedJobs.map((job) => (
              <JobCard
                key={job.id}
                scoredJob={{ job, score: 0, ai_score: null, match_reasons: [] }}
                profile={null}
                onExplain={explainJob}
                explaining={false}
                isSaved
                onUnsave={handleUnsave}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
