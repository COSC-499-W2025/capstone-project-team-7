"use client";

import { create } from "zustand";
import type { ProjectDetail } from "@/types/project";

export type MainTabValue = "overview" | "skills" | "content" | "ai-analysis" | "tools";
export type OverviewTabValue =
  | "overview-main"
  | "languages"
  | "git-analysis";
export type ToolsTabValue =
  | "tools-main"
  | "file-browser"
  | "duplicate-finder";

type RetryLoadProject = (() => Promise<void> | void) | null;

type ProjectPageStore = {
  projectId: string | null;
  project: ProjectDetail | null;
  projectError: string | null;
  projectLoading: boolean;
  activeMainTab: MainTabValue;
  activeOverviewTab: OverviewTabValue;
  activeToolsTab: ToolsTabValue;
  retryLoadProject: RetryLoadProject;
  setProjectId: (projectId: string | null) => void;
  setProject: (project: ProjectDetail | null) => void;
  setProjectError: (projectError: string | null) => void;
  setProjectLoading: (projectLoading: boolean) => void;
  setActiveMainTab: (tab: MainTabValue) => void;
  setActiveOverviewTab: (tab: OverviewTabValue) => void;
  setActiveToolsTab: (tab: ToolsTabValue) => void;
  setRetryLoadProject: (callback: RetryLoadProject) => void;
};

const EMPTY_SCAN_DATA: Record<string, unknown> = {};

export const useProjectPageStore = create<ProjectPageStore>()((set) => ({
  projectId: null,
  project: null,
  projectError: null,
  projectLoading: true,
  activeMainTab: "overview",
  activeOverviewTab: "overview-main",
  activeToolsTab: "tools-main",
  retryLoadProject: null,
  setProjectId: (projectId) => set({ projectId }),
  setProject: (project) => set({ project }),
  setProjectError: (projectError) => set({ projectError }),
  setProjectLoading: (projectLoading) => set({ projectLoading }),
  setActiveMainTab: (activeMainTab) => set({ activeMainTab }),
  setActiveOverviewTab: (activeOverviewTab) => set({ activeOverviewTab }),
  setActiveToolsTab: (activeToolsTab) => set({ activeToolsTab }),
  setRetryLoadProject: (retryLoadProject) => set({ retryLoadProject }),
}));

export const projectPageSelectors = {
  projectId: (state: ProjectPageStore) => state.projectId,
  project: (state: ProjectPageStore) => state.project,
  projectError: (state: ProjectPageStore) => state.projectError,
  projectLoading: (state: ProjectPageStore) => state.projectLoading,
  activeMainTab: (state: ProjectPageStore) => state.activeMainTab,
  activeOverviewTab: (state: ProjectPageStore) => state.activeOverviewTab,
  activeToolsTab: (state: ProjectPageStore) => state.activeToolsTab,
  hasProject: (state: ProjectPageStore) => Boolean(state.project),
  scanData: (state: ProjectPageStore) =>
    (state.project?.scan_data as Record<string, unknown> | undefined) ??
    EMPTY_SCAN_DATA,
  retryLoadProject: (state: ProjectPageStore) => state.retryLoadProject,
  setProjectId: (state: ProjectPageStore) => state.setProjectId,
  setProject: (state: ProjectPageStore) => state.setProject,
  setProjectError: (state: ProjectPageStore) => state.setProjectError,
  setProjectLoading: (state: ProjectPageStore) => state.setProjectLoading,
  setActiveMainTab: (state: ProjectPageStore) => state.setActiveMainTab,
  setActiveOverviewTab: (state: ProjectPageStore) => state.setActiveOverviewTab,
  setActiveToolsTab: (state: ProjectPageStore) => state.setActiveToolsTab,
  setRetryLoadProject: (state: ProjectPageStore) => state.setRetryLoadProject,
};

export type { ProjectPageStore };
