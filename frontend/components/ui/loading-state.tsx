import { cn } from "@/lib/utils";

interface LoadingStateProps {
  message?: string;
  className?: string;
}

export function LoadingState({
  message = "Loading...",
  className,
}: LoadingStateProps) {
  return (
    <section
      aria-live="polite"
      className={cn(
        "relative w-full overflow-hidden rounded-[18px] border border-border bg-gradient-to-b from-card to-background/85",
        className,
      )}
    >
      <div className="absolute inset-0 bg-[linear-gradient(90deg,transparent_0,transparent_calc(100%-1px),hsl(var(--foreground)/0.035)_calc(100%-1px),hsl(var(--foreground)/0.035)_100%),linear-gradient(0deg,transparent_0,transparent_calc(100%-1px),hsl(var(--foreground)/0.035)_calc(100%-1px),hsl(var(--foreground)/0.035)_100%)] bg-[length:30px_30px] opacity-60" />
      <div className="relative mx-auto flex min-h-[280px] max-w-xl flex-col items-center justify-center gap-5 px-8 py-12 text-center">
        <div className="relative flex h-16 w-16 items-center justify-center rounded-full border border-border bg-background/90">
          <div className="absolute inset-[10px] rounded-full border border-border/70" />
          <div className="absolute inset-[10px] rounded-full border-2 border-transparent border-t-foreground/80 animate-spin" />
          <div className="absolute inset-[22px] rounded-full bg-muted/80" />
        </div>
        <div className="space-y-2">
          <p className="page-kicker mb-0 justify-center">Preparing View</p>
          <p className="text-base font-medium text-foreground">{message}</p>
          <p className="text-sm text-muted-foreground">
            Organizing content and analysis into the current layout.
          </p>
        </div>
      </div>
    </section>
  );
}
