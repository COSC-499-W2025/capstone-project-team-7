"use client";

import React, { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { JobSearchPayload, UserJobProfile } from "@/lib/api";
import { Search, Loader2, FileText } from "lucide-react";
import { listUserResumes } from "@/lib/api/user-resume";
import { getStoredToken } from "@/lib/auth";
import type { UserResumeSummary } from "@/types/user-resume";

interface JobSearchFormProps {
  onSearch: (search: JobSearchPayload, profile: UserJobProfile, resumeId?: string) => void;
  loading: boolean;
}

export function JobSearchForm({ onSearch, loading }: JobSearchFormProps) {
  const [keywords, setKeywords] = useState("");
  const [location, setLocation] = useState("");
  const [skills, setSkills] = useState("");
  const [jobTitles, setJobTitles] = useState("");
  const [experienceSummary, setExperienceSummary] = useState("");
  const [education, setEducation] = useState("");
  const [salaryMin, setSalaryMin] = useState("");
  const [country, setCountry] = useState("ca");
  const [resumes, setResumes] = useState<UserResumeSummary[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState("");

  useEffect(() => {
    const token = getStoredToken();
    if (!token) return;
    listUserResumes(token).then((resp) => setResumes(resp.items)).catch(() => {});
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const searchPayload: JobSearchPayload = {
      keywords,
      location,
      remote_only: false,
      salary_min: salaryMin ? parseInt(salaryMin, 10) : null,
      category: "",
      results_per_page: 15,
      country,
    };

    const profilePayload: UserJobProfile = {
      skills: skills
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      job_titles: jobTitles
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      experience_summary: experienceSummary,
      education,
    };

    onSearch(searchPayload, profilePayload, selectedResumeId || undefined);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search size={20} />
          Job Preferences
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Resume selector */}
          {resumes.length > 0 && (
            <div className="space-y-1.5">
              <Label htmlFor="resume" className="flex items-center gap-1.5">
                <FileText size={14} />
                Score with Resume (optional)
              </Label>
              <select
                id="resume"
                value={selectedResumeId}
                onChange={(e) => setSelectedResumeId(e.target.value)}
                className="flex h-11 w-full rounded-[14px] border border-input bg-card px-3.5 py-2.5 text-sm text-foreground"
              >
                <option value="">No resume – keyword scoring only</option>
                {resumes.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground">
                Select a resume to get AI-powered match scores based on your actual skills and experience.
              </p>
            </div>
          )}

          {/* Search Fields */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="keywords">Search Keywords</Label>
              <Input
                id="keywords"
                placeholder="e.g. python developer"
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="location">Location</Label>
              <Input
                id="location"
                placeholder="e.g. Vancouver, BC"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="salaryMin">Minimum Salary</Label>
              <Input
                id="salaryMin"
                type="number"
                placeholder="e.g. 70000"
                value={salaryMin}
                onChange={(e) => setSalaryMin(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="country">Country</Label>
              <select
                id="country"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                className="flex h-11 w-full rounded-[14px] border border-input bg-card px-3.5 py-2.5 text-sm text-foreground"
              >
                <option value="ca">Canada</option>
                <option value="us">United States</option>
                <option value="gb">United Kingdom</option>
                <option value="au">Australia</option>
              </select>
            </div>
          </div>

          {/* Profile Fields */}
          <div className="border-t border-border/60 pt-4">
            <p className="text-sm font-medium text-muted-foreground mb-3">
              Your Profile (improves match accuracy)
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="skills">Skills (comma-separated)</Label>
                <Input
                  id="skills"
                  placeholder="e.g. Python, React, SQL"
                  value={skills}
                  onChange={(e) => setSkills(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="jobTitles">Desired Roles (comma-separated)</Label>
                <Input
                  id="jobTitles"
                  placeholder="e.g. Full-Stack Developer, Backend Engineer"
                  value={jobTitles}
                  onChange={(e) => setJobTitles(e.target.value)}
                />
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
              <div className="space-y-1.5">
                <Label htmlFor="experience">Experience Summary</Label>
                <Input
                  id="experience"
                  placeholder="e.g. 2 years building web apps"
                  value={experienceSummary}
                  onChange={(e) => setExperienceSummary(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="education">Education</Label>
                <Input
                  id="education"
                  placeholder="e.g. B.Sc. Computer Science"
                  value={education}
                  onChange={(e) => setEducation(e.target.value)}
                />
              </div>
            </div>
          </div>

          <Button type="submit" disabled={loading} className="w-full sm:w-auto">
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Searching…
              </>
            ) : (
              <>
                <Search size={16} />
                Find Matching Jobs
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
