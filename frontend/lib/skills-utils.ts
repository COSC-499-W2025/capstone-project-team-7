import type { SkillEvidenceItem } from "@/types/project";

/**
 * Get a human-readable label for a skill category key.
 * Uses the backend-provided labels when available, falls back to title-casing the key.
 */
export function getCategoryLabel(
  key: string,
  categoryLabels?: Record<string, string>,
): string {
  if (categoryLabels && categoryLabels[key]) {
    return categoryLabels[key];
  }
  // Fallback: title-case the key (e.g. "web_frameworks" → "Web Frameworks")
  return key
    .split(/[_-]/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/**
 * Build a Map from skill name → evidence items for O(1) lookups.
 */
export function buildEvidenceMap(
  skills: Array<{ name?: string; evidence?: SkillEvidenceItem[] }>,
): Map<string, SkillEvidenceItem[]> {
  const map = new Map<string, SkillEvidenceItem[]>();
  for (const skill of skills) {
    if (skill.name && Array.isArray(skill.evidence)) {
      map.set(skill.name, skill.evidence);
    }
  }
  return map;
}
