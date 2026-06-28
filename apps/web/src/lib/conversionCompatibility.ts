const registeredFormats = new Set([
  "PNG",
  "DDS",
  "JPG",
  "JPEG",
  "WEBP",
  "TGA",
  "BMP",
  "TIFF",
  "AVIF",
  "SVG",
  "ICO",
  "HEIC",
  "PSD",
  "MP4",
  "MOV",
  "AVI",
  "MKV",
  "WEBM",
  "M4V",
  "FLV",
  "WMV",
  "MP3",
  "WAV",
  "AAC",
  "OGG",
  "FLAC",
  "M4A",
  "WMA",
  "PDF",
  "DOCX",
  "DOC",
  "XLSX",
  "CSV",
  "PPTX",
  "TXT",
  "MD",
  "ZIP",
  "RAR",
  "7Z",
  "TAR",
  "GZ",
  "JSON",
  "XML",
  "HTML",
]);

const imageFormats = new Set(["PNG", "DDS", "JPG", "JPEG", "WEBP", "TGA", "BMP", "TIFF", "AVIF", "ICO"]);
const videoFormats = new Set(["MP4", "MOV", "AVI", "MKV", "WEBM", "M4V", "FLV", "WMV"]);
const audioFormats = new Set(["MP3", "WAV", "AAC", "OGG", "FLAC", "M4A", "WMA"]);
const tabularFormats = new Set(["CSV", "JSON", "XML", "HTML", "XLSX"]);
const textFormats = new Set(["TXT", "MD"]);
const implementedFormats = new Set([...imageFormats, ...videoFormats, ...audioFormats, ...tabularFormats, ...textFormats, "ZIP"]);

const extensionMap: Record<string, string[]> = {
  JPEG: [".jpg", ".jpeg"],
  JPG: [".jpg", ".jpeg"],
  TIFF: [".tif", ".tiff"],
  HTML: [".html", ".htm"],
  MD: [".md", ".markdown"],
  "7Z": [".7z"],
};

export type ConversionValidation = {
  allowed: boolean;
  message: string;
  sourceFormat: string;
  targetFormat: string;
  status: "allowed" | "blocked" | "unsupported";
};

export const MAX_UPLOAD_SIZE_MB = 100;

export function normalizeFormat(value: string) {
  return value.trim().toUpperCase().replace(/^\./, "");
}

export function extensionsForFormat(format: string) {
  const normalized = normalizeFormat(format);
  return extensionMap[normalized] ?? [`.${normalized.toLowerCase()}`];
}

export function detectFormatFromFileName(fileName: string) {
  const lowerName = fileName.toLowerCase();
  const formats = Array.from(registeredFormats).sort((a, b) => b.length - a.length);

  for (const format of formats) {
    if (extensionsForFormat(format).some((extension) => lowerName.endsWith(extension))) {
      if (format === "JPEG") {
        return "JPG";
      }

      return format;
    }
  }

  return "";
}

function impossibleMessage(sourceFormat: string, targetFormat: string) {
  return `Essa conversão não é possível. O formato ${sourceFormat} não pode ser convertido diretamente para ${targetFormat}. Escolha uma combinação compatível.`;
}

function unsupportedMessage(format: string) {
  return `Essa conversão ainda não é suportada. O formato ${format} aparece nas opções, mas ainda não possui processamento disponível.`;
}

export function validateConversion(sourceFormat: string, targetFormat: string): ConversionValidation {
  const source = normalizeFormat(sourceFormat);
  const target = normalizeFormat(targetFormat);

  if (!source) {
    return { allowed: false, message: "Escolha o formato de entrada antes de converter.", sourceFormat: source, targetFormat: target, status: "blocked" };
  }

  if (!target) {
    return { allowed: false, message: "Escolha o formato de saída antes de converter.", sourceFormat: source, targetFormat: target, status: "blocked" };
  }

  if (!registeredFormats.has(source)) {
    return { allowed: false, message: `Formato de entrada não suportado: ${sourceFormat}`, sourceFormat: source, targetFormat: target, status: "blocked" };
  }

  if (!registeredFormats.has(target)) {
    return { allowed: false, message: `Formato de saída não suportado: ${targetFormat}`, sourceFormat: source, targetFormat: target, status: "blocked" };
  }

  if (!implementedFormats.has(source)) {
    return { allowed: false, message: unsupportedMessage(source), sourceFormat: source, targetFormat: target, status: "unsupported" };
  }

  if (!implementedFormats.has(target)) {
    return { allowed: false, message: unsupportedMessage(target), sourceFormat: source, targetFormat: target, status: "unsupported" };
  }

  if (target === "ZIP") {
    return { allowed: true, message: "Conversão permitida.", sourceFormat: source, targetFormat: target, status: "allowed" };
  }

  if (imageFormats.has(source) && imageFormats.has(target)) {
    return { allowed: true, message: "Conversão permitida.", sourceFormat: source, targetFormat: target, status: "allowed" };
  }

  if (videoFormats.has(source) && (videoFormats.has(target) || audioFormats.has(target))) {
    return { allowed: true, message: "Conversão permitida.", sourceFormat: source, targetFormat: target, status: "allowed" };
  }

  if (audioFormats.has(source) && audioFormats.has(target)) {
    return { allowed: true, message: "Conversão permitida.", sourceFormat: source, targetFormat: target, status: "allowed" };
  }

  if (tabularFormats.has(source) && tabularFormats.has(target)) {
    return { allowed: true, message: "Conversão permitida.", sourceFormat: source, targetFormat: target, status: "allowed" };
  }

  if (textFormats.has(source) && textFormats.has(target)) {
    return { allowed: true, message: "Conversão permitida.", sourceFormat: source, targetFormat: target, status: "allowed" };
  }

  return { allowed: false, message: impossibleMessage(source, target), sourceFormat: source, targetFormat: target, status: "blocked" };
}

export function validateFileForConversion(file: File, sourceFormat: string) {
  if (file.size <= 0) {
    return "O arquivo enviado está vazio. Escolha outro arquivo para converter.";
  }

  if (file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
    return `Arquivo excede o limite de ${MAX_UPLOAD_SIZE_MB} MB.`;
  }

  const lowerName = file.name.toLowerCase();
  const allowedExtensions = extensionsForFormat(sourceFormat);
  const hasExpectedExtension = allowedExtensions.some((extension) => lowerName.endsWith(extension));

  if (!hasExpectedExtension) {
    return `A extensão do arquivo não corresponde ao formato selecionado. Para ${normalizeFormat(sourceFormat)}, use: ${allowedExtensions.join(", ")}.`;
  }

  return "";
}
