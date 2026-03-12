"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

interface LanguageEntry {
  name: string;
  percentage: number;
}

interface LanguagesTabProps {
  topLanguages: LanguageEntry[];
}

export function LanguagesTab({ topLanguages }: LanguagesTabProps) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardHeader className="border-b border-gray-200">
        <CardTitle className="text-xl font-bold text-gray-900">
          Language Breakdown
        </CardTitle>
      </CardHeader>
      <CardContent className="p-6">
        {topLanguages.length === 0 ? (
          <p className="text-sm text-gray-500">
            No language data available for this project.
          </p>
        ) : (
          <div className="space-y-4">
            {topLanguages.map((lang) => (
              <div key={lang.name} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="font-medium text-gray-900">{lang.name}</span>
                  <span className="text-gray-500">{lang.percentage}%</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-gray-900 h-2 rounded-full transition-all"
                    style={{ width: `${lang.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
