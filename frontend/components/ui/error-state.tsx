import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <Card>
      <CardContent className="p-10 text-center space-y-3">
        <p className="text-sm text-destructive font-medium">{message}</p>
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
