import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { DownloadSeoLanding } from "@/components/SeoToolLanding";
import { downloadSeoPages, findDownloadSeoPage } from "@/lib/toolSeoPages";

type PageProps = {
  params: Promise<{ slug: string }>;
};

export function generateStaticParams() {
  return downloadSeoPages.map((page) => ({ slug: page.slug }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const page = findDownloadSeoPage(slug);

  if (!page) {
    return {};
  }

  return {
    title: page.title,
    description: page.description,
    alternates: { canonical: `/download/${page.slug}` },
    openGraph: {
      title: page.title,
      description: page.description,
      url: `/download/${page.slug}`,
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: page.title,
      description: page.description,
    },
  };
}

export default async function DownloadSeoPage({ params }: PageProps) {
  const { slug } = await params;
  const page = findDownloadSeoPage(slug);

  if (!page) {
    notFound();
  }

  return <DownloadSeoLanding page={page} />;
}
