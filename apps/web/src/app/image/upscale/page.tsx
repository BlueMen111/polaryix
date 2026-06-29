import { ImageToolWorkspace } from "@/components/ImageToolWorkspace";

export default function UpscaleImagePage() {
  return (
    <ImageToolWorkspace
      operation="upscale_image"
      eyebrow="Upscaling de Imagem"
      title="Aumente a resolução com mais nitidez"
      description="Free usa preset automático com marca d'água. Premium libera 2x, 4x e controles avançados sem marca d'água."
      cost="5 tokens em 2x · 10 tokens em 4x"
    />
  );
}
