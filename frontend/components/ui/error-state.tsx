import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardContent className="p-10 text-center text-sm text-red-600 space-y-3">
        <p>{message}</p>
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
