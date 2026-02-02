"use client";

export type AppSettings = {
  defaultSavePath?: string | null;
  enableHighContrast?: boolean;
  enableAnalytics?: boolean;
};

const STORAGE_KEY = "app:settings:v1";

export const loadSettings = (): AppSettings => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as AppSettings;
  } catch {
    return {};
  }
};

export const saveSettings = (s: AppSettings) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
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
