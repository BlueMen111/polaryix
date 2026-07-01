import type { Metadata } from "next";
import { ConversionSeoLanding } from "@/components/SeoToolLanding";
import { findConversionSeoPage } from "@/lib/toolSeoPages";

const page = findConversionSeoPage("png-to-dds")!;

export const metadata: Metadata = {
  title: page.title,
  description: page.description,
  alternates: { canonical: "/convert/png-to-dds" },
};

export default function PngToDdsPage() {
  return <ConversionSeoLanding page={page} />;
}
