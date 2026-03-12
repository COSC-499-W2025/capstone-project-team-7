import { Card, CardContent } from "@/components/ui/card";

interface StatCardProps {
  label: string;
  value: string | number;
}

export function StatCard({ label, value }: StatCardProps) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardContent className="p-4">
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-lg font-semibold text-gray-900 mt-1">{value}</p>
      </CardContent>
    </Card>
  );
}
