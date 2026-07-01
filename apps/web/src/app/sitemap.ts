import type { MetadataRoute } from "next";
import { conversionSeoPages, downloadSeoPages } from "@/lib/toolSeoPages";

const routes = Array.from(new Set([
  "/",
  "/image/remove-background",
  "/image/optimize",
  "/image/upscale",
  "/premium",
  "/terms",
  "/security",
  "/youtube-to-mp3",
  "/youtube-to-mp4",
  ...conversionSeoPages.map((page) => `/convert/${page.slug}`),
  ...downloadSeoPages.map((page) => `/download/${page.slug}`),
]));

export default function sitemap(): MetadataRoute.Sitemap {
  return routes.map((route) => ({
    url: `https://polaryix.com${route}`,
    lastModified: new Date(),
    changeFrequency: route === "/" ? "daily" : "weekly",
    priority: route === "/" ? 1 : 0.8,
  }));
}
