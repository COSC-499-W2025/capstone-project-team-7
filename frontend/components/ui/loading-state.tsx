import { Card, CardContent } from "@/components/ui/card";

interface LoadingStateProps {
  message?: string;
}

export function LoadingState({ message = "Loading…" }: LoadingStateProps) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardContent className="p-10 text-center text-sm text-gray-500 space-y-3">
        <div className="flex justify-center">
          <div className="h-8 w-8 rounded-full border-2 border-gray-300 border-t-gray-700 animate-spin" />
        </div>
        <p>{message}</p>
      </CardContent>
    </Card>
  );
}
