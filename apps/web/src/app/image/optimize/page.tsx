import type { Metadata } from "next";
import { ImageToolWorkspace } from "@/components/ImageToolWorkspace";

export const metadata: Metadata = {
  title: "Image Optimizer | PolarYix",
  description: "Optimize and compress images online with PolarYix.",
  alternates: { canonical: "/image/optimize" },
};

export default function OptimizeImagePage() {
  return (
    <ImageToolWorkspace
      operation="optimize_image"
      eyebrow="Image Optimizer"
      title="Image Optimizer"
      description="Optimize and compress images online with PolarYix."
      cost="2 tokens"
    />
  );
}
