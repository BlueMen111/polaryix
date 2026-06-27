"use client";

import { ChangeEvent, useMemo, useRef, useState } from "react";
import { Header } from "@/components/Header";
import { convertFile, downloadFromLink } from "@/lib/api";
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
  { name: "Instagram", text: "Reels e mídia para baixar rápido.", icon: "/assets/icons/instagram.svg", brand: "instagram" },
];

const heroBadges = ["Rápido", "Seguro", "Sem limites"];

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

export default function HomePage() {
  const [fromFormat, setFromFormat] = useState("PNG");
  const [toFormat, setToFormat] = useState("DDS");
  const [openPicker, setOpenPicker] = useState<"from" | "to" | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState("");
  const [status, setStatus] = useState("Selecione um arquivo para preparar a conversão.");
  const [downloadUrl, setDownloadUrl] = useState("");
  const [downloadMode, setDownloadMode] = useState<"video" | "audio">("video");
  const [downloadStatus, setDownloadStatus] = useState("Cole um link para preparar o download.");
  const [isConverting, setIsConverting] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const conversionLabel = useMemo(() => `${fromFormat} > ${toFormat}`, [fromFormat, toFormat]);
  const acceptList = useMemo(() => allFormats.map((format) => `.${format.toLowerCase()}`).join(","), []);

  function swapFormats() {
    setFromFormat(toFormat);
    setToFormat(fromFormat);
    setOpenPicker(null);
  }

  function setFile(file: File | null) {
    setSelectedFile(file);
    setFileName(file?.name ?? "");
    setStatus(file ? `${file.name} pronto para converter em ${toFormat}.` : "Selecione um arquivo para preparar a conversão.");
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
  }

  async function handleConvert() {
    if (!selectedFile) {
      setStatus("Escolha um arquivo antes de iniciar a conversão.");
      fileInputRef.current?.click();
      return;
    }

    setIsConverting(true);
    setStatus(`Convertendo ${conversionLabel}...`);

    try {
      const result = await convertFile({
        file: selectedFile,
        fromFormat,
        toFormat,
      });

      setStatus(`Conversão concluída. Download iniciado: ${result.filename}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Erro ao converter arquivo.");
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
    setDownloadStatus(`Preparando download de ${downloadMode === "video" ? "vídeo" : "áudio"}...`);

    try {
      const result = await downloadFromLink({
        url: downloadUrl,
        mediaType: downloadMode,
      });

      setDownloadStatus(`Download iniciado: ${result.filename}`);
    } catch (error) {
      setDownloadStatus(error instanceof Error ? error.message : "Erro ao baixar o link.");
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <div className={styles.page}>
      <Header />

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
              <div className={styles.floatingCard}>
                <span>PNG</span>
                <strong>para</strong>
                <span>DDS</span>
              </div>
            </div>
          </div>
        </section>

        <div className={styles.toolGrid}>
          <section id="converter" className={styles.converterSection} aria-labelledby="converter-title">
            <div className={styles.sectionHeader}>
              <p>Converter imagem</p>
              <h2 id="converter-title">Escolha os formatos e envie seu arquivo</h2>
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

              <button
                type="button"
                className={styles.dropzone}
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(event) => {
                  event.preventDefault();
                }}
                onDrop={(event) => {
                  event.preventDefault();
                  setFile(event.dataTransfer.files?.[0] ?? null);
                }}
              >
                <input ref={fileInputRef} type="file" onChange={handleFileChange} accept={acceptList} />
                <strong>Selecionar arquivo</strong>
                <span>{fileName || "Arraste ou escolha uma imagem para converter"}</span>
                <small>Fluxo atual: {conversionLabel}</small>
              </button>

              <div className={styles.actionRow}>
                <button type="button" className={styles.convertButton} onClick={handleConvert} disabled={isConverting}>
                  {isConverting ? "Convertendo..." : "Converter agora"}
                </button>
                <p className={styles.statusText}>{status}</p>
              </div>
            </div>
          </section>

          <section id="download-link" className={styles.downloadSection} aria-labelledby="download-title">
            <div className={styles.downloadCopy}>
              <p>Download por link</p>
              <h2 id="download-title">Baixe vídeos e áudios por link</h2>
              <span>Cole um link do YouTube, TikTok ou Instagram para baixar vídeo ou áudio rapidamente.</span>
            </div>

            <div className={styles.downloadTool}>
              <input
                type="url"
                value={downloadUrl}
                onChange={(event) => setDownloadUrl(event.target.value)}
                placeholder="Cole a URL aqui"
                aria-label="URL para baixar vídeo ou áudio"
              />
              <div className={styles.downloadModes} aria-label="Tipo de download">
                <button
                  type="button"
                  className={downloadMode === "video" ? styles.activeMode : undefined}
                  onClick={() => setDownloadMode("video")}
                >
                  Vídeo
                </button>
                <button
                  type="button"
                  className={downloadMode === "audio" ? styles.activeMode : undefined}
                  onClick={() => setDownloadMode("audio")}
                >
                  Áudio
                </button>
              </div>
              <button type="button" onClick={handleLinkDownload} disabled={isDownloading}>
                {isDownloading ? "Preparando..." : "Preparar download"}
              </button>
              <p className={styles.statusText}>{downloadStatus}</p>
            </div>

            <div className={styles.downloadCards}>
              {downloadCards.map((card) => (
                <article key={card.name} className={styles[card.brand as "youtube" | "tiktok" | "instagram"]}>
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
