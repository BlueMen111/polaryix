import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ConversionSeoLanding } from "@/components/SeoToolLanding";
import { conversionSeoPages, findConversionSeoPage } from "@/lib/toolSeoPages";

type PageProps = {
  params: Promise<{ slug: string }>;
};

export function generateStaticParams() {
  return conversionSeoPages
    .filter((page) => !["dds-to-png", "png-to-dds"].includes(page.slug))
    .map((page) => ({ slug: page.slug }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const page = findConversionSeoPage(slug);

  if (!page) {
    return {};
  }

  return {
    title: page.title,
    description: page.description,
    alternates: { canonical: `/convert/${page.slug}` },
    openGraph: {
      title: page.title,
      description: page.description,
      url: `/convert/${page.slug}`,
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: page.title,
      description: page.description,
    },
  };
}

export default async function ConversionSeoPage({ params }: PageProps) {
  const { slug } = await params;
  const page = findConversionSeoPage(slug);

  if (!page) {
    notFound();
  }

  return <ConversionSeoLanding page={page} />;
}
