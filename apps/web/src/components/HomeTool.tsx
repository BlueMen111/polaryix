"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  AuthUser,
  ConversionJob,
  LinkDownloadJob,
  LinkPreview,
  UsageInfo,
  UserComment,
  cancelConversionJob,
  createComment,
  createLinkDownloadJob,
  convertFile,
  convertFiles,
  downloadConversionJob,
  downloadLinkJobFile,
  getConversionJob,
  getLinkDownloadJob,
  getLinkPreview,
  getCurrentUser,
  getUsage,
  listComments,
  persistAuthSession,
} from "@/lib/api";
import { useLanguage } from "@/i18n/LanguageProvider";
import { detectFormatFromFileName, validateConversion, validateFileForConversion } from "@/lib/conversionCompatibility";
import styles from "@/app/page.module.css";

const formatGroups = [
  { titleKey: "home.format.images", formats: ["PNG", "DDS", "JPG", "JPEG", "WEBP", "TGA", "BMP", "TIFF", "AVIF", "SVG", "ICO"] },
  { titleKey: "home.format.videos", formats: ["MP4", "MOV", "AVI", "MKV", "WEBM", "M4V", "FLV", "WMV"] },
  { titleKey: "home.format.audios", formats: ["MP3", "WAV", "AAC", "OGG", "FLAC", "M4A", "WMA"] },
  { titleKey: "home.format.documents", formats: ["PDF", "DOCX", "DOC", "XLSX", "CSV", "PPTX", "TXT", "MD"] },
  { titleKey: "home.format.archives", formats: ["ZIP", "RAR", "7Z", "TAR", "GZ"] },
  { titleKey: "home.format.others", formats: ["JSON", "XML", "HTML", "HEIC", "PSD"] },
];

const allFormats = formatGroups.flatMap((group) => group.formats);
const formatOptions = allFormats.map((format) => ({ value: format, label: format }));

const fallbackComments: UserComment[] = [
  {
    id: "fallback-1",
    message: "Converti meus arquivos em segundos. Muito mais pratico.",
    user_name: "Usuario Polaryix",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "fallback-2",
    message: "Interface limpa, rapida e facil de usar.",
    user_name: "Usuario Polaryix",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "fallback-3",
    message: "O Polaryix economizou muito tempo no meu fluxo de trabalho.",
    user_name: "Usuario Polaryix",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "fallback-4",
    message: "Finalmente um conversor simples e bonito.",
    user_name: "Usuario Polaryix",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "fallback-5",
    message: "O fluxo PNG para DDS ficou direto e sem distracoes.",
    user_name: "Usuario Polaryix",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "fallback-6",
    message: "Uso para testar imagens de jogos e tudo ficou mais agil.",
    user_name: "Usuario Polaryix",
    created_at: "2026-01-01T00:00:00Z",
  },
];

const downloadCards = [
  { name: "YouTube", textKey: "home.downloadYoutube", icon: "/assets/icons/youtube.svg", brand: "youtube" },
  { name: "TikTok", textKey: "home.downloadTikTok", icon: "/assets/icons/tiktok.svg", brand: "tiktok" },
];

const heroBadgeKeys = ["home.badgeFast", "home.badgeSafe", "home.badgeNoLimits"];
const heroFormatPairs = [
  ["PNG", "DDS"],
  ["TXT", "DOCX"],
  ["CSV", "XLSX"],
  ["MP4", "MP3"],
  ["WEBP", "PNG"],
  ["PDF", "DOCX"],
  ["JPG", "PNG"],
];

const downloadOptions = [
  { id: "mp4", label: "MP4", detail: "720p - 7 tokens", mediaType: "video", premium: false },
  { id: "mp3", label: "MP3", detail: "4 tokens", mediaType: "audio", premium: false },
  { id: "4k", label: "4K", detail: "7 tokens - Premium", mediaType: "video", premium: true },
] as const;

