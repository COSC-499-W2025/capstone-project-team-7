import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "secondary" | "outline";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const variantClasses: Record<BadgeVariant, string> = {
  default:
    "border border-primary/20 bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--accent-foreground))]",
  secondary:
    "border border-border/80 bg-secondary/85 text-secondary-foreground",
  outline:
    "border border-border/80 bg-card/70 text-foreground"
};

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] transition-colors",
        variantClasses[variant],
        className
      )}
      {...props}
    />
  );
}
