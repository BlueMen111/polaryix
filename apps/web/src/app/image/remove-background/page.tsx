"use client";

import { ImageToolWorkspace } from "@/components/ImageToolWorkspace";
import { useLanguage } from "@/i18n/LanguageProvider";

export default function RemoveBackgroundPage() {
  const { t } = useLanguage();

  return (
    <ImageToolWorkspace
      operation="remove_background"
      eyebrow={t("image.removeBackground.title")}
      title={t("image.removeBackground.pageTitle")}
      description={t("image.removeBackground.pageDescription")}
      cost="1 token"
    />
  );
}
