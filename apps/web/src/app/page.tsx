"use client";

import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  LinkPreview,
  UsageInfo,
  convertFile,
  convertFiles,
  createLinkDownloadJob,
  downloadLinkJobFile,
  getLinkDownloadJob,
  getLinkPreview,
  getUsage,
} from "@/lib/api";
import { detectFormatFromFileName, validateConversion, validateFileForConversion } from "@/lib/conversionCompatibility";
import styles from "./page.module.css";

const formatGroups = [
  { title: "Imagens", formats: ["PNG", "DDS", "JPG", "JPEG", "WEBP", "TGA", "BMP", "TIFF", "AVIF", "SVG", "ICO"] },
  { title: "Vídeos", formats: ["MP4", "MOV", "AVI", "MKV", "WEBM", "M4V", "FLV", "WMV"] },
  { title: "Áudios", formats: ["MP3", "WAV", "AAC", "OGG", "FLAC", "M4A", "WMA"] },
  { title: "Documentos", formats: ["PDF", "DOCX", "DOC", "XLSX", "CSV", "PPTX", "TXT", "MD"] },
  { title: "Arquivos", formats: ["ZIP", "RAR", "7Z", "TAR", "GZ"] },
  { title: "Outros", formats: ["JSON", "XML", "HTML", "HEIC", "PSD"] },
];

const allFormats = formatGroups.flatMap((group) => group.formats);
const formatOptions = allFormats.map((format) => ({ value: format, label: format }));

const comments = [
  "Converti meus arquivos em segundos. Muito mais prático.",
  "Interface limpa, rápida e fácil de usar.",
  "O Polaryix economizou muito tempo no meu fluxo de trabalho.",
  "Finalmente um conversor simples e bonito.",
  "O fluxo PNG para DDS ficou direto e sem distrações.",
  "Uso para testar imagens de jogos e tudo ficou mais ágil.",
];

const downloadCards = [
  { name: "YouTube", text: "Vídeos e áudios em poucos cliques.", icon: "/assets/icons/youtube.svg", brand: "youtube" },
  { name: "TikTok", text: "Cole o link e escolha o formato.", icon: "/assets/icons/tiktok.svg", brand: "tiktok" },
];

const heroBadges = ["Rápido", "Seguro", "Sem limites"];
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
  { id: "mp4", label: "MP4", detail: "720p - 5 tokens", mediaType: "video", premium: false },
  { id: "mp3", label: "MP3", detail: "2 tokens", mediaType: "audio", premium: false },
  { id: "4k", label: "4K", detail: "5 tokens - Premium", mediaType: "video", premium: true },
] as const;

