"use client";

import type { ReactNode } from "react";
import { Suspense } from "react";
import { AnalyticsTracker } from "@/components/AnalyticsTracker";
import { LanguageProvider } from "@/i18n/LanguageProvider";
import { ThemeProvider } from "@/theme/ThemeProvider";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <Suspense fallback={null}>
          <AnalyticsTracker />
        </Suspense>
        {children}
      </LanguageProvider>
    </ThemeProvider>
  );
}
