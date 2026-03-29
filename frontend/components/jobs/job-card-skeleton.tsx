import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function JobCardSkeleton() {
  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        {/* Top row: logo + title + bookmark */}
        <div className="flex items-start gap-3">
          <Skeleton className="h-10 w-10 shrink-0 rounded-full" />
          <Skeleton className="h-5 flex-1 rounded" />
          <Skeleton className="h-6 w-6 shrink-0 rounded" />
        </div>

        {/* Second row: company + location */}
        <div className="flex items-center gap-3">
          <Skeleton className="h-4 w-28 rounded" />
          <Skeleton className="h-4 w-24 rounded" />
        </div>

        {/* Third row: skill badges */}
        <div className="flex flex-wrap gap-2">
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-5 w-14 rounded-full" />
          <Skeleton className="h-5 w-18 rounded-full" />
        </div>

        {/* Bottom row: score + source + date */}
        <div className="flex items-center gap-3">
          <Skeleton className="h-4 w-12 rounded" />
          <Skeleton className="h-4 w-16 rounded" />
          <Skeleton className="ml-auto h-4 w-20 rounded" />
        </div>
      </CardContent>
    </Card>
  );
}
