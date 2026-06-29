import { ImageToolWorkspace } from "@/components/ImageToolWorkspace";

export default function RemoveBackgroundPage() {
  return (
    <ImageToolWorkspace
      operation="remove_background"
      eyebrow="Remover Fundo"
      title="Remova o fundo e baixe em PNG transparente"
      description="Ideal para produtos, perfis e imagens com objeto principal. Mantemos largura e altura originais."
      cost="1 token"
    />
  );
}
