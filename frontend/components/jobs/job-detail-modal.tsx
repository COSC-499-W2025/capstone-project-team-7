"use client";

import { ExternalLink, Sparkles, Bookmark, BookmarkCheck, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { UserJob, ApplicationStatus } from "@/types/job";

interface JobDetailModalProps {
  userJob: UserJob | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (jobId: string) => void;
  onUnsave: (jobId: string) => void;
  onStatusChange: (jobId: string, status: ApplicationStatus, notes?: string) => void;
  onAiMatch: (jobId: string) => void;
  aiMatchLoading?: boolean;
}

const STATUS_OPTIONS: { value: ApplicationStatus; label: string }[] = [
  { value: "saved", label: "Saved" },
  { value: "applied", label: "Applied" },
  { value: "interviewing", label: "Interviewing" },
  { value: "offer", label: "Offer" },
  { value: "rejected", label: "Rejected" },
];

function ScoreBar({ label, score, color }: { label: string; score: number; color: string }) {
  // Backend returns 0.0–1.0; convert to percentage for display
  const raw = score <= 1 ? score * 100 : score;
  const pct = Math.min(Math.max(Math.round(raw), 0), 100);
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className="text-xs font-semibold text-foreground">{pct}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted/60">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function formatSource(source: string): string {
  return source.charAt(0).toUpperCase() + source.slice(1);
}

export function JobDetailModal({
  userJob,
  open,
  onOpenChange,
  onSave,
  onUnsave,
  onStatusChange,
  onAiMatch,
  aiMatchLoading,
}: JobDetailModalProps) {
  const job = userJob?.job;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        {userJob && job ? (
          <>
            {/* Header */}
            <DialogHeader>
              <DialogTitle className="text-xl">{job.title}</DialogTitle>
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <span className="text-sm text-muted-foreground">{job.company}</span>
                {job.location && (
                  <>
                    <span className="text-muted-foreground/40">|</span>
                    <span className="text-sm text-muted-foreground">{job.location}</span>
                  </>
                )}
                {job.is_remote && (
                  <Badge variant="default" className="text-[10px]">Remote</Badge>
                )}
                <Badge variant="secondary" className="text-[10px]">
                  {formatSource(job.source)}
                </Badge>
              </div>
            </DialogHeader>

            {/* Match Scores */}
            <div className="flex flex-col gap-3 rounded-2xl border border-border/60 bg-card/50 p-4">
              <h4 className="text-sm font-semibold text-foreground">Match Scores</h4>
              {userJob.keyword_match_score != null && (
                <ScoreBar
                  label="Keyword Match"
                  score={userJob.keyword_match_score}
                  color="bg-primary"
                />
              )}
              {userJob.ai_match_score != null && (
                <ScoreBar
                  label="AI Match"
                  score={userJob.ai_match_score}
                  color="bg-emerald-500"
                />
              )}
              {userJob.keyword_match_score == null && userJob.ai_match_score == null && (
                <p className="text-xs text-muted-foreground">No match scores available yet.</p>
              )}
              <Button
                variant="outline"
                size="sm"
                disabled={aiMatchLoading}
                onClick={() => onAiMatch(userJob.job_id)}
              >
                {aiMatchLoading ? (
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                )}
                {aiMatchLoading ? "Analyzing..." : "Run AI Match"}
              </Button>
            </div>

            {/* Skills */}
            {(userJob.matched_skills.length > 0 || userJob.missing_skills.length > 0) && (
              <div className="flex flex-col gap-3 rounded-2xl border border-border/60 bg-card/50 p-4">
                <h4 className="text-sm font-semibold text-foreground">Skills</h4>
                <div className="grid grid-cols-2 gap-4">
                  {/* Matched Skills */}
                  <div className="flex flex-col gap-1.5">
                    <span className="text-xs font-medium text-emerald-400">Matched Skills</span>
                    <div className="flex flex-wrap gap-1.5">
                      {userJob.matched_skills.length > 0 ? (
                        userJob.matched_skills.map((skill) => (
                          <Badge
                            key={skill}
                            className="border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-[10px]"
                          >
                            {skill}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-xs text-muted-foreground">None</span>
                      )}
                    </div>
                  </div>
                  {/* Missing Skills */}
                  <div className="flex flex-col gap-1.5">
                    <span className="text-xs font-medium text-red-400">Missing Skills</span>
                    <div className="flex flex-wrap gap-1.5">
                      {userJob.missing_skills.length > 0 ? (
                        userJob.missing_skills.map((skill) => (
                          <Badge
                            key={skill}
                            variant="secondary"
                            className="border-red-500/20 bg-red-500/10 text-red-400 text-[10px]"
                          >
                            {skill}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-xs text-muted-foreground">None</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* AI Summary */}
            {userJob.ai_match_summary && (
              <div className="rounded-2xl border border-primary/20 bg-primary/5 p-4">
                <div className="flex items-center gap-1.5 pb-2">
                  <Sparkles className="h-3.5 w-3.5 text-primary" />
                  <h4 className="text-sm font-semibold text-foreground">AI Summary</h4>
                </div>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {userJob.ai_match_summary}
                </p>
              </div>
            )}

            {/* Description */}
            {job.description && (
              <div className="flex flex-col gap-2">
                <h4 className="text-sm font-semibold text-foreground">Description</h4>
                <div className="max-h-60 overflow-y-auto rounded-2xl border border-border/60 bg-card/50 p-4">
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
                    {job.description}
                  </p>
                </div>
              </div>
            )}

            {/* Application Tracking */}
            <div className="flex flex-col gap-3 rounded-2xl border border-border/60 bg-card/50 p-4">
              <h4 className="text-sm font-semibold text-foreground">Application Tracking</h4>
              <div className="flex flex-col gap-3">
                <div className="flex flex-col gap-1.5">
                  <Label>Status</Label>
                  <Select
                    value={userJob.status}
                    onValueChange={(val) =>
                      onStatusChange(userJob.job_id, val as ApplicationStatus, userJob.notes ?? undefined)
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {STATUS_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Notes</Label>
                  <Textarea
                    placeholder="Add notes about this application..."
                    defaultValue={userJob.notes ?? ""}
                    className="min-h-[80px]"
                    onBlur={(e) => {
                      const newNotes = e.target.value;
                      if (newNotes !== (userJob.notes ?? "")) {
                        onStatusChange(userJob.job_id, userJob.status, newNotes || undefined);
                      }
                    }}
                  />
                </div>
                {userJob.applied_at && (
                  <p className="text-xs text-muted-foreground">
                    Applied: {new Date(userJob.applied_at).toLocaleDateString()}
                  </p>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 pt-1">
              {userJob.status === "saved" ? (
                <Button variant="outline" size="sm" onClick={() => onUnsave(userJob.job_id)}>
                  <BookmarkCheck className="mr-1.5 h-4 w-4" />
                  Unsave
                </Button>
              ) : (
                <Button variant="outline" size="sm" onClick={() => onSave(userJob.job_id)}>
                  <Bookmark className="mr-1.5 h-4 w-4" />
                  Save
                </Button>
              )}
              {job.url && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => window.open(job.url!, "_blank", "noopener,noreferrer")}
                >
                  <ExternalLink className="mr-1.5 h-4 w-4" />
                  View Original
                </Button>
              )}
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center py-12">
            <p className="text-sm text-muted-foreground">No job selected.</p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
