import { ImageToolWorkspace } from "@/components/ImageToolWorkspace";

export default function OptimizeImagePage() {
  return (
    <ImageToolWorkspace
      operation="optimize_image"
      eyebrow="Otimizar Imagem"
      title="Reduza o peso sem mudar as dimensões"
      description="Remove metadados e aplica compressão real em PNG, JPG e WEBP. Mostramos tamanho original, final e redução."
      cost="2 tokens"
    />
  );
}
