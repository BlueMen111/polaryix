export type ConversionSeoPage = {
  slug: string;
  source: string;
  target: string;
  title: string;
  description: string;
  eyebrow: string;
};

export type DownloadSeoPage = {
  slug: string;
  provider: "youtube" | "tiktok";
  format: "mp4" | "mp3";
  title: string;
  description: string;
  eyebrow: string;
};

const imageFormats = ["PNG", "DDS", "JPG", "JPEG", "WEBP", "TGA", "BMP", "TIFF", "AVIF", "ICO"];
const videoFormats = ["MP4", "MOV", "AVI", "MKV", "WEBM", "M4V", "FLV", "WMV"];
const audioFormats = ["MP3", "WAV", "AAC", "OGG", "FLAC", "M4A", "WMA"];
const tabularFormats = ["CSV", "JSON", "XML", "HTML", "XLSX"];
const textFormats = ["TXT", "MD"];
const zipInputFormats = [...imageFormats, ...videoFormats, ...audioFormats, ...tabularFormats, ...textFormats];

function slugFor(source: string, target: string) {
  return `${source.toLowerCase()}-to-${target.toLowerCase()}`;
}

function labelFor(source: string, target: string) {
  return `${source} to ${target}`;
}

function pageFor(source: string, target: string, eyebrow: string): ConversionSeoPage {
  const label = labelFor(source, target);
  return {
    slug: slugFor(source, target),
    source,
    target,
    title: `${label} Converter | PolarYix`,
    description: `Convert ${source} files to ${target} online with PolarYix. Use the existing secure converter with ${source} to ${target} already selected.`,
    eyebrow,
  };
}

function pairPages(sources: string[], targets: string[], eyebrow: string) {
  return sources.flatMap((source) => targets.filter((target) => target !== source).map((target) => pageFor(source, target, eyebrow)));
}

const conversionPageMap = new Map<string, ConversionSeoPage>();

[
  ...pairPages(imageFormats, imageFormats, "Image converter"),
  ...pairPages(videoFormats, [...videoFormats, ...audioFormats], "Video converter"),
  ...pairPages(audioFormats, audioFormats, "Audio converter"),
  ...pairPages(tabularFormats, tabularFormats, "File converter"),
  ...pairPages(textFormats, textFormats, "Text converter"),
  ...zipInputFormats.map((source) => pageFor(source, "ZIP", "Archive converter")),
].forEach((page) => {
  conversionPageMap.set(page.slug, page);
});

export const conversionSeoPages = Array.from(conversionPageMap.values()).sort((a, b) => a.slug.localeCompare(b.slug));

export const downloadSeoPages: DownloadSeoPage[] = [
  {
    slug: "youtube-to-mp4",
    provider: "youtube",
    format: "mp4",
    title: "YouTube to MP4 Downloader | PolarYix",
    description: "Prepare public YouTube videos as MP4 files with PolarYix when YouTube allows server-side extraction.",
    eyebrow: "Download by link",
  },
  {
    slug: "youtube-to-mp3",
    provider: "youtube",
    format: "mp3",
    title: "YouTube to MP3 Downloader | PolarYix",
    description: "Prepare public YouTube videos as MP3 audio with PolarYix when YouTube allows server-side extraction.",
    eyebrow: "Download by link",
  },
  {
    slug: "tiktok-to-mp4",
    provider: "tiktok",
    format: "mp4",
    title: "TikTok to MP4 Downloader | PolarYix",
    description: "Paste a public TikTok link and prepare an MP4 download with the existing PolarYix link tool.",
    eyebrow: "Download by link",
  },
  {
    slug: "tiktok-to-mp3",
    provider: "tiktok",
    format: "mp3",
    title: "TikTok to MP3 Downloader | PolarYix",
    description: "Paste a public TikTok link and prepare MP3 audio with the existing PolarYix link tool.",
    eyebrow: "Download by link",
  },
];

export function findConversionSeoPage(slug: string) {
  return conversionPageMap.get(slug);
}

export function findDownloadSeoPage(slug: string) {
  return downloadSeoPages.find((page) => page.slug === slug);
}
