import { CheckCircle2, XCircle } from "lucide-react";

export function EligibilityBadge({ ok }: { ok: boolean | null }) {
  if (ok === null)
    return <span className="text-xs text-muted-foreground">Not checked</span>;
  return ok ? (
    <span className="tone-pill tone-pill-emerald inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium">
      <CheckCircle2 size={13} /> Ready
    </span>
  ) : (
    <span className="tone-pill tone-pill-amber inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium">
      <XCircle size={13} /> Not ready
    </span>
  );
}
