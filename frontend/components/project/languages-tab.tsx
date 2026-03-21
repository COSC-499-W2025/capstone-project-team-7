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
    <Card className="rounded-[18px]">
      <CardHeader className="border-b border-border">
        <CardTitle className="text-xl font-bold text-foreground">
          Language Breakdown
        </CardTitle>
      </CardHeader>
      <CardContent className="p-6">
        {topLanguages.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No language data available for this project.
          </p>
        ) : (
          <div className="space-y-4">
            {topLanguages.map((lang) => (
              <div key={lang.name} className="space-y-2 rounded-[14px] border border-border bg-muted/70 p-4">
                <div className="flex justify-between text-sm">
                  <span className="font-medium text-foreground">{lang.name}</span>
                  <span className="text-muted-foreground">{lang.percentage}%</span>
                </div>
                <div className="w-full bg-background rounded-md h-2">
                  <div
                    className="bg-foreground h-2 rounded-md transition-all"
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
