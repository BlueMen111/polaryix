import type { MetadataRoute } from "next";

const routes = [
  "/",
  "/image/remove-background",
  "/image/optimize",
  "/image/upscale",
  "/premium",
  "/terms",
  "/security",
  "/convert/dds-to-png",
  "/convert/png-to-dds",
  "/youtube-to-mp3",
  "/youtube-to-mp4",
];

export default function sitemap(): MetadataRoute.Sitemap {
  return routes.map((route) => ({
    url: `https://polaryix.com${route}`,
    lastModified: new Date(),
    changeFrequency: route === "/" ? "daily" : "weekly",
    priority: route === "/" ? 1 : 0.8,
  }));
}
