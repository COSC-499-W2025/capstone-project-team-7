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
      <div
        className={cn(
          "rounded-2xl border border-slate-200 bg-white/95 px-4 py-3 shadow-[0_1px_2px_rgba(15,23,42,0.04)]",
          className,
        )}
      >
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
        <p className="mt-2 text-xl font-semibold tracking-tight text-slate-950">{value}</p>
      </div>
    );
  }

  return (
    <Card
      className={cn(
        "rounded-2xl border border-slate-200 bg-white/95 shadow-[0_1px_2px_rgba(15,23,42,0.04)]",
        className,
      )}
    >
      <CardContent className="p-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
        <p className="mt-2 text-xl font-semibold tracking-tight text-slate-950">{value}</p>
      </CardContent>
    </Card>
  );
}
