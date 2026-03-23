"use client";

import { useState, type ReactNode } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type {
  ResumeStructuredData,
  ResumeContactInfo,
  ResumeEducationEntry,
  ResumeExperienceEntry,
  ResumeSkillsSection,
  ResumeAwardEntry,
} from "@/types/user-resume";

function generateId() {
  return Math.random().toString(36).substring(2, 9);
}

interface ProfileFormProps {
  initialData: ResumeStructuredData;
  onSave: (data: ResumeStructuredData) => Promise<void>;
  saving: boolean;
  saved: boolean;
  error: string | null;
}

export function ProfileForm({
  initialData,
  onSave,
  saving,
  saved,
  error,
}: ProfileFormProps) {
  const [data, setData] = useState<ResumeStructuredData>(initialData);

  // ── Contact ────────────────────────────────────────────────────────────────
  const updateContact = (updates: Partial<ResumeContactInfo>) => {
    setData((d) => ({
      ...d,
      contact: { full_name: "", ...d.contact, ...updates },
    }));
  };

  // ── Education ──────────────────────────────────────────────────────────────
  const addEducation = () => {
    const entry: ResumeEducationEntry = { id: generateId(), institution: "", degree: "" };
    setData((d) => ({ ...d, education: [...(d.education ?? []), entry] }));
  };
  const updateEducation = (idx: number, updates: Partial<ResumeEducationEntry>) => {
    setData((d) => {
      const updated = [...(d.education ?? [])];
      updated[idx] = { ...updated[idx], ...updates };
      return { ...d, education: updated };
    });
  };
  const removeEducation = (idx: number) => {
    setData((d) => ({ ...d, education: (d.education ?? []).filter((_, i) => i !== idx) }));
  };

  // ── Experience ─────────────────────────────────────────────────────────────
  const addExperience = () => {
    const entry: ResumeExperienceEntry = {
      id: generateId(),
      company: "",
      position: "",
      bullets: [],
    };
    setData((d) => ({ ...d, experience: [...(d.experience ?? []), entry] }));
  };
  const updateExperience = (idx: number, updates: Partial<ResumeExperienceEntry>) => {
    setData((d) => {
      const updated = [...(d.experience ?? [])];
      updated[idx] = { ...updated[idx], ...updates };
      return { ...d, experience: updated };
    });
  };
  const removeExperience = (idx: number) => {
    setData((d) => ({
      ...d,
      experience: (d.experience ?? []).filter((_, i) => i !== idx),
    }));
  };

  // ── Skills ─────────────────────────────────────────────────────────────────
  const updateSkillCategory = (category: keyof ResumeSkillsSection, value: string) => {
    const items = value
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    setData((d) => ({ ...d, skills: { ...d.skills, [category]: items } }));
  };

  // ── Awards ─────────────────────────────────────────────────────────────────
  const addAward = () => {
    const entry: ResumeAwardEntry = { id: generateId(), title: "" };
    setData((d) => ({ ...d, awards: [...(d.awards ?? []), entry] }));
  };
  const updateAward = (idx: number, updates: Partial<ResumeAwardEntry>) => {
    setData((d) => {
      const updated = [...(d.awards ?? [])];
      updated[idx] = { ...updated[idx], ...updates };
      return { ...d, awards: updated };
    });
  };
  const removeAward = (idx: number) => {
    setData((d) => ({ ...d, awards: (d.awards ?? []).filter((_, i) => i !== idx) }));
  };

  const handleSave = () => onSave(data);

  return (
    <div className="space-y-8">
      {/* Save bar */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Save your information once and generate any resume instantly.
        </p>
        <div className="flex items-center gap-3">
          {saved && <span className="text-sm text-green-600">✓ Saved</span>}
          {error && <span className="text-sm text-destructive">{error}</span>}
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Saving…" : "Save Profile"}
          </Button>
        </div>
      </div>

      {/* ── Contact ── */}
      <section className="rounded-xl border p-6 space-y-4">
        <h2 className="text-base font-semibold">Contact Information</h2>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Full Name">
            <Input
              value={data.contact?.full_name ?? ""}
              onChange={(e) => updateContact({ full_name: e.target.value })}
              placeholder="Jane Doe"
            />
          </Field>
          <Field label="Email">
            <Input
              type="email"
              value={data.contact?.email ?? ""}
              onChange={(e) => updateContact({ email: e.target.value })}
              placeholder="jane@example.com"
            />
          </Field>
          <Field label="Phone">
            <Input
              value={data.contact?.phone ?? ""}
              onChange={(e) => updateContact({ phone: e.target.value })}
              placeholder="555-123-4567"
            />
          </Field>
          <Field label="Location">
            <Input
              value={data.contact?.location ?? ""}
              onChange={(e) => updateContact({ location: e.target.value })}
              placeholder="City, State"
            />
          </Field>
          <Field label="LinkedIn URL">
            <Input
              value={data.contact?.linkedin_url ?? ""}
              onChange={(e) => updateContact({ linkedin_url: e.target.value })}
              placeholder="https://linkedin.com/in/…"
            />
          </Field>
          <Field label="GitHub URL">
            <Input
              value={data.contact?.github_url ?? ""}
              onChange={(e) => updateContact({ github_url: e.target.value })}
              placeholder="https://github.com/…"
            />
          </Field>
          <div className="col-span-2">
            <Field label="Portfolio URL">
              <Input
                value={data.contact?.portfolio_url ?? ""}
                onChange={(e) => updateContact({ portfolio_url: e.target.value })}
                placeholder="https://yourportfolio.com"
              />
            </Field>
          </div>
        </div>
      </section>

      {/* ── Education ── */}
      <section className="rounded-xl border p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Education</h2>
          <Button variant="outline" size="sm" onClick={addEducation}>
            <Plus size={14} className="mr-1" />
            Add
          </Button>
        </div>
        {(data.education ?? []).length === 0 && (
          <p className="text-sm text-muted-foreground">No education entries yet.</p>
        )}
        {(data.education ?? []).map((edu, idx) => (
          <div key={edu.id} className="rounded-lg border bg-muted/30 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">
                {edu.institution || `Education #${idx + 1}`}
              </span>
              <button
                onClick={() => removeEducation(idx)}
                className="text-xs text-destructive hover:underline"
              >
                Remove
              </button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <SmallField label="Institution">
                <Input
                  value={edu.institution}
                  onChange={(e) => updateEducation(idx, { institution: e.target.value })}
                  placeholder="University of British Columbia"
                />
              </SmallField>
              <SmallField label="Degree">
                <Input
                  value={edu.degree}
                  onChange={(e) => updateEducation(idx, { degree: e.target.value })}
                  placeholder="B.Sc. Computer Science"
                />
              </SmallField>
              <SmallField label="Start Date">
                <Input
                  value={edu.start_date ?? ""}
                  onChange={(e) => updateEducation(idx, { start_date: e.target.value })}
                  placeholder="Sep 2021"
                />
              </SmallField>
              <SmallField label="End Date">
                <Input
                  value={edu.end_date ?? ""}
                  onChange={(e) => updateEducation(idx, { end_date: e.target.value })}
                  placeholder="Apr 2025"
                />
              </SmallField>
              <SmallField label="GPA (optional)">
                <Input
                  value={edu.gpa ?? ""}
                  onChange={(e) => updateEducation(idx, { gpa: e.target.value })}
                  placeholder="3.8/4.0"
                />
              </SmallField>
              <SmallField label="Location (optional)">
                <Input
                  value={edu.location ?? ""}
                  onChange={(e) => updateEducation(idx, { location: e.target.value })}
                  placeholder="Vancouver, BC"
                />
              </SmallField>
            </div>
          </div>
        ))}
      </section>

      {/* ── Experience ── */}
      <section className="rounded-xl border p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Work Experience</h2>
          <Button variant="outline" size="sm" onClick={addExperience}>
            <Plus size={14} className="mr-1" />
            Add
          </Button>
        </div>
        {(data.experience ?? []).length === 0 && (
          <p className="text-sm text-muted-foreground">No experience entries yet.</p>
        )}
        {(data.experience ?? []).map((exp, idx) => (
          <div key={exp.id} className="rounded-lg border bg-muted/30 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">
                {exp.position
                  ? `${exp.position} @ ${exp.company}`
                  : `Experience #${idx + 1}`}
              </span>
              <button
                onClick={() => removeExperience(idx)}
                className="text-xs text-destructive hover:underline"
              >
                Remove
              </button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <SmallField label="Company">
                <Input
                  value={exp.company}
                  onChange={(e) => updateExperience(idx, { company: e.target.value })}
                  placeholder="Acme Corp"
                />
              </SmallField>
              <SmallField label="Position">
                <Input
                  value={exp.position}
                  onChange={(e) => updateExperience(idx, { position: e.target.value })}
                  placeholder="Software Engineer"
                />
              </SmallField>
              <SmallField label="Start Date">
                <Input
                  value={exp.start_date ?? ""}
                  onChange={(e) => updateExperience(idx, { start_date: e.target.value })}
                  placeholder="May 2023"
                />
              </SmallField>
              <SmallField label="End Date">
                <Input
                  value={exp.end_date ?? ""}
                  onChange={(e) => updateExperience(idx, { end_date: e.target.value })}
                  placeholder="Aug 2023 or Present"
                />
              </SmallField>
              <div className="col-span-2">
                <SmallField label="Bullet points (one per line)">
                  <Textarea
                    value={(exp.bullets ?? []).join("\n")}
                    onChange={(e) =>
                      updateExperience(idx, { bullets: e.target.value.split("\n") })
                    }
                    placeholder={
                      "Built REST API with FastAPI and PostgreSQL\nReduced query latency by 40%"
                    }
                    rows={3}
                  />
                </SmallField>
              </div>
            </div>
          </div>
        ))}
      </section>

      {/* ── Skills ── */}
      <section className="rounded-xl border p-6 space-y-4">
        <h2 className="text-base font-semibold">Skills</h2>
        <p className="text-sm text-muted-foreground">
          Enter comma-separated values for each category.
        </p>
        <div className="grid grid-cols-2 gap-4">
          {(
            [
              {
                key: "languages" as const,
                label: "Programming Languages",
                placeholder: "Python, TypeScript, Java",
              },
              {
                key: "frameworks" as const,
                label: "Frameworks",
                placeholder: "React, Next.js, FastAPI",
              },
              {
                key: "developer_tools" as const,
                label: "Developer Tools",
                placeholder: "Git, Docker, AWS",
              },
              {
                key: "libraries" as const,
                label: "Libraries",
                placeholder: "NumPy, Pandas, TensorFlow",
              },
            ] as { key: keyof ResumeSkillsSection; label: string; placeholder: string }[]
          ).map(({ key, label, placeholder }) => (
            <Field key={key} label={label}>
              <Input
                value={(data.skills?.[key] as string[] | undefined ?? []).join(", ")}
                onChange={(e) => updateSkillCategory(key, e.target.value)}
                placeholder={placeholder}
              />
            </Field>
          ))}
        </div>
      </section>

      {/* ── Awards ── */}
      <section className="rounded-xl border p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Awards &amp; Honors</h2>
          <Button variant="outline" size="sm" onClick={addAward}>
            <Plus size={14} className="mr-1" />
            Add
          </Button>
        </div>
        {(data.awards ?? []).length === 0 && (
          <p className="text-sm text-muted-foreground">No awards yet.</p>
        )}
        {(data.awards ?? []).map((award, idx) => (
          <div key={award.id} className="rounded-lg border bg-muted/30 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">
                {award.title || `Award #${idx + 1}`}
              </span>
              <button
                onClick={() => removeAward(idx)}
                className="text-xs text-destructive hover:underline"
              >
                Remove
              </button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <SmallField label="Title">
                <Input
                  value={award.title}
                  onChange={(e) => updateAward(idx, { title: e.target.value })}
                  placeholder="Dean's List"
                />
              </SmallField>
              <SmallField label="Issuer">
                <Input
                  value={award.issuer ?? ""}
                  onChange={(e) => updateAward(idx, { issuer: e.target.value })}
                  placeholder="UBC Faculty of Science"
                />
              </SmallField>
              <SmallField label="Date">
                <Input
                  value={award.date ?? ""}
                  onChange={(e) => updateAward(idx, { date: e.target.value })}
                  placeholder="Apr 2024"
                />
              </SmallField>
              <SmallField label="Description (optional)">
                <Input
                  value={award.description ?? ""}
                  onChange={(e) => updateAward(idx, { description: e.target.value })}
                  placeholder="Brief description"
                />
              </SmallField>
            </div>
          </div>
        ))}
      </section>

      {/* Bottom save */}
      <div className="flex justify-end pb-8">
        <Button onClick={handleSave} disabled={saving} size="lg">
          {saving ? "Saving…" : "Save Profile"}
        </Button>
      </div>
    </div>
  );
}

// ── Small helpers ────────────────────────────────────────────────────────────

function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

function SmallField({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1">
      <Label className="text-xs">{label}</Label>
      {children}
    </div>
  );
}
