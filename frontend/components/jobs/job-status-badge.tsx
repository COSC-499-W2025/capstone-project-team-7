import { cn } from "@/lib/utils";
import type { ApplicationStatus } from "@/types/job";

interface JobStatusBadgeProps {
  status: ApplicationStatus;
}

const statusStyles: Record<ApplicationStatus, string> = {
  unsaved: "bg-neutral-500/20 text-neutral-400",
  saved: "bg-blue-500/20 text-blue-400",
  applied: "bg-amber-500/20 text-amber-400",
  interviewing: "bg-purple-500/20 text-purple-400",
  offer: "bg-green-500/20 text-green-400",
  rejected: "bg-red-500/20 text-red-400",
};

export function JobStatusBadge({ status }: JobStatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize",
        statusStyles[status]
      )}
    >
      {status}
    </span>
  );
}
