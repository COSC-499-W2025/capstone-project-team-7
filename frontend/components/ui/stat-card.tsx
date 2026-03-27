import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  /** "card" wraps in a Card component (default). "plain" renders a plain div. */
  variant?: "card" | "plain";
  className?: string;
}

export function StatCard({ label, value, variant = "card", className }: StatCardProps) {
  if (variant === "plain") {
    return (
      <div className={cn("stat-block", className)}>
        <p className="stat-label">{label}</p>
        <p className="stat-value">{value}</p>
      </div>
    );
  }

  return (
    <Card className={cn(className)}>
      <CardContent className="p-4 sm:p-4">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
        <p className="text-xl font-bold text-foreground mt-1">{value}</p>
      </CardContent>
    </Card>
  );
}
