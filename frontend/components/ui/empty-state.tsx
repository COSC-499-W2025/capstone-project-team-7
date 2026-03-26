import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  title: string;
  description?: string;
  onRetry?: () => void;
  /** "card" wraps in a Card component (default). "plain" renders a plain div. */
  variant?: "card" | "plain";
  className?: string;
}

export function EmptyState({ title, description, onRetry, variant = "card", className }: EmptyStateProps) {
  const content = (
    <>
      <p className="text-sm font-medium text-foreground">{title}</p>
      {description && (
        <p className="text-sm text-muted-foreground">{description}</p>
      )}
      {onRetry && (
        <div>
          <Button variant="outline" onClick={onRetry}>
            Retry
          </Button>
        </div>
      )}
    </>
  );

  if (variant === "plain") {
    return (
      <div className={cn("empty-state space-y-3", className)}>
        {content}
      </div>
    );
  }

  return (
    <Card className={cn(className)}>
      <CardContent className="flex min-h-[220px] flex-col justify-center space-y-3 p-10 text-center sm:p-10 sm:pt-10">
        {content}
      </CardContent>
    </Card>
  );
}
