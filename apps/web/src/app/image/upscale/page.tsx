"use client";

import { ImageToolWorkspace } from "@/components/ImageToolWorkspace";
import { useLanguage } from "@/i18n/LanguageProvider";

export default function UpscaleImagePage() {
  const { t } = useLanguage();

  return (
    <ImageToolWorkspace
      operation="upscale_image"
      eyebrow={t("image.upscale.title")}
      title={t("image.upscale.pageTitle")}
      description={t("image.upscale.description")}
      cost={t("image.upscale.cost")}
    />
  );
}
