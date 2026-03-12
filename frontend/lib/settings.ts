"use client";

export type AppSettings = {
  defaultSavePath?: string | null;
  enableHighContrast?: boolean;
  enableAnalytics?: boolean;
  contributionUserName?: string;
  contributionUserEmail?: string;
  contributionEmailAliases?: string;
};

export const SETTINGS_STORAGE_KEY = "app:settings:v1";

export const getSettings = (): AppSettings => {
  try {
    const raw = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as AppSettings;
  } catch {
    return {};
  }
};

export const getContributionHeaders = (): Record<string, string> => {
  if (typeof window === "undefined") {
    return {};
  }

  const settings = getSettings();
  const headers: Record<string, string> = {};
  const userName = settings.contributionUserName?.trim();
  const userEmail = settings.contributionUserEmail?.trim();
  const aliases = settings.contributionEmailAliases
    ?.split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .join(",");

  if (userName) {
    headers["X-Contribution-User-Name"] = userName;
  }
  if (userEmail) {
    headers["X-Contribution-User-Email"] = userEmail;
  }
  if (aliases) {
    headers["X-Contribution-User-Email-Aliases"] = aliases;
  }

  return headers;
};

export const loadSettings = (): AppSettings => {
  return getSettings();
};

export const saveSettings = (s: AppSettings) => {
  try {
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(s));
    return true;
  } catch {
    return false;
  }
};

export type ConsentRecord = {
  id: string;
  granted: boolean;
  purpose: string;
  timestamp: string;
};

const CONSENT_KEY = "app:consents:v1";

export const loadConsents = (): ConsentRecord[] => {
  try {
    const raw = localStorage.getItem(CONSENT_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as ConsentRecord[];
  } catch {
    return [];
  }
};

export const saveConsents = (c: ConsentRecord[]) => {
  try {
    localStorage.setItem(CONSENT_KEY, JSON.stringify(c));
    return true;
  } catch {
    return false;
  }
};
