"use client";

import type { ReactNode } from "react";
import { LanguageProvider } from "@/i18n/LanguageProvider";
import { ThemeProvider } from "@/theme/ThemeProvider";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <LanguageProvider>{children}</LanguageProvider>
    </ThemeProvider>
  );
}
