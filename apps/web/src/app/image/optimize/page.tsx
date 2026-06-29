"use client";

import { ImageToolWorkspace } from "@/components/ImageToolWorkspace";
import { useLanguage } from "@/i18n/LanguageProvider";

export default function OptimizeImagePage() {
  const { t } = useLanguage();

  return (
    <ImageToolWorkspace
      operation="optimize_image"
      eyebrow={t("image.optimize.title")}
      title={t("image.optimize.pageTitle")}
      description={t("image.optimize.pageDescription")}
      cost="2 tokens"
    />
  );
}
