import type { Metadata } from "next";
import { ImageToolWorkspace } from "@/components/ImageToolWorkspace";

export const metadata: Metadata = {
  title: "Remove Background Online | PolarYix",
  description: "Remove image backgrounds online with PolarYix.",
  alternates: { canonical: "/image/remove-background" },
};

export default function RemoveBackgroundPage() {
  return (
    <ImageToolWorkspace
      operation="remove_background"
      eyebrow="Remove Background"
      title="Remove Background Online"
      description="Remove image backgrounds online with PolarYix."
      cost="1 token"
    />
  );
}
