"use client";

import {
  Section,
  SectionBody,
  SectionDescription,
  SectionHeader,
  SectionHeading,
  SectionTitle,
} from "@/components/ui/section";

interface LanguageEntry {
  name: string;
  percentage: number;
}

interface LanguagesTabProps {
  topLanguages: LanguageEntry[];
}

export function LanguagesTab({ topLanguages }: LanguagesTabProps) {
  return (
    <Section>
      <SectionHeader>
        <SectionHeading>
          <SectionTitle>Language Breakdown</SectionTitle>
          <SectionDescription>Relative language share across the scanned codebase.</SectionDescription>
        </SectionHeading>
      </SectionHeader>
      <SectionBody className="pt-0">
        {topLanguages.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No language data available for this project.
          </p>
        ) : (
          <div className="space-y-4">
            {topLanguages.map((lang) => (
              <div key={lang.name} className="space-y-2 rounded-[16px] bg-muted/55 p-4">
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
      </SectionBody>
    </Section>
  );
}
