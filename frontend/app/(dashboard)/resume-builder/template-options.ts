import type { ResumeTemplate } from "@/types/user-resume";

export const TEMPLATE_INFO: Record<ResumeTemplate, { name: string; description: string }> = {
  jake: {
    name: "Jake's Resume",
    description: "Clean, ATS-friendly single-column template",
  },
  classic: {
    name: "Classic",
    description: "Traditional professional layout",
  },
  modern: {
    name: "Modern",
    description: "Contemporary design with clean sections",
  },
  minimal: {
    name: "Minimal",
    description: "Ultra-clean minimalist design",
  },
  custom: {
    name: "Custom",
    description: "Start from scratch",
  },
};

/** Same data as an array – handy for rendering <Select> options. */
export const TEMPLATES: { id: ResumeTemplate; name: string; description: string }[] =
  (Object.keys(TEMPLATE_INFO) as ResumeTemplate[]).map((id) => ({
    id,
    ...TEMPLATE_INFO[id],
  }));
