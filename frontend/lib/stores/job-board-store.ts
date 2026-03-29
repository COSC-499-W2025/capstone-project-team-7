"use client";

import { create } from "zustand";
import type { UserJob, JobFilters, ScrapeRun } from "@/types/job";

export type JobBoardTab = "discover" | "saved" | "applied" | "history";

type JobBoardStore = {
  jobs: UserJob[];
  jobsCount: number;
  jobsLoading: boolean;
  jobsError: string | null;

  filters: JobFilters;
  page: number;
  pageSize: number;

  activeTab: JobBoardTab;

  selectedJob: UserJob | null;
  detailOpen: boolean;

  scraping: boolean;
  scrapeError: string | null;

  savedJobs: UserJob[];
  savedJobsLoading: boolean;

  scrapeHistory: ScrapeRun[];

  setJobs: (jobs: UserJob[], count: number) => void;
  setJobsLoading: (loading: boolean) => void;
  setJobsError: (error: string | null) => void;

  setFilters: (filters: Partial<JobFilters>) => void;
  resetFilters: () => void;

  setPage: (page: number) => void;
  setActiveTab: (tab: JobBoardTab) => void;

  setSelectedJob: (job: UserJob | null) => void;
  setDetailOpen: (open: boolean) => void;

  setScraping: (scraping: boolean) => void;
  setScrapeError: (error: string | null) => void;

  setSavedJobs: (jobs: UserJob[]) => void;
  setSavedJobsLoading: (loading: boolean) => void;

  updateJobInList: (jobId: string, updates: Partial<UserJob>) => void;
  removeJobFromSaved: (jobId: string) => void;

  setScrapeHistory: (history: ScrapeRun[]) => void;
};

export const useJobBoardStore = create<JobBoardStore>()((set) => ({
  jobs: [],
  jobsCount: 0,
  jobsLoading: false,
  jobsError: null,

  filters: {},
  page: 1,
  pageSize: 20,

  activeTab: "discover",

  selectedJob: null,
  detailOpen: false,

  scraping: false,
  scrapeError: null,

  savedJobs: [],
  savedJobsLoading: false,

  scrapeHistory: [],

  setJobs: (jobs, count) => set({ jobs, jobsCount: count }),
  setJobsLoading: (jobsLoading) => set({ jobsLoading }),
  setJobsError: (jobsError) => set({ jobsError }),

  setFilters: (partial) =>
    set((state) => ({ filters: { ...state.filters, ...partial }, page: 1 })),
  resetFilters: () => set({ filters: {}, page: 1 }),

  setPage: (page) => set({ page }),
  setActiveTab: (activeTab) => set({ activeTab }),

  setSelectedJob: (selectedJob) => set({ selectedJob }),
  setDetailOpen: (detailOpen) => set({ detailOpen }),

  setScraping: (scraping) => set({ scraping }),
  setScrapeError: (scrapeError) => set({ scrapeError }),

  setSavedJobs: (savedJobs) => set({ savedJobs }),
  setSavedJobsLoading: (savedJobsLoading) => set({ savedJobsLoading }),

  updateJobInList: (jobId, updates) =>
    set((state) => ({
      jobs: state.jobs.map((j) => (j.job_id === jobId ? { ...j, ...updates } : j)),
      savedJobs: state.savedJobs.map((j) => (j.job_id === jobId ? { ...j, ...updates } : j)),
    })),
  removeJobFromSaved: (jobId) =>
    set((state) => ({
      savedJobs: state.savedJobs.filter((j) => j.job_id !== jobId),
    })),

  setScrapeHistory: (scrapeHistory) => set({ scrapeHistory }),
}));

export const jobBoardSelectors = {
  jobs: (state: JobBoardStore) => state.jobs,
  jobsCount: (state: JobBoardStore) => state.jobsCount,
  jobsLoading: (state: JobBoardStore) => state.jobsLoading,
  jobsError: (state: JobBoardStore) => state.jobsError,
  filters: (state: JobBoardStore) => state.filters,
  page: (state: JobBoardStore) => state.page,
  pageSize: (state: JobBoardStore) => state.pageSize,
  activeTab: (state: JobBoardStore) => state.activeTab,
  selectedJob: (state: JobBoardStore) => state.selectedJob,
  detailOpen: (state: JobBoardStore) => state.detailOpen,
  scraping: (state: JobBoardStore) => state.scraping,
  scrapeError: (state: JobBoardStore) => state.scrapeError,
  savedJobs: (state: JobBoardStore) => state.savedJobs,
  savedJobsLoading: (state: JobBoardStore) => state.savedJobsLoading,
  scrapeHistory: (state: JobBoardStore) => state.scrapeHistory,
  setJobs: (state: JobBoardStore) => state.setJobs,
  setJobsLoading: (state: JobBoardStore) => state.setJobsLoading,
  setJobsError: (state: JobBoardStore) => state.setJobsError,
  setFilters: (state: JobBoardStore) => state.setFilters,
  resetFilters: (state: JobBoardStore) => state.resetFilters,
  setPage: (state: JobBoardStore) => state.setPage,
  setActiveTab: (state: JobBoardStore) => state.setActiveTab,
  setSelectedJob: (state: JobBoardStore) => state.setSelectedJob,
  setDetailOpen: (state: JobBoardStore) => state.setDetailOpen,
  setScraping: (state: JobBoardStore) => state.setScraping,
  setScrapeError: (state: JobBoardStore) => state.setScrapeError,
  setSavedJobs: (state: JobBoardStore) => state.setSavedJobs,
  setSavedJobsLoading: (state: JobBoardStore) => state.setSavedJobsLoading,
  updateJobInList: (state: JobBoardStore) => state.updateJobInList,
  removeJobFromSaved: (state: JobBoardStore) => state.removeJobFromSaved,
  setScrapeHistory: (state: JobBoardStore) => state.setScrapeHistory,
};

export type { JobBoardStore };
