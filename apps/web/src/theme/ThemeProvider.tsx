"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type ThemePreference = "light" | "dark" | "system";
type AppliedTheme = "light" | "dark";
type ThemeContextValue = {
  theme: ThemePreference;
  appliedTheme: AppliedTheme;
  setTheme: (theme: ThemePreference) => void;
  cycleTheme: () => void;
};

const STORAGE_KEY = "polaryix:theme";
const COOKIE_KEY = "polaryix_theme";
const ThemeContext = createContext<ThemeContextValue | null>(null);

function cookieValue(name: string) {
  if (typeof document === "undefined") return "";
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1] ?? "";
}

function isThemePreference(value: string | null): value is ThemePreference {
  return value === "light" || value === "dark" || value === "system";
}

function getSystemTheme(): AppliedTheme {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(preference: ThemePreference, systemTheme = getSystemTheme()) {
  const appliedTheme = preference === "system" ? systemTheme : preference;
  document.documentElement.dataset.theme = appliedTheme;
  document.documentElement.classList.toggle("dark", appliedTheme === "dark");
  return appliedTheme;
}

function persistTheme(theme: ThemePreference) {
  window.localStorage.setItem(STORAGE_KEY, theme);
  document.cookie = `${COOKIE_KEY}=${theme}; path=/; max-age=31536000; SameSite=Lax`;
}

function detectPreference(): ThemePreference {
  if (typeof window === "undefined") return "system";
  const stored = window.localStorage.getItem(STORAGE_KEY) || cookieValue(COOKIE_KEY);
  return isThemePreference(stored) ? stored : "system";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemePreference>("system");
  const [appliedTheme, setAppliedTheme] = useState<AppliedTheme>("light");

  useEffect(() => {
    const detected = detectPreference();
    setThemeState(detected);
    setAppliedTheme(applyTheme(detected));
  }, []);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = () => {
      if (theme === "system") {
        setAppliedTheme(applyTheme("system", media.matches ? "dark" : "light"));
      }
    };
    media.addEventListener("change", handleChange);
    return () => media.removeEventListener("change", handleChange);
  }, [theme]);

  const value = useMemo<ThemeContextValue>(() => {
    function setTheme(nextTheme: ThemePreference) {
      persistTheme(nextTheme);
      setThemeState(nextTheme);
      setAppliedTheme(applyTheme(nextTheme));
    }

    function cycleTheme() {
      setTheme(theme === "dark" ? "light" : "dark");
    }

    return { theme, appliedTheme, setTheme, cycleTheme };
  }, [appliedTheme, theme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used inside ThemeProvider");
  }
  return context;
}
