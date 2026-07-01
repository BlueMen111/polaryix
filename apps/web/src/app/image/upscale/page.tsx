import type { Metadata } from "next";
import { ImageToolWorkspace } from "@/components/ImageToolWorkspace";

export const metadata: Metadata = {
  title: "Image Upscaler | PolarYix",
  description: "Upscale images online with PolarYix and improve resolution.",
  alternates: { canonical: "/image/upscale" },
};

export default function UpscaleImagePage() {
  return (
    <ImageToolWorkspace
      operation="upscale_image"
      eyebrow="Image Upscaler"
      title="Image Upscaler"
      description="Upscale images online with PolarYix and improve resolution."
      cost="5 tokens em 2x · 10 tokens em 4x"
    />
  );
}
