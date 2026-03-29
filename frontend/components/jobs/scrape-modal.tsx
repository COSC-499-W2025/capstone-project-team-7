"use client";

import { useState } from "react";
import { Search, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import type { JobSource } from "@/types/job";

interface ScrapeModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onScrape: (source: JobSource, query: string, location: string, limit: number) => void;
  scraping: boolean;
  lastResult: { jobs_found: number; jobs_new: number } | null;
}

const SOURCES: { value: JobSource; label: string; icon: string }[] = [
  { value: "linkedin", label: "LinkedIn", icon: "in" },
  { value: "indeed", label: "Indeed", icon: "I" },
];

export function ScrapeModal({
  open,
  onOpenChange,
  onScrape,
  scraping,
  lastResult,
}: ScrapeModalProps) {
  const [source, setSource] = useState<JobSource | null>(null);
  const [query, setQuery] = useState("");
  const [location, setLocation] = useState("");
  const [limit, setLimit] = useState(25);

  const canSubmit = source !== null && query.trim().length > 0 && !scraping;

  function handleSubmit() {
    if (!canSubmit || !source) return;
    onScrape(source, query.trim(), location.trim(), Math.min(Math.max(limit, 1), 100));
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Scrape Jobs</DialogTitle>
          <DialogDescription>
            Search for new job listings from external sources.
          </DialogDescription>
        </DialogHeader>

        {/* Source Picker */}
        <div className="flex flex-col gap-2">
          <Label>Source</Label>
          <div className="grid grid-cols-3 gap-2">
            {SOURCES.map((s) => (
              <button
                key={s.value}
                type="button"
                onClick={() => setSource(s.value)}
                className={`flex flex-col items-center gap-1.5 rounded-xl border px-3 py-3 text-sm font-medium transition-colors ${
                  source === s.value
                    ? "border-primary/50 bg-primary/10 text-primary"
                    : "border-border/60 bg-card/50 text-muted-foreground hover:border-border hover:bg-accent/70 hover:text-foreground"
                }`}
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted/50 text-xs font-bold">
                  {s.icon}
                </span>
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Search Query */}
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="scrape-query">Search Query</Label>
          <Input
            id="scrape-query"
            placeholder="e.g. Software Engineer"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSubmit();
            }}
          />
        </div>

        {/* Location */}
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="scrape-location">Location</Label>
          <Input
            id="scrape-location"
            placeholder="e.g. San Francisco, Remote"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
        </div>

        {/* Limit */}
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="scrape-limit">Limit</Label>
          <Input
            id="scrape-limit"
            type="number"
            min={1}
            max={100}
            value={limit}
            onChange={(e) => {
              const val = parseInt(e.target.value, 10);
              if (!isNaN(val)) setLimit(val);
            }}
          />
          <p className="text-xs text-muted-foreground">Number of jobs to fetch (1-100)</p>
        </div>

        {/* Scrape Button */}
        <Button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="w-full"
        >
          {scraping ? (
            <>
              <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
              Scraping...
            </>
          ) : (
            <>
              <Search className="mr-1.5 h-4 w-4" />
              Scrape Jobs
            </>
          )}
        </Button>

        {/* Results Summary */}
        {lastResult && !scraping && (
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3">
            <p className="text-sm font-medium text-emerald-400">
              Found {lastResult.jobs_found} jobs ({lastResult.jobs_new} new)
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
