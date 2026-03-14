import type { SkillEvidenceItem } from "@/types/project";

/**
 * Get a human-friendly label for a skill category key.
 * Falls back to title-casing the key with underscores replaced by spaces.
 */
export function getCategoryLabel(
  key: string,
  categoryLabels: Record<string, string>,
): string {
  return (
    categoryLabels[key] ||
    key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

/**
 * Build a lookup map from the flat skills array for O(1) evidence access.
 */
export function buildEvidenceMap(
  skills: Array<{
    name?: string;
    evidence_count?: number;
    evidence?: SkillEvidenceItem[];
  }>,
): Map<string, SkillEvidenceItem[]> {
  const map = new Map<string, SkillEvidenceItem[]>();
  for (const s of skills) {
    if (s.name) {
      map.set(s.name, Array.isArray(s.evidence) ? s.evidence : []);
    }
  }
  return map;
}

/**
 * Extract the flat skills list from a skills analysis object, with safe fallback.
 */
export function getFullSkillsList(
  skillsAnalysis: { skills?: Array<Record<string, unknown>> } | undefined | null,
): Array<Record<string, unknown>> {
  return Array.isArray(skillsAnalysis?.skills) ? skillsAnalysis.skills : [];
}
