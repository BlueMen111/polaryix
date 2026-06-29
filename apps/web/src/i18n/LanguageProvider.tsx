"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { type Language, translations } from "./translations";

type TranslationValues = Record<string, string | number>;
type LanguageContextValue = {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: string, values?: TranslationValues) => string;
};

const STORAGE_KEY = "polaryix:language";
const COOKIE_KEY = "polaryix_language";
const LanguageContext = createContext<LanguageContextValue | null>(null);

function cookieValue(name: string) {
  if (typeof document === "undefined") return "";
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1] ?? "";
}

function persistLanguage(language: Language) {
  window.localStorage.setItem(STORAGE_KEY, language);
  document.cookie = `${COOKIE_KEY}=${language}; path=/; max-age=31536000; SameSite=Lax`;
}

function detectLanguage(): Language {
  if (typeof window === "undefined") return "pt-BR";
  const stored = window.localStorage.getItem(STORAGE_KEY) || cookieValue(COOKIE_KEY);
  if (stored === "pt-BR" || stored === "en-US") return stored;
  return window.navigator.language.toLowerCase().startsWith("pt") ? "pt-BR" : "en-US";
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>("pt-BR");

  useEffect(() => {
    const detected = detectLanguage();
    setLanguageState(detected);
    document.documentElement.lang = detected;
  }, []);

  const value = useMemo<LanguageContextValue>(() => {
    function setLanguage(nextLanguage: Language) {
      persistLanguage(nextLanguage);
      setLanguageState(nextLanguage);
      document.documentElement.lang = nextLanguage;
    }

    function t(key: string, values: TranslationValues = {}) {
      const template = translations[language][key] ?? translations["pt-BR"][key] ?? key;
      return Object.entries(values).reduce((text, [name, nextValue]) => text.replaceAll(`{${name}}`, String(nextValue)), template);
    }

    return { language, setLanguage, t };
  }, [language]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used inside LanguageProvider");
  }
  return context;
}
