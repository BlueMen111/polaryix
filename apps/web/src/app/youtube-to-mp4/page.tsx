import type { Metadata } from "next";
import { DownloadSeoLanding } from "@/components/SeoToolLanding";
import { findDownloadSeoPage } from "@/lib/toolSeoPages";

const page = findDownloadSeoPage("youtube-to-mp4")!;

export const metadata: Metadata = {
  title: page.title,
  description: page.description,
  alternates: { canonical: "/youtube-to-mp4" },
};

export default function YoutubeToMp4Page() {
  return <DownloadSeoLanding page={page} />;
}
