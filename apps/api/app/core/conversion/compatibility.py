from __future__ import annotations

from dataclasses import dataclass


IMAGE_FORMATS = {"PNG", "DDS", "JPG", "JPEG", "WEBP", "TGA", "BMP", "TIFF", "AVIF", "SVG", "ICO", "HEIC", "PSD"}
VIDEO_FORMATS = {"MP4", "MOV", "AVI", "MKV", "WEBM", "M4V", "FLV", "WMV"}
AUDIO_FORMATS = {"MP3", "WAV", "AAC", "OGG", "FLAC", "M4A", "WMA"}
DOCUMENT_FORMATS = {"PDF", "DOCX", "DOC", "XLSX", "CSV", "PPTX", "TXT", "MD"}
ARCHIVE_FORMATS = {"ZIP", "RAR", "7Z", "TAR", "GZ"}
OTHER_FORMATS = {"JSON", "XML", "HTML"}

REGISTERED_FORMATS = IMAGE_FORMATS | VIDEO_FORMATS | AUDIO_FORMATS | DOCUMENT_FORMATS | ARCHIVE_FORMATS | OTHER_FORMATS

CONVERTIBLE_IMAGE_FORMATS = {"PNG", "DDS", "JPG", "JPEG", "WEBP", "TGA", "BMP", "TIFF", "AVIF", "ICO"}
CONVERTIBLE_VIDEO_FORMATS = VIDEO_FORMATS
CONVERTIBLE_AUDIO_FORMATS = AUDIO_FORMATS
CONVERTIBLE_TABULAR_FORMATS = {"CSV", "JSON", "XML", "HTML", "XLSX"}
CONVERTIBLE_TEXT_FORMATS = {"TXT", "MD"}
CONVERTIBLE_ARCHIVE_FORMATS = {"ZIP"}

IMPLEMENTED_INPUT_FORMATS = (
    CONVERTIBLE_IMAGE_FORMATS
    | CONVERTIBLE_VIDEO_FORMATS
    | CONVERTIBLE_AUDIO_FORMATS
    | CONVERTIBLE_TABULAR_FORMATS
    | CONVERTIBLE_TEXT_FORMATS
    | CONVERTIBLE_ARCHIVE_FORMATS
)
IMPLEMENTED_OUTPUT_FORMATS = (
    CONVERTIBLE_IMAGE_FORMATS
    | CONVERTIBLE_VIDEO_FORMATS
    | CONVERTIBLE_AUDIO_FORMATS
    | CONVERTIBLE_TABULAR_FORMATS
    | CONVERTIBLE_TEXT_FORMATS
    | CONVERTIBLE_ARCHIVE_FORMATS
)

FORMAT_EXTENSIONS = {
    "JPEG": {".jpg", ".jpeg"},
    "JPG": {".jpg", ".jpeg"},
    "TIFF": {".tif", ".tiff"},
    "HTML": {".html", ".htm"},
    "JSON": {".json"},
    "XML": {".xml"},
    "XLSX": {".xlsx"},
    "CSV": {".csv"},
    "TXT": {".txt"},
    "MD": {".md", ".markdown"},
    "7Z": {".7z"},
}


@dataclass(frozen=True)
class ConversionValidation:
    allowed: bool
    message: str
    source_format: str
    target_format: str
    status: str

    def as_dict(self) -> dict[str, str | bool]:
        return {
            "allowed": self.allowed,
            "message": self.message,
            "sourceFormat": self.source_format,
            "targetFormat": self.target_format,
            "status": self.status,
        }


def normalize_format(value: str) -> str:
    return value.strip().upper().lstrip(".")


def registered_extensions_for_format(format_value: str) -> set[str]:
    normalized = normalize_format(format_value)
    return FORMAT_EXTENSIONS.get(normalized, {f".{normalized.lower()}"})


def _impossible_message(source_format: str, target_format: str) -> str:
    return (
        f"Essa conversão não é possível. O formato {source_format} não pode ser convertido diretamente para "
        f"{target_format}. Escolha uma combinação compatível."
    )


def _unsupported_message(format_value: str) -> str:
    return (
        f"Essa conversão ainda não é suportada. O formato {format_value} aparece nas opções, "
        "mas ainda não possui processamento disponível."
    )


def validate_conversion(source_format: str, target_format: str) -> ConversionValidation:
    source = normalize_format(source_format)
    target = normalize_format(target_format)

    if not source:
        return ConversionValidation(False, "Escolha o formato de entrada antes de converter.", source, target, "blocked")

    if not target:
        return ConversionValidation(False, "Escolha o formato de saída antes de converter.", source, target, "blocked")

    if source not in REGISTERED_FORMATS:
        return ConversionValidation(False, f"Formato de entrada não suportado: {source_format}", source, target, "blocked")

    if target not in REGISTERED_FORMATS:
        return ConversionValidation(False, f"Formato de saída não suportado: {target_format}", source, target, "blocked")

    if source not in IMPLEMENTED_INPUT_FORMATS:
        return ConversionValidation(False, _unsupported_message(source), source, target, "unsupported")

    if target not in IMPLEMENTED_OUTPUT_FORMATS:
        return ConversionValidation(False, _unsupported_message(target), source, target, "unsupported")

    if target == "ZIP":
        return ConversionValidation(True, "Conversão permitida.", source, target, "allowed")

    if source in CONVERTIBLE_IMAGE_FORMATS and target in CONVERTIBLE_IMAGE_FORMATS:
        return ConversionValidation(True, "Conversão permitida.", source, target, "allowed")

    if source in CONVERTIBLE_VIDEO_FORMATS and target in (CONVERTIBLE_VIDEO_FORMATS | CONVERTIBLE_AUDIO_FORMATS):
        return ConversionValidation(True, "Conversão permitida.", source, target, "allowed")

    if source in CONVERTIBLE_AUDIO_FORMATS and target in CONVERTIBLE_AUDIO_FORMATS:
        return ConversionValidation(True, "Conversão permitida.", source, target, "allowed")

    if source in CONVERTIBLE_TABULAR_FORMATS and target in CONVERTIBLE_TABULAR_FORMATS:
        return ConversionValidation(True, "Conversão permitida.", source, target, "allowed")

    if source in CONVERTIBLE_TEXT_FORMATS and target in CONVERTIBLE_TEXT_FORMATS:
        return ConversionValidation(True, "Conversão permitida.", source, target, "allowed")

    return ConversionValidation(False, _impossible_message(source, target), source, target, "blocked")


def build_compatibility_matrix() -> dict[str, dict[str, dict[str, str | bool]]]:
    return {
        source: {target: validate_conversion(source, target).as_dict() for target in sorted(REGISTERED_FORMATS)}
        for source in sorted(REGISTERED_FORMATS)
    }
