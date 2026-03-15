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
      <div className={cn("p-3 bg-white border border-gray-200 rounded", className)}>
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-lg font-semibold text-gray-900 mt-1">{value}</p>
      </div>
    );
  }

  return (
    <Card className={cn("bg-white border border-gray-200", className)}>
      <CardContent className="p-4">
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-lg font-semibold text-gray-900 mt-1">{value}</p>
      </CardContent>
    </Card>
  );
}
