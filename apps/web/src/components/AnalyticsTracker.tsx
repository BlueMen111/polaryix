"use client";

import { useEffect } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { recordAnalyticsEvent } from "@/lib/api";

export function AnalyticsTracker() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    const query = searchParams.toString();
    const path = query ? `${pathname}?${query}` : pathname;
    recordAnalyticsEvent({
      eventType: "page_view",
      path,
      referrer: document.referrer || undefined,
    });
  }, [pathname, searchParams]);

  return null;
}
