import type { Metadata } from "next";
import { ConversionSeoLanding } from "@/components/SeoToolLanding";
import { findConversionSeoPage } from "@/lib/toolSeoPages";

const page = findConversionSeoPage("dds-to-png")!;

export const metadata: Metadata = {
  title: page.title,
  description: page.description,
  alternates: { canonical: "/convert/dds-to-png" },
};

export default function DdsToPngPage() {
  return <ConversionSeoLanding page={page} />;
}
