import { cn } from "@/lib/utils";
import { Sparkles } from "lucide-react";

interface MatchScoreIndicatorProps {
  score: number | null;
  label?: string;
  isAi?: boolean;
}

function getScoreColor(score: number): string {
  if (score >= 70) return "text-green-400";
  if (score >= 40) return "text-amber-400";
  return "text-red-400";
}

function getBarColor(score: number): string {
  if (score >= 70) return "bg-green-400";
  if (score >= 40) return "bg-amber-400";
  return "bg-red-400";
}

export function MatchScoreIndicator({ score, label, isAi }: MatchScoreIndicatorProps) {
  if (score === null) {
    return (
      <div className="flex flex-col gap-1">
        {label && (
          <span className="text-[11px] text-muted-foreground">{label}</span>
        )}
        <span className="text-xs text-muted-foreground">No match</span>
      </div>
    );
  }

  // Backend returns 0.0–1.0; convert to percentage for display
  const pct = score <= 1 ? score * 100 : score;
  const clamped = Math.max(0, Math.min(100, Math.round(pct)));

  return (
    <div className="flex w-20 flex-col gap-1">
      {label && (
        <span className="text-[11px] text-muted-foreground">{label}</span>
      )}
      <div className="flex items-center gap-1.5">
        <span className={cn("text-sm font-semibold tabular-nums", getScoreColor(clamped))}>
          {clamped}%
        </span>
        {isAi && (
          <span className="inline-flex items-center gap-0.5 rounded bg-purple-500/20 px-1 py-0.5 text-[10px] font-semibold text-purple-400">
            <Sparkles className="h-2.5 w-2.5" />
            AI
          </span>
        )}
      </div>
      <div className="h-1 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={cn("h-full rounded-full transition-all", getBarColor(clamped))}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
