"use client";

import Link from "next/link";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import {
  LayoutDashboard,
  FileText,
  BarChart3,
  Code2,
  Award,
  GitBranch,
  Users,
  FileEdit,
  Copy,
  Search,
  FileJson,
  FileCode2,
  Printer,
  FileImage,
  BookOpen,
  Film,
} from "lucide-react";

const tabs = [
  { value: "overview", label: "Show Overview", icon: LayoutDashboard },
  { value: "file-list", label: "View File List", icon: FileText },
  { value: "languages", label: "Language Breakdown", icon: BarChart3 },
  { value: "code-analysis", label: "Code Analysis", icon: Code2 },
  { value: "skills", label: "Skills Analysis", icon: Award },
  { value: "git-analysis", label: "Run Git Analysis", icon: GitBranch },
  { value: "contributions", label: "Contribution Metrics", icon: Users },
  { value: "resume-item", label: "Generate Resume Item", icon: FileEdit },
  { value: "duplicates", label: "Find Duplicate Files", icon: Copy },
  { value: "search-filter", label: "Search and Filter Files", icon: Search },
  { value: "export-json", label: "Export JSON Report", icon: FileJson },
  { value: "export-html", label: "Export HTML Report", icon: FileCode2 },
  { value: "export-print", label: "Export Printable Report", icon: Printer },
  { value: "analyze-pdf", label: "Analyze PDF Files", icon: FileImage },
  { value: "doc-analysis", label: "Document Analysis", icon: BookOpen },
  { value: "media-analysis", label: "Media Analysis", icon: Film },
] as const;

const overviewLanguages = [
  { name: "TypeScript", percentage: 42.3 },
  { name: "Python", percentage: 28.1 },
  { name: "JavaScript", percentage: 15.7 },
  { name: "CSS", percentage: 8.4 },
  { name: "HTML", percentage: 5.5 },
];

function PlaceholderContent({ label }: { label: string }) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardContent className="p-12 text-center">
        <p className="text-gray-500 text-sm">{label} — This section will be available soon.</p>
      </CardContent>
    </Card>
  );
}

export default function ProjectPage() {
  return (
    <div className="p-8">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 mb-6">
        <Link href="/scanned-results" className="text-sm text-gray-600 hover:text-gray-900 mb-2 inline-block">
          ← Back
        </Link>
        <h1 className="text-4xl font-bold text-gray-900 tracking-tight">Project: My Capstone App</h1>
        <p className="text-gray-500 mt-1 text-sm">Scanned project analysis and reports</p>
      </div>

      <Tabs defaultValue="overview">
        <TabsList className="flex flex-wrap gap-1 h-auto bg-gray-100 rounded-lg p-1.5">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <TabsTrigger key={tab.value} value={tab.value} className="gap-1.5 text-xs px-2.5 py-1.5">
                <Icon size={14} />
                {tab.label}
              </TabsTrigger>
            );
          })}
        </TabsList>

        {/* Overview tab with real content */}
        <TabsContent value="overview">
          <div className="space-y-6">
            {/* Project Info */}
            <Card className="bg-white border border-gray-200">
              <CardHeader className="border-b border-gray-200">
                <CardTitle className="text-xl font-bold text-gray-900">Project Information</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Project Name</p>
                    <p className="text-sm font-semibold text-gray-900 mt-1">My Capstone App</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Path</p>
                    <p className="text-sm font-mono text-gray-900 mt-1">/home/user/projects/capstone-app</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Scan Timestamp</p>
                    <p className="text-sm text-gray-900 mt-1">2025-01-15 14:32:07</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Scan Duration</p>
                    <p className="text-sm text-gray-900 mt-1">3.2 seconds</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Summary Stats */}
            <Card className="bg-white border border-gray-200">
              <CardHeader className="border-b border-gray-200">
                <CardTitle className="text-xl font-bold text-gray-900">Summary Statistics</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                  <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-gray-900">247</p>
                    <p className="text-xs text-gray-500 mt-1">Files Processed</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-gray-900">4.8 MB</p>
                    <p className="text-xs text-gray-500 mt-1">Total Size</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-gray-900">12</p>
                    <p className="text-xs text-gray-500 mt-1">Issues Found</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-gray-900">18,432</p>
                    <p className="text-xs text-gray-500 mt-1">Lines of Code</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Top Languages */}
            <Card className="bg-white border border-gray-200">
              <CardHeader className="border-b border-gray-200">
                <CardTitle className="text-xl font-bold text-gray-900">Top 5 Languages</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="space-y-3">
                  {overviewLanguages.map((lang) => (
                    <div key={lang.name} className="flex items-center gap-3">
                      <span className="text-sm text-gray-900 w-28 font-medium">{lang.name}</span>
                      <div className="flex-1 bg-gray-100 rounded-full h-2.5">
                        <div
                          className="bg-gray-900 h-2.5 rounded-full"
                          style={{ width: `${lang.percentage}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-500 w-14 text-right">{lang.percentage}%</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Additional Counts */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card className="bg-white border border-gray-200">
                <CardHeader className="border-b border-gray-200">
                  <CardTitle className="text-base font-bold text-gray-900">Git Repositories</CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <p className="text-3xl font-bold text-gray-900">2</p>
                  <p className="text-xs text-gray-500 mt-1">Repositories detected</p>
                </CardContent>
              </Card>

              <Card className="bg-white border border-gray-200">
                <CardHeader className="border-b border-gray-200">
                  <CardTitle className="text-base font-bold text-gray-900">Media Files</CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <p className="text-3xl font-bold text-gray-900">15</p>
                  <p className="text-xs text-gray-500 mt-1">Images, videos, and audio</p>
                </CardContent>
              </Card>

              <Card className="bg-white border border-gray-200">
                <CardHeader className="border-b border-gray-200">
                  <CardTitle className="text-base font-bold text-gray-900">Documents</CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <div className="flex gap-6">
                    <div>
                      <p className="text-3xl font-bold text-gray-900">3</p>
                      <p className="text-xs text-gray-500 mt-1">PDF files</p>
                    </div>
                    <div>
                      <p className="text-3xl font-bold text-gray-900">8</p>
                      <p className="text-xs text-gray-500 mt-1">Other docs</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* Placeholder tabs */}
        {tabs.slice(1).map((tab) => (
          <TabsContent key={tab.value} value={tab.value}>
            <PlaceholderContent label={tab.label} />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
