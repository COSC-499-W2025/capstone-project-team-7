"use client";

import { useCallback, useEffect, useState } from "react";
import {
  jobs,
  type JobListing,
  type JobSearchPayload,
  type ScoredJob,
  type UserJobProfile,
} from "@/lib/api";

interface UseJobMatchReturn {
  results: ScoredJob[];
  total: number;
  loading: boolean;
  error: string | null;
  searchJobs: (search: JobSearchPayload, profile: UserJobProfile, resumeId?: string) => Promise<void>;
  explainJob: (job: JobListing, profile: UserJobProfile) => Promise<string>;
  explaining: string | null;
  savedJobs: JobListing[];
  savedLoading: boolean;
  loadSavedJobs: () => Promise<void>;
  saveJob: (job: JobListing) => Promise<void>;
  unsaveJob: (jobId: string) => Promise<void>;
  isJobSaved: (jobId: string) => boolean;
}

export function useJobMatch(): UseJobMatchReturn {
  const [results, setResults] = useState<ScoredJob[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [explaining, setExplaining] = useState<string | null>(null);

  const [savedJobs, setSavedJobs] = useState<JobListing[]>([]);
  const [savedLoading, setSavedLoading] = useState(false);
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());

  const loadSavedJobs = useCallback(async () => {
    setSavedLoading(true);
    try {
      const res = await jobs.saved.list();
      if (res.ok) {
        setSavedJobs(res.data);
        setSavedIds(new Set(res.data.map((j) => j.id)));
      }
    } finally {
      setSavedLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSavedJobs();
  }, [loadSavedJobs]);

  const saveJob = useCallback(async (job: JobListing) => {
    try {
      const res = await jobs.saved.save(job);
      if (res.ok) {
        setSavedJobs((prev) => [res.data, ...prev]);
        setSavedIds((prev) => new Set(prev).add(job.id));
      } else {
        setError(res.error || "Failed to save job");
      }
    } catch {
      setError("Network error while saving job");
    }
  }, []);

  const unsaveJob = useCallback(async (jobId: string) => {
    try {
      const res = await jobs.saved.remove(jobId);
      if (res.ok) {
        setSavedJobs((prev) => prev.filter((j) => j.id !== jobId));
        setSavedIds((prev) => {
          const next = new Set(prev);
          next.delete(jobId);
          return next;
        });
      } else {
        setError(res.error || "Failed to remove saved job");
      }
    } catch {
      setError("Network error while removing saved job");
    }
  }, []);

  const isJobSaved = useCallback((jobId: string) => savedIds.has(jobId), [savedIds]);

  const searchJobs = useCallback(
    async (search: JobSearchPayload, profile: UserJobProfile, resumeId?: string) => {
      setLoading(true);
      setError(null);
      try {
        const res = await jobs.match(search, profile, resumeId);
        if (!res.ok) {
          setResults([]);
          setTotal(0);
          setError(res.error || "Failed to search jobs");
          return;
        }
        setResults(res.data.jobs);
        setTotal(res.data.total);
      } catch (err) {
        setResults([]);
        setTotal(0);
        setError(err instanceof Error ? err.message : "Network error");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const explainJob = useCallback(
    async (job: JobListing, profile: UserJobProfile): Promise<string> => {
      setExplaining(job.id);
      try {
        const res = await jobs.explain(job, profile);
        if (!res.ok) {
          setError(res.error || "Could not generate explanation");
          return "";
        }
        return res.data.explanation;
      } catch {
        setError("Failed to get explanation");
        return "";
      } finally {
        setExplaining(null);
      }
    },
    [],
  );

  return {
    results, total, loading, error, searchJobs, explainJob, explaining,
    savedJobs, savedLoading, loadSavedJobs, saveJob, unsaveJob, isJobSaved,
  };
}
