import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  title: string;
  description?: string;
  onRetry?: () => void;
}

export function EmptyState({ title, description, onRetry }: EmptyStateProps) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardContent className="p-10 text-center space-y-3">
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
      </CardContent>
    </Card>
  );
}