function FormatPicker({
  label,
  value,
  isOpen,
  onToggle,
  onSelect,
}: {
  label: string;
  value: string;
  isOpen: boolean;
  onToggle: () => void;
  onSelect: (value: string) => void;
}) {
  return (
    <div className={styles.formatPicker}>
      <span className={styles.pickerLabel}>{label}</span>
      <button type="button" className={styles.pickerButton} onClick={onToggle} aria-expanded={isOpen}>
        <strong>{value}</strong>
        <span>Escolher</span>
      </button>
      {isOpen ? (
        <div className={styles.formatMenu}>
          {formatGroups.map((group) => (
            <section key={group.title}>
              <h3>{group.title}</h3>
              <div>
                {group.formats.map((format) => (
                  <button
                    type="button"
                    key={`${group.title}-${format}`}
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

function StatusMessage({ message }: { message: string }) {
  const impossiblePrefix = "Essa conversão não é possível.";

  if (message.startsWith(impossiblePrefix)) {
    return (
      <>
        Essa conversão <strong className={styles.errorHighlight}>não é possível</strong>.
        {message.slice(impossiblePrefix.length)}
      </>
    );
  }

  if (message.startsWith("Essa conversão ainda não é suportada.")) {
    return (
      <>
        Essa conversão ainda <strong className={styles.errorHighlight}>não é suportada</strong>.
        {message.slice("Essa conversão ainda não é suportada.".length)}
      </>
    );
  }

  return message;
}

export default function HomePage() {
  const [fromFormat, setFromFormat] = useState("PNG");
  const [toFormat, setToFormat] = useState("DDS");
  const [openPicker, setOpenPicker] = useState<"from" | "to" | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [fileName, setFileName] = useState("");
  const [status, setStatus] = useState("Selecione um arquivo para preparar a conversão.");
  const [downloadUrl, setDownloadUrl] = useState("");
  const [downloadFormat, setDownloadFormat] = useState<(typeof downloadOptions)[number]["id"]>("mp4");
  const [downloadStatus, setDownloadStatus] = useState("Cole um link para preparar o download.");
  const [linkPreview, setLinkPreview] = useState<LinkPreview | null>(null);
  const [previewStatus, setPreviewStatus] = useState("");
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [isConverting, setIsConverting] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isPremium, setIsPremium] = useState(false);
  const [premiumPlan, setPremiumPlan] = useState("basic");
  const [usage, setUsage] = useState<UsageInfo | null>(null);
  const [usageError, setUsageError] = useState("");
  const [heroFormatIndex, setHeroFormatIndex] = useState(0);
  const [isHeroFormatSwitching, setIsHeroFormatSwitching] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const conversionLabel = useMemo(() => `${fromFormat} > ${toFormat}`, [fromFormat, toFormat]);
  const acceptList = useMemo(() => allFormats.map((format) => `.${format.toLowerCase()}`).join(","), []);
  const batchLimit = isPremium ? (premiumPlan === "pro" ? 600 : 30) : 2;
  const totalSelectedSize = useMemo(() => selectedFiles.reduce((sum, file) => sum + file.size, 0), [selectedFiles]);
  const [heroFormatFrom, heroFormatTo] = heroFormatPairs[heroFormatIndex];

  useEffect(() => {
    setIsPremium(window.localStorage.getItem("polaryix:isPremium") === "true");
    setPremiumPlan(window.localStorage.getItem("polaryix:premiumPlan") ?? "basic");
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

  async function refreshUsage() {
    try {
      const currentUsage = await getUsage({ isPremium, premiumPlan });
      setUsage(currentUsage);
      setUsageError("");
    } catch {
      setUsage(null);
      setUsageError("Não foi possível atualizar os créditos agora.");
    }
  }

  useEffect(() => {
    const normalizedUrl = downloadUrl.trim();

    setLinkPreview(null);
    setPreviewStatus("");

    if (!/^https?:\/\//i.test(normalizedUrl)) {
      return;
    }

    const timeout = window.setTimeout(async () => {
      setPreviewStatus("Carregando preview...");

      try {
        const preview = await getLinkPreview(normalizedUrl);
        setLinkPreview(preview);
        setPreviewStatus("");
      } catch (error) {
        setPreviewStatus(error instanceof Error ? error.message : "Não foi possível carregar o preview.");
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
      setStatus(invalidFileMessage || `${limitedFiles.length} arquivos prontos para converter em ${toFormat}. O download virá em ZIP.${detectedSuffix}`);
      return;
    }

    const invalidFileMessage = limitedFiles[0] ? validateFileForConversion(limitedFiles[0], nextFromFormat) : "";
    const detectedSuffix = detectedFormat ? ` Formato detectado: ${detectedFormat}.` : "";
    setStatus(
      invalidFileMessage ||
      (limitedFiles[0]
        ? `${limitedFiles[0].name} pronto para converter em ${toFormat}.${detectedSuffix}`
        : "Selecione um arquivo para preparar a conversão.")
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
      return `${usage.remaining} créditos restantes`;
    }

    return usageError ? "30 créditos grátis/dia" : "30 créditos grátis/dia";
  }

  function downloadProgressLabel() {
    if (downloadProgress >= 92 && isDownloading) {
      return "Finalizando arquivo";
    }

    if (downloadProgress >= 55 && isDownloading) {
      return "Preparando mídia";
    }

    return "Progresso";
  }

  function downloadProgressHint() {
    if (downloadProgress >= 92 && isDownloading) {
      return "Para vídeos longos, essa etapa pode levar alguns minutos enquanto o arquivo final é preparado.";
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
      setStatus("Escolha um arquivo antes de iniciar a conversão.");
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
    setStatus(selectedFiles.length > 1 ? `Convertendo ${selectedFiles.length} arquivos (${conversionLabel})...` : `Convertendo ${conversionLabel}...`);

    try {
      const result =
        selectedFiles.length > 1
          ? await convertFiles({
            files: selectedFiles,
            fromFormat,
            toFormat,
            isPremium,
            premiumPlan,
          })
          : await convertFile({
              file: selectedFile as File,
              fromFormat,
              toFormat,
              isPremium,
              premiumPlan,
            });

      setStatus(`Conversão concluída. Download iniciado: ${result.filename}`);
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
      setDownloadStatus("Cole uma URL antes de preparar o download.");
      return;
    }

    setIsDownloading(true);
    setDownloadProgress(0);
    const selectedOption = downloadOptions.find((option) => option.id === downloadFormat) ?? downloadOptions[0];

    if (selectedOption.premium && !isPremium) {
      setDownloadStatus("Essa qualidade é exclusiva do Premium. Escolha MP4 ou MP3.");
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
        setDownloadStatus(job.message || "Processando download...");
      }

      if (job.status === "error") {
        throw new Error(job.message || "Não foi possível concluir o download.");
      }

      const filename = await downloadLinkJobFile(job);
      setDownloadProgress(100);
      setDownloadStatus(`Download iniciado: ${filename}`);
      await refreshUsage();
    } catch (error) {
      setDownloadProgress(0);
      setDownloadStatus(error instanceof Error ? error.message : "Erro ao baixar o link.");
      await refreshUsage();
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <div className={styles.page}>
      <main>
        <section className={styles.hero}>
          <div className={styles.heroGrid} aria-hidden="true" />
          <div className={styles.heroOrb} aria-hidden="true" />
          <div className={styles.heroInner}>
            <div className={styles.heroCopy}>
              <h1>
                Conversões rápidas, visuais e sem <span>complicação</span>
              </h1>
              <p>Converta arquivos com controle, velocidade e praticidade.</p>
              <div className={styles.heroBadges}>
                {heroBadges.map((badge) => (
                  <span key={badge}>{badge}</span>
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

        <div className={styles.toolStack}>
          <section id="converter" className={styles.converterSection} aria-labelledby="converter-title">
            <div className={styles.sectionHeader}>
              <div>
                <p>Converter imagem</p>
                <h2 id="converter-title">Escolha os formatos e envie seu arquivo</h2>
              </div>
              <span className={styles.tokenBadge}>{tokenLabel()}</span>
            </div>

            <div className={styles.converterPanel}>
              <div className={styles.formatRow}>
                <FormatPicker
                  label="Converter de"
                  value={fromFormat}
                  isOpen={openPicker === "from"}
                  onToggle={() => setOpenPicker(openPicker === "from" ? null : "from")}
                  onSelect={(format) => {
                    setFromFormat(format);
                    setOpenPicker(null);
                  }}
                />
                <button type="button" className={styles.swapButton} onClick={swapFormats} aria-label="Inverter formatos">
                  ⇄
                </button>
                <FormatPicker
                  label="Converter para"
                  value={toFormat}
                  isOpen={openPicker === "to"}
                  onToggle={() => setOpenPicker(openPicker === "to" ? null : "to")}
                  onSelect={(format) => {
                    setToFormat(format);
                    setOpenPicker(null);
                  }}
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
                  <strong>Selecionar arquivo</strong>
                  <span>Arraste ou escolha arquivos para converter</span>
                  <small>Fluxo atual: {conversionLabel} · limite por lote: {batchLimit}</small>
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
                        <span className={styles.fileTo}>para</span>
                        <select value={toFormat} onChange={(event) => setToFormat(event.target.value)}>
                          {formatOptions.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                        <em>Pronto</em>
                        <small>{formatFileSize(file.size)}</small>
                        <button type="button" onClick={() => removeSelectedFile(index)} aria-label={`Remover ${file.name}`}>
                          ×
                        </button>
                      </article>
                    ))}
                  </div>

                  <div className={styles.queueConvertAll}>
                    <span>Converta todos para</span>
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
                      + Adicionar mais arquivos
                    </button>
                    <p>
                      {selectedFiles.length}/{batchLimit} arquivos · {formatFileSize(totalSelectedSize)}
                    </p>
                    <button type="button" className={styles.queueConvertButton} onClick={handleConvert} disabled={isConverting}>
                      {isConverting ? "Convertendo..." : "Converter"}
                      <span>→</span>
                    </button>
                  </div>
                </div>
              )}

              {selectedFiles.length === 0 ? (
                <div className={styles.actionRow}>
                  <button type="button" className={styles.convertButton} onClick={handleConvert} disabled={isConverting}>
                    {isConverting ? "Convertendo..." : "Converter agora"}
                  </button>
                  <p className={styles.statusText}>
                    <StatusMessage message={status} />
                  </p>
                  {isTokenLimitMessage(status) ? (
                    <a className={styles.limitNotice} href="/premium">
                      Seus tokens acabaram. Conheça o Premium para continuar convertendo.
                    </a>
                  ) : null}
                </div>
              ) : (
                <>
                  <p className={styles.statusText}>
                    <StatusMessage message={status} />
                  </p>
                  {isTokenLimitMessage(status) ? (
                    <a className={styles.limitNotice} href="/premium">
                      Seus tokens acabaram. Conheça o Premium para continuar convertendo.
                    </a>
                  ) : null}
                </>
              )}
            </div>
          </section>

          <section id="download-link" className={styles.downloadSection} aria-labelledby="download-title">
            <div className={styles.downloadCopy}>
              <div>
                <p>Download por link</p>
                <h2 id="download-title">Baixe vídeos e áudios por link</h2>
                <span>Cole um link do YouTube ou TikTok para baixar vídeo ou áudio rapidamente.</span>
              </div>
              <span className={styles.tokenBadge}>{tokenLabel()}</span>
            </div>

            <div className={styles.downloadTool}>
              <input
                type="url"
                value={downloadUrl}
                onChange={(event) => setDownloadUrl(event.target.value)}
                placeholder="Cole a URL aqui"
                aria-label="URL para baixar vídeo ou áudio"
              />
              <div className={styles.downloadModes} aria-label="Formato do download">
                {downloadOptions.map((option) => (
                  <button
                    type="button"
                    key={option.id}
                    className={downloadFormat === option.id ? styles.activeMode : undefined}
                    onClick={() => {
                      setDownloadFormat(option.id);
                      if (option.premium && !isPremium) {
                        setDownloadStatus("Essa qualidade é exclusiva do Premium. Escolha MP4 ou MP3.");
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
                {isDownloading ? "Preparando..." : "Preparar download"}
              </button>
              <p className={styles.statusText}>
                <StatusMessage message={downloadStatus} />
              </p>
              {isTokenLimitMessage(downloadStatus) ? (
                <a className={styles.limitNotice} href="/premium">
                  Seus tokens acabaram. Conheça o Premium para continuar baixando.
                </a>
              ) : null}
            </div>

            {(linkPreview || previewStatus) && (
              <div className={styles.previewCard}>
                {linkPreview?.thumbnail ? <img src={linkPreview.thumbnail} alt="" /> : <div className={styles.previewPlaceholder} />}
                <div>
                  <strong>{linkPreview?.title ?? "Preview do link"}</strong>
                  {linkPreview?.uploader ? <span>{linkPreview.uploader}</span> : null}
                  {formatDuration(linkPreview?.duration) ? <small>{formatDuration(linkPreview?.duration)}</small> : null}
                  {previewStatus ? <p>{previewStatus}</p> : null}
                </div>
              </div>
            )}

            {(isDownloading || downloadProgress > 0) && (
              <div className={styles.progressWrap} aria-label="Progresso do download">
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
                  <p>{card.text}</p>
                </article>
              ))}
            </div>
          </section>
        </div>

        <section className={styles.testimonialsSection} aria-label="Comentários de usuários">
          <div className={styles.testimonialHeader}>
            <p>Comentários</p>
            <h2>Quem converte com o Polaryix volta pela praticidade</h2>
          </div>
          <div className={styles.marquee}>
            <div className={styles.marqueeTrack}>
              {[...comments, ...comments].map((comment, index) => (
                <article className={styles.commentCard} key={`${comment}-${index}`}>
                  <p>“{comment}”</p>
                  <span>Usuário Polaryix</span>
                </article>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className={styles.footer}>
        <p>© 2026 Polaryix. Todos os direitos reservados.</p>
      </footer>
    </div>
  );
}
