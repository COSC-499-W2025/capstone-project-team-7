import { CheckCircle2, XCircle } from "lucide-react";

export function EligibilityBadge({ ok }: { ok: boolean | null }) {
  if (ok === null)
    return <span className="text-xs text-gray-400">Not checked</span>;
  return ok ? (
    <span className="flex items-center gap-1 text-xs text-green-700 font-medium">
      <CheckCircle2 size={13} /> Ready
    </span>
  ) : (
    <span className="flex items-center gap-1 text-xs text-amber-700 font-medium">
      <XCircle size={13} /> Not ready
    </span>
  );
}
