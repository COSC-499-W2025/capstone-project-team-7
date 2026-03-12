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
      <p className="text-sm text-gray-600">{title}</p>
      {description && (
        <p className="text-xs text-gray-400">{description}</p>
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
      <div className={cn("text-center py-12 space-y-3", className)}>
        {content}
      </div>
    );
  }

  return (
    <Card className={cn("bg-white border border-gray-200", className)}>
      <CardContent className="p-10 text-center space-y-3">
        {content}
      </CardContent>
    </Card>
  );
}
