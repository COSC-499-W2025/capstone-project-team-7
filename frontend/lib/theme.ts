"use client";

export type Theme = "light" | "dark";

const THEME_KEY = "app:theme:v1";

export const loadTheme = (): Theme => {
  try {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === "light" || stored === "dark") return stored;
    return "dark"; // default
  } catch {
    return "dark";
  }
};

export const saveTheme = (theme: Theme): boolean => {
  try {
    localStorage.setItem(THEME_KEY, theme);
    return true;
  } catch {
    return false;
  }
};

export const applyTheme = (theme: Theme) => {
  if (typeof document !== "undefined") {
    document.documentElement.classList.toggle("dark", theme === "dark");
    document.documentElement.classList.toggle("light", theme === "light");
  }
};