function FormatPicker({
  label,
  value,
  isOpen,
  onToggle,
  onSelect,
  t,
}: {
  label: string;
  value: string;
  isOpen: boolean;
  onToggle: () => void;
  onSelect: (value: string) => void;
  t: (key: string) => string;
}) {
  return (
    <div className={styles.formatPicker}>
      <span className={styles.pickerLabel}>{label}</span>
      <button type="button" className={styles.pickerButton} onClick={onToggle} aria-expanded={isOpen}>
        <strong>{value}</strong>
        <span>{t("home.pickFormat")}</span>
      </button>
      {isOpen ? (
        <div className={styles.formatMenu}>
          {formatGroups.map((group) => (
            <section key={group.titleKey}>
              <h3>{t(group.titleKey)}</h3>
              <div>
                {group.formats.map((format) => (
                  <button
                    type="button"
                    key={`${group.titleKey}-${format}`}
                    className={format === value ? styles.activeFormat : undefined}
                    onClick={() => onSelect(format)}
                  >
                    {format}
                  </button>
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function StatusMessage({ message, t }: { message: string; t: (key: string) => string }) {
  const impossiblePrefix = "Essa conversão não é possível.";

  if (message.startsWith(impossiblePrefix)) {
    return (
      <>
        <strong className={styles.errorHighlight}>{t("home.impossiblePrefix")}</strong>
        {message.slice(impossiblePrefix.length)}
      </>
    );
  }

  if (message.startsWith("Essa conversão ainda não é suportada.")) {
    return (
      <>
        <strong className={styles.errorHighlight}>{t("home.unsupportedPrefix")}</strong>
        {message.slice("Essa conversão ainda não é suportada.".length)}
      </>
    );
  }

  return message;
}

type HomePageProps = {
  initialFromFormat?: string;
  initialToFormat?: string;
  initialDownloadFormat?: (typeof downloadOptions)[number]["id"];
  toolMode?: "all" | "converter" | "download";
};

export function HomeTool({
  initialFromFormat = "PNG",
  initialToFormat = "DDS",
  initialDownloadFormat = "mp4",
  toolMode = "all",
}: HomePageProps = {}) {
  const { t } = useLanguage();
  const [fromFormat, setFromFormat] = useState(initialFromFormat);
  const [toFormat, setToFormat] = useState(initialToFormat);
  const [openPicker, setOpenPicker] = useState<"from" | "to" | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [fileName, setFileName] = useState("");
  const [status, setStatus] = useState(t("home.initialStatus"));
  const [downloadUrl, setDownloadUrl] = useState("");
  const [downloadFormat, setDownloadFormat] = useState<(typeof downloadOptions)[number]["id"]>(initialDownloadFormat);
  const [downloadStatus, setDownloadStatus] = useState(t("home.initialDownloadStatus"));
  const [linkPreview, setLinkPreview] = useState<LinkPreview | null>(null);
  const [previewStatus, setPreviewStatus] = useState("");
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [preparedLinkJob, setPreparedLinkJob] = useState<LinkDownloadJob | null>(null);
  const [isConverting, setIsConverting] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isPremium, setIsPremium] = useState(false);
  const [premiumPlan, setPremiumPlan] = useState("basic");
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [comments, setComments] = useState<UserComment[]>([]);
  const [commentMessage, setCommentMessage] = useState("");
  const [commentStatus, setCommentStatus] = useState("");
  const [isPostingComment, setIsPostingComment] = useState(false);
  const [conversionJobs, setConversionJobs] = useState<ConversionJob[]>([]);
  const [usage, setUsage] = useState<UsageInfo | null>(null);
  const [usageError, setUsageError] = useState("");
  const [heroFormatIndex, setHeroFormatIndex] = useState(0);
  const [isHeroFormatSwitching, setIsHeroFormatSwitching] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const conversionLabel = useMemo(() => `${fromFormat} > ${toFormat}`, [fromFormat, toFormat]);
  const acceptList = useMemo(() => allFormats.map((format) => `.${format.toLowerCase()}`).join(","), []);
  const batchLimit = isPremium ? (premiumPlan === "pro" ? 60 : 30) : 2;
  const totalSelectedSize = useMemo(() => selectedFiles.reduce((sum, file) => sum + file.size, 0), [selectedFiles]);
  const [heroFormatFrom, heroFormatTo] = heroFormatPairs[heroFormatIndex];

  useEffect(() => {
    setComments((current) => (current.length ? current : fallbackComments));
  }, []);

  useEffect(() => {
    const token = window.localStorage.getItem("polaryix:auth-token");
    setIsPremium(window.localStorage.getItem("polaryix:isPremium") === "true");
    setPremiumPlan(window.localStorage.getItem("polaryix:premiumPlan") ?? "basic");

    if (token) {
      getCurrentUser()
        .then(({ user }) => {
          persistAuthSession({ token, user });
          setCurrentUser(user);
          setIsPremium(user.is_premium);
          setPremiumPlan(user.plan);
        })
        .catch(() => setCurrentUser(null));
    }
  }, []);

  useEffect(() => {
    listComments()
      .then(({ comments }) => {
        if (comments.length > 0) {
          setComments(comments);
        }
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    refreshUsage();
  }, [isPremium, premiumPlan]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setIsHeroFormatSwitching(true);
      window.setTimeout(() => {
        setHeroFormatIndex((current) => (current + 1) % heroFormatPairs.length);
        setIsHeroFormatSwitching(false);
      }, 220);
    }, 2200);

    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    const activeJobs = conversionJobs.filter((job) => job.status === "queued" || job.status === "processing");
    if (activeJobs.length === 0) {
      return;
    }

    const interval = window.setInterval(async () => {
      const updates = await Promise.allSettled(activeJobs.map((job) => getConversionJob(job.id)));
      setConversionJobs((current) =>
        current.map((job) => {
          const index = activeJobs.findIndex((activeJob) => activeJob.id === job.id);
          const update = index >= 0 ? updates[index] : null;
          return update?.status === "fulfilled" ? update.value.job : job;
        })
      );
    }, 2500);

    return () => window.clearInterval(interval);
  }, [conversionJobs]);

  async function refreshUsage() {
    try {
      const currentUsage = await getUsage({ isPremium, premiumPlan });
      setUsage(currentUsage);
      setUsageError("");
    } catch {
      setUsage(null);
      setUsageError(t("home.usageError"));
    }
  }

  useEffect(() => {
    const normalizedUrl = downloadUrl.trim();

    setLinkPreview(null);
    setPreviewStatus("");

    if (!/^https?:\/\//i.test(normalizedUrl)) {
      return;
    }

    setPreparedLinkJob(null);
    setDownloadProgress(0);

    const timeout = window.setTimeout(async () => {
      setPreviewStatus("Carregando preview...");

      try {
        const preview = await getLinkPreview(normalizedUrl);
        setLinkPreview(preview);
        setPreviewStatus("");
      } catch (error) {
        setPreviewStatus(error instanceof Error ? error.message : t("home.previewError"));
      }
    }, 700);

    return () => window.clearTimeout(timeout);
  }, [downloadUrl]);

  function formatDuration(duration?: number | null) {
    if (!duration) {
      return null;
    }

    const minutes = Math.floor(duration / 60);
    const seconds = Math.floor(duration % 60)
      .toString()
      .padStart(2, "0");

    return `${minutes}:${seconds}`;
  }

  function swapFormats() {
    setFromFormat(toFormat);
    setToFormat(fromFormat);
    setOpenPicker(null);
  }

  function setFiles(files: File[]) {
    const limitedFiles = files.slice(0, batchLimit);
    const detectedFormat = limitedFiles[0] ? detectFormatFromFileName(limitedFiles[0].name) : "";
    const nextFromFormat = detectedFormat || fromFormat;

    if (detectedFormat && detectedFormat !== fromFormat) {
      setFromFormat(detectedFormat);
      setOpenPicker(null);
    }

    setSelectedFiles(limitedFiles);
    setSelectedFile(limitedFiles[0] ?? null);
    setFileName(limitedFiles.map((file) => file.name).join(", "));

    if (files.length > batchLimit) {
      setStatus(`Seu plano permite converter ${batchLimit} arquivo(s) por lote. Mantive os ${batchLimit} primeiros.`);
      return;
    }

    if (limitedFiles.length > 1) {
      const invalidFileMessage = limitedFiles.map((file) => validateFileForConversion(file, nextFromFormat)).find(Boolean);
      const detectedSuffix = detectedFormat ? ` Formato detectado: ${detectedFormat}.` : "";
      setStatus(invalidFileMessage || t("home.filesReadyZip", { count: limitedFiles.length, format: toFormat, suffix: detectedSuffix }));
      return;
    }

    const invalidFileMessage = limitedFiles[0] ? validateFileForConversion(limitedFiles[0], nextFromFormat) : "";
    const detectedSuffix = detectedFormat ? ` Formato detectado: ${detectedFormat}.` : "";
    setStatus(
      invalidFileMessage ||
      (limitedFiles[0]
        ? t("home.fileReadyToConvert", { filename: limitedFiles[0].name, format: toFormat, suffix: detectedSuffix })
        : t("home.initialStatus"))
    );
  }

  function formatFileSize(bytes: number) {
    if (bytes < 1024) {
      return `${bytes} B`;
    }

    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }

    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }

  function tokenLabel() {
    if (usage) {
      return t("home.creditsRemaining", { credits: usage.remaining });
    }

    return t("home.freeCredits");
  }

  function downloadProgressLabel() {
    if (downloadProgress >= 92 && isDownloading) {
      return t("home.finalizingFile");
    }

    if (downloadProgress >= 55 && isDownloading) {
      return t("home.preparingMedia");
    }

    return t("home.progress");
  }

  function downloadProgressHint() {
    if (downloadProgress >= 92 && isDownloading) {
      return t("home.longVideoHint");
    }

    return "";
  }

  function isTokenLimitMessage(message: string) {
    return message.toLowerCase().includes("tokens gratuitos acabaram");
  }

  function removeSelectedFile(indexToRemove: number) {
    setFiles(selectedFiles.filter((_, index) => index !== indexToRemove));
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFiles(Array.from(event.target.files ?? []));
  }

  async function handleConvert() {
    if (selectedFiles.length === 0) {
      setStatus(t("home.chooseFileFirst"));
      fileInputRef.current?.click();
      return;
    }

    const conversionValidation = validateConversion(fromFormat, toFormat);
    if (!conversionValidation.allowed) {
      setStatus(conversionValidation.message);
      return;
    }

    const invalidFileMessage = selectedFiles.map((file) => validateFileForConversion(file, fromFormat)).find(Boolean);
    if (invalidFileMessage) {
      setStatus(invalidFileMessage);
      return;
    }

    setIsConverting(true);
    setStatus(selectedFiles.length > 1 ? t("home.sendingConversions", { count: selectedFiles.length }) : t("home.sendingConversion"));

    try {
      if (selectedFiles.length === 1) {
        const result = await convertFile({
          file: selectedFiles[0],
          fromFormat,
          toFormat,
          isPremium,
          premiumPlan,
        });
        setStatus(`Download iniciado: ${result.filename}`);
      } else {
        const result = await convertFiles({
          files: selectedFiles,
          fromFormat,
          toFormat,
          isPremium,
          premiumPlan,
        });
        setStatus(`Download iniciado: ${result.filename}`);
      }
      await refreshUsage();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Erro ao converter arquivo.");
      await refreshUsage();
    } finally {
      setIsConverting(false);
    }
  }

  async function handleLinkDownload() {
    if (!downloadUrl.trim()) {
      setDownloadStatus(t("home.pasteUrlFirst"));
      return;
    }

    setIsDownloading(true);
    setDownloadProgress(0);
    setPreparedLinkJob(null);
    const selectedOption = downloadOptions.find((option) => option.id === downloadFormat) ?? downloadOptions[0];

    if (selectedOption.premium && !isPremium) {
      setDownloadStatus(t("home.premiumQualityOnly"));
      setIsDownloading(false);
      return;
    }

    setDownloadStatus(`Criando tarefa de download em ${selectedOption.label}...`);

    try {
      let job = await createLinkDownloadJob({
        url: downloadUrl,
        mediaType: selectedOption.mediaType,
        downloadFormat: selectedOption.id,
        isPremium,
        premiumPlan,
      });

      setDownloadProgress(job.progress ?? 3);
      setDownloadStatus(job.message || "Download iniciado...");

      while (job.status === "queued" || job.status === "running") {
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
        job = await getLinkDownloadJob(job.id);
        setDownloadProgress(job.progress ?? 0);
        setDownloadStatus(job.message || t("home.processingDownload"));
      }

      if (job.status === "error") {
        throw new Error(job.message || t("home.downloadCompleteError"));
      }

      setDownloadProgress(100);
      setPreparedLinkJob(job);
      setDownloadStatus("Arquivo pronto. Clique em Baixar para salvar; ele expira em 10 minutos.");
      await refreshUsage();
    } catch (error) {
      setDownloadProgress(0);
      setDownloadStatus(error instanceof Error ? error.message : "Erro ao baixar o link.");
      await refreshUsage();
    } finally {
      setIsDownloading(false);
    }
  }

  async function handlePreparedLinkDownload() {
    if (!preparedLinkJob) {
      return;
    }

    setIsDownloading(true);
    setDownloadStatus("Iniciando download...");
    try {
      const filename = await downloadLinkJobFile(preparedLinkJob);
      setDownloadStatus(`Download iniciado: ${filename}`);
      setPreparedLinkJob(null);
      setDownloadProgress(0);
      await refreshUsage();
    } catch (error) {
      setDownloadStatus(error instanceof Error ? error.message : "Nao foi possivel baixar o arquivo preparado.");
    } finally {
      setIsDownloading(false);
    }
  }

  async function handleCommentSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!currentUser) {
      setCommentStatus("Entre com Google ou com sua conta Polaryix para comentar.");
      return;
    }

    const message = commentMessage.trim();
    if (message.length < 3) {
      setCommentStatus("Escreva um comentario um pouco maior.");
      return;
    }

    setIsPostingComment(true);
    setCommentStatus("Enviando comentario...");

    try {
      const { comment } = await createComment(message);
      setComments((current) => [comment, ...current.filter((item) => !item.id.startsWith("fallback-"))]);
      setCommentMessage("");
      setCommentStatus("Comentario publicado. Obrigado por contar sua experiencia.");
    } catch (error) {
      setCommentStatus(error instanceof Error ? error.message : "Nao foi possivel enviar seu comentario.");
    } finally {
      setIsPostingComment(false);
    }
  }

  async function handleRefreshJob(jobId: string) {
    try {
      const { job } = await getConversionJob(jobId);
      setConversionJobs((current) => current.map((item) => (item.id === job.id ? job : item)));
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("home.refreshConversionError"));
    }
  }

  async function handleCancelJob(jobId: string) {
    try {
      const { job } = await cancelConversionJob(jobId);
      setConversionJobs((current) => current.map((item) => (item.id === job.id ? job : item)));
      setStatus(t("home.conversionCancelled"));
      await refreshUsage();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("home.cancelConversionError"));
    }
  }

  async function handleDownloadJob(job: ConversionJob) {
    try {
      const filename = await downloadConversionJob(job);
      setStatus(`Download iniciado: ${filename}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("home.downloadConversionError"));
    }
  }

  function jobStatusLabel(job: ConversionJob) {
    if (job.status === "queued") {
      return job.queue_position ? t("home.statusQueuedPosition", { position: job.queue_position }) : t("common.queued");
    }
    if (job.status === "processing") {
      return t("common.processing");
    }
    if (job.status === "completed") {
      return t("common.completed");
    }
    if (job.status === "cancelled") {
      return "Cancelado";
    }
    return t("common.failed");
  }

  return (
    <div className={styles.page}>
      <main>
        {toolMode === "all" ? (
        <section className={styles.hero}>
          <div className={styles.heroGrid} aria-hidden="true" />
          <div className={styles.heroOrb} aria-hidden="true" />
          <div className={styles.heroInner}>
            <div className={styles.heroCopy}>
              <h1>
                {t("home.heroTitleBefore")} <span>{t("home.heroTitleHighlight")}</span>
              </h1>
              <p>{t("home.heroSubtitle")}</p>
              <div className={styles.heroBadges}>
                {heroBadgeKeys.map((badgeKey) => (
                  <span key={badgeKey}>{t(badgeKey)}</span>
                ))}
              </div>
            </div>
            <div className={styles.heroVisual} aria-hidden="true">
              <img
                src="/assets/polaryix-penguin.png"
                alt=""
                className={styles.penguin}
                onError={(event) => {
                  event.currentTarget.style.display = "none";
                }}
              />
              <div className={`${styles.floatingCard} ${isHeroFormatSwitching ? styles.switchingCard : ""}`}>
                <span>{heroFormatFrom}</span>
                <strong>&lt;&gt;</strong>
                <span>{heroFormatTo}</span>
              </div>
            </div>
          </div>
        </section>
        ) : null}

        <div className={styles.toolStack}>
          {toolMode === "all" || toolMode === "converter" ? (
          <section id="converter" className={styles.converterSection} aria-labelledby="converter-title">
            <div className={styles.sectionHeader}>
              <div>
                <p>{t("home.converterEyebrow")}</p>
                <h2 id="converter-title">{t("home.converterTitle")}</h2>
              </div>
              <span className={styles.tokenBadge}>{tokenLabel()}</span>
            </div>

            <div className={styles.converterPanel}>
              <div className={styles.formatRow}>
                <FormatPicker
                  label={t("home.convertFrom")}
                  value={fromFormat}
                  isOpen={openPicker === "from"}
                  onToggle={() => setOpenPicker(openPicker === "from" ? null : "from")}
                  onSelect={(format) => {
                    setFromFormat(format);
                    setOpenPicker(null);
                  }}
                  t={t}
                />
                <button type="button" className={styles.swapButton} onClick={swapFormats} aria-label={t("home.swapFormats")}>
                  ⇄
                </button>
                <FormatPicker
                  label={t("home.convertTo")}
                  value={toFormat}
                  isOpen={openPicker === "to"}
                  onToggle={() => setOpenPicker(openPicker === "to" ? null : "to")}
                  onSelect={(format) => {
                    setToFormat(format);
                    setOpenPicker(null);
                  }}
                  t={t}
                />
              </div>

              {selectedFiles.length === 0 ? (
                <button
                  type="button"
                  className={styles.dropzone}
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={(event) => {
                    event.preventDefault();
                  }}
                  onDrop={(event) => {
                    event.preventDefault();
                    setFiles(Array.from(event.dataTransfer.files ?? []));
                  }}
                >
                  <input ref={fileInputRef} type="file" onChange={handleFileChange} accept={acceptList} multiple />
                  <strong>{t("home.selectFile")}</strong>
                  <span>{t("home.dragFiles")}</span>
                  <small>{t("home.currentFlow", { conversion: conversionLabel, limit: batchLimit })}</small>
                </button>
              ) : (
                <div
                  className={styles.fileQueue}
                  onDragOver={(event) => {
                    event.preventDefault();
                  }}
                  onDrop={(event) => {
                    event.preventDefault();
                    setFiles([...selectedFiles, ...Array.from(event.dataTransfer.files ?? [])]);
                  }}
                >
                  <input ref={fileInputRef} type="file" onChange={handleFileChange} accept={acceptList} multiple />
                  <div className={styles.fileQueueList}>
                    {selectedFiles.map((file, index) => (
                      <article className={styles.fileQueueItem} key={`${file.name}-${file.size}-${index}`}>
                        <span className={styles.fileIcon}>IMG</span>
                        <strong>{file.name}</strong>
                        <span className={styles.fileTo}>{t("home.to")}</span>
                        <select value={toFormat} onChange={(event) => setToFormat(event.target.value)}>
                          {formatOptions.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                        <em>{t("home.ready")}</em>
                        <small>{formatFileSize(file.size)}</small>
                        <button type="button" onClick={() => removeSelectedFile(index)} aria-label={`Remover ${file.name}`}>
                          ×
                        </button>
                      </article>
                    ))}
                  </div>

                  <div className={styles.queueConvertAll}>
                    <span>{t("home.convertAllTo")}</span>
                    <select value={toFormat} onChange={(event) => setToFormat(event.target.value)}>
                      {formatOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className={styles.fileQueueActions}>
                    <button type="button" className={styles.addFilesButton} onClick={() => fileInputRef.current?.click()}>
                      {t("home.addMoreFiles")}
                    </button>
                    <p>
                      {t("home.filesCount", { count: selectedFiles.length, limit: batchLimit, size: formatFileSize(totalSelectedSize) })}
                    </p>
                    <button type="button" className={styles.queueConvertButton} onClick={handleConvert} disabled={isConverting}>
                      {isConverting ? t("home.converting") : t("home.convert")}
                      <span>→</span>
                    </button>
                  </div>
                </div>
              )}

              {selectedFiles.length === 0 ? (
                <div className={styles.actionRow}>
                  <button type="button" className={styles.convertButton} onClick={handleConvert} disabled={isConverting}>
                    {isConverting ? t("home.converting") : t("home.convertNow")}
                  </button>
                  <p className={styles.statusText}>
                    <StatusMessage message={status} t={t} />
                  </p>
                  {isTokenLimitMessage(status) ? (
                    <a className={styles.limitNotice} href="/premium">
                      {t("home.tokenLimitConvert")}
                    </a>
                  ) : null}
                </div>
              ) : (
                <>
                  <p className={styles.statusText}>
                    <StatusMessage message={status} t={t} />
                  </p>
                  {isTokenLimitMessage(status) ? (
                    <a className={styles.limitNotice} href="/premium">
                      {t("home.tokenLimitConvert")}
                    </a>
                  ) : null}
                </>
              )}

              {conversionJobs.length > 0 ? (
                <div className={styles.jobPanel} aria-label={t("home.jobQueue")}>
                  {conversionJobs.map((job) => (
                    <article className={styles.jobCard} key={job.id}>
                      <div>
                        <strong>{job.original_filename}</strong>
                        <span>
                          {job.input_format} {t("home.to")} {job.output_format}
                        </span>
                        {job.is_priority ? <em>{t("home.priorityQueue")}</em> : null}
                      </div>
                      <p className={styles.statusText}>
                        {jobStatusLabel(job)}
                        {job.status === "failed" && job.error_message ? `: ${job.error_message}` : ""}
                      </p>
                      <div className={styles.jobActions}>
                        <button type="button" onClick={() => handleRefreshJob(job.id)}>
                          {t("home.refreshStatus")}
                        </button>
                        {job.status === "queued" ? (
                          <button type="button" onClick={() => handleCancelJob(job.id)}>
                            {t("common.cancel")}
                          </button>
                        ) : null}
                        {job.status === "completed" ? (
                          <button type="button" onClick={() => handleDownloadJob(job)}>
                            {t("common.download")}
                          </button>
                        ) : null}
                      </div>
                    </article>
                  ))}
                </div>
              ) : null}
            </div>
          </section>
          ) : null}

          {toolMode === "all" || toolMode === "download" ? (
          <section id="download-link" className={styles.downloadSection} aria-labelledby="download-title">
            <div className={styles.downloadCopy}>
              <div>
                <p>{t("home.downloadLinkEyebrow")}</p>
                <h2 id="download-title">{t("home.downloadLinkTitle")}</h2>
                <span>{t("home.downloadLinkSubtitle")}</span>
              </div>
              <span className={styles.tokenBadge}>{tokenLabel()}</span>
            </div>

            <div className={styles.downloadTool}>
              <input
                type="url"
                value={downloadUrl}
                onChange={(event) => setDownloadUrl(event.target.value)}
                placeholder={t("home.urlPlaceholder")}
                aria-label={t("home.urlAria")}
              />
              <div className={styles.downloadModes} aria-label={t("home.downloadFormat")}>
                {downloadOptions.map((option) => (
                  <button
                    type="button"
                    key={option.id}
                    className={downloadFormat === option.id ? styles.activeMode : undefined}
                    onClick={() => {
                      setDownloadFormat(option.id);
                      if (option.premium && !isPremium) {
                        setDownloadStatus(t("home.premiumQualityOnly"));
                      }
                    }}
                    disabled={isDownloading}
                  >
                    <strong>{option.label}</strong>
                    <span>{option.detail}</span>
                  </button>
                ))}
              </div>
              <button type="button" onClick={handleLinkDownload} disabled={isDownloading}>
                {isDownloading ? t("home.preparing") : t("home.prepareDownload")}
              </button>
              <p className={styles.statusText}>
                <StatusMessage message={downloadStatus} t={t} />
              </p>
              {preparedLinkJob ? (
                <button type="button" className={styles.readyDownloadButton} onClick={handlePreparedLinkDownload} disabled={isDownloading}>
                  Baixar arquivo preparado
                </button>
              ) : null}
              {isTokenLimitMessage(downloadStatus) ? (
                <a className={styles.limitNotice} href="/premium">
                  {t("home.tokenLimitDownload")}
                </a>
              ) : null}
            </div>

            {(linkPreview || previewStatus) && (
              <div className={styles.previewCard}>
                {linkPreview?.thumbnail ? <img src={linkPreview.thumbnail} alt="" /> : <div className={styles.previewPlaceholder} />}
                <div>
                  <strong>{linkPreview?.title ?? t("home.previewTitle")}</strong>
                  {linkPreview?.uploader ? <span>{linkPreview.uploader}</span> : null}
                  {formatDuration(linkPreview?.duration) ? <small>{formatDuration(linkPreview?.duration)}</small> : null}
                  {previewStatus ? <p>{previewStatus}</p> : null}
                </div>
              </div>
            )}

            {(isDownloading || downloadProgress > 0) && (
              <div className={styles.progressWrap} aria-label={t("home.downloadProgress")}>
                <div>
                  <span>{downloadProgressLabel()}</span>
                  <strong>{downloadProgress}%</strong>
                </div>
                <progress value={downloadProgress} max={100} />
                {downloadProgressHint() ? <p>{downloadProgressHint()}</p> : null}
              </div>
            )}

            <div className={styles.downloadCards}>
              {downloadCards.map((card) => (
                <article key={card.name} className={styles[card.brand as "youtube" | "tiktok"]}>
                  <img src={card.icon} alt="" aria-hidden="true" />
                  <strong>{card.name}</strong>
                  <p>{t(card.textKey)}</p>
                </article>
              ))}
            </div>
          </section>
          ) : null}
        </div>

        {toolMode === "all" ? (
        <>
        <section className={styles.popularToolsSection} aria-label="Popular PolarYix tools">
          <div>
            <p>POPULAR TOOLS</p>
            <h2>File converters and media tools</h2>
            <span>Find PolarYix tools for DDS, PNG, YouTube, MP3, MP4 and online image processing.</span>
          </div>
          <div className={styles.popularToolsGrid}>
            <a href="/convert/dds-to-png">DDS to PNG Converter</a>
            <a href="/convert/png-to-dds">PNG to DDS Converter</a>
            <a href="/convert/webp-to-png">WEBP to PNG Converter</a>
            <a href="/convert/mp4-to-mp3">MP4 to MP3 Converter</a>
            <a href="/youtube-to-mp3">YouTube to MP3 Converter</a>
            <a href="/youtube-to-mp4">YouTube to MP4 Converter</a>
            <a href="/download/tiktok-to-mp4">TikTok to MP4 Downloader</a>
            <a href="/image/remove-background">Remove Background Online</a>
            <a href="/image/optimize">Image Optimizer</a>
            <a href="/image/upscale">Image Upscaler</a>
          </div>
        </section>

        <section className={styles.testimonialsSection} aria-label={t("home.testimonialsAria")}>
          <div className={styles.testimonialHeader}>
            <div>
              <p>{t("home.commentsEyebrow")}</p>
              <h2>{t("home.commentsTitle")}</h2>
            </div>
            <form className={styles.commentForm} onSubmit={handleCommentSubmit}>
              <textarea
                value={commentMessage}
                onChange={(event) => setCommentMessage(event.target.value)}
                placeholder={currentUser ? t("home.commentPlaceholderLogged") : t("home.commentPlaceholderGuest")}
                maxLength={500}
                disabled={!currentUser || isPostingComment}
              />
              <div>
                <span>{commentStatus || (currentUser ? t("home.commentingAs", { name: currentUser.name }) : t("home.commentLoginNeeded"))}</span>
                {currentUser ? (
                  <button type="submit" disabled={isPostingComment}>
                    {isPostingComment ? t("home.sending") : t("home.sendComment")}
                  </button>
                ) : (
                  <a href="/login">{t("home.loginToComment")}</a>
                )}
              </div>
            </form>
          </div>
          <div className={styles.marquee}>
            <div className={styles.marqueeTrack}>
              {[...comments, ...comments].map((comment, index) => (
                <article className={styles.commentCard} key={`${comment.id}-${index}`}>
                  <p>“{comment.message}”</p>
                  <span>{comment.user_name}</span>
                </article>
              ))}
            </div>
          </div>
        </section>
        </>
        ) : null}
      </main>

    </div>
  );
}
