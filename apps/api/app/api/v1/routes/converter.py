from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

try:
    import yt_dlp
except Exception:  # pragma: no cover - optional runtime dependency guard
    yt_dlp = None

from app.core.config.settings import settings
from app.core.security.file_security import FileSecurityError, validate_file_name, validate_upload_size


router = APIRouter(prefix="/converter", tags=["Converter"])

IMAGE_FORMATS = {
    "PNG": {"ext": ".png", "pil": "PNG"},
    "DDS": {"ext": ".dds", "pil": "DDS"},
    "JPG": {"ext": ".jpg", "pil": "JPEG"},
    "JPEG": {"ext": ".jpg", "pil": "JPEG"},
    "WEBP": {"ext": ".webp", "pil": "WEBP"},
    "TGA": {"ext": ".tga", "pil": "TGA"},
    "BMP": {"ext": ".bmp", "pil": "BMP"},
    "TIFF": {"ext": ".tiff", "pil": "TIFF"},
    "AVIF": {"ext": ".avif", "pil": "AVIF"},
    "ICO": {"ext": ".ico", "pil": "ICO"},
}

VIDEO_FORMATS = {"MP4", "MOV", "AVI", "MKV", "WEBM", "M4V", "FLV", "WMV"}
AUDIO_FORMATS = {"MP3", "WAV", "AAC", "OGG", "FLAC", "M4A", "WMA"}
TEXT_FORMATS = {"TXT", "MD", "CSV", "JSON", "XML", "HTML"}
ARCHIVE_FORMATS = {"ZIP"}

SUPPORTED_FORMATS = IMAGE_FORMATS.keys() | VIDEO_FORMATS | AUDIO_FORMATS | TEXT_FORMATS | ARCHIVE_FORMATS
SAFE_URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


def _normalize_format(value: str) -> str:
    normalized = value.strip().upper().lstrip(".")

    if normalized not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato não suportado: {value}",
        )

    return normalized


def _output_filename(input_name: str, target_format: str) -> str:
    stem = Path(input_name).stem or "polaryix-convertido"

    if target_format in IMAGE_FORMATS:
        extension = IMAGE_FORMATS[target_format]["ext"]
    else:
        extension = f".{target_format.lower()}"

    return f"{stem}-polaryix{extension}"


def _ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Conversão de vídeo/áudio requer FFmpeg instalado no ambiente.",
        )


def _convert_image(input_path: Path, output_path: Path, target_format: str) -> None:
    pil_format = IMAGE_FORMATS[target_format]["pil"]

    try:
        with Image.open(input_path) as image:
            if pil_format in {"JPEG", "BMP"} and image.mode in {"RGBA", "LA", "P"}:
                image = image.convert("RGBA")
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.getchannel("A"))
                image = background
            elif pil_format == "DDS" and image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA")
            elif image.mode == "P":
                image = image.convert("RGBA")

            save_kwargs = {"format": pil_format}
            if pil_format == "JPEG":
                save_kwargs.update({"quality": 92, "optimize": True})
            if pil_format == "WEBP":
                save_kwargs.update({"quality": 92})

            image.save(output_path, **save_kwargs)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"O Pillow instalado não suporta salvar {target_format}.",
        ) from exc
    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Não foi possível ler a imagem enviada.",
        ) from exc


def _convert_media(input_path: Path, output_path: Path, target_format: str) -> None:
    _ensure_ffmpeg_available()

    command = ["ffmpeg", "-y", "-i", str(input_path)]

    if target_format in AUDIO_FORMATS:
        command.extend(["-vn"])

    command.append(str(output_path))

    result = subprocess.run(command, capture_output=True, text=True, timeout=180)

    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "Erro ao converter mídia."
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


def _convert_text(input_path: Path, output_path: Path) -> None:
    data = input_path.read_bytes()
    output_path.write_bytes(data)


def _convert_to_zip(input_path: Path, output_path: Path, original_name: str) -> None:
    import zipfile

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(input_path, arcname=Path(original_name).name)


async def _save_upload(file: UploadFile, destination: Path) -> str:
    safe_name = validate_file_name(file.filename or "arquivo")
    await validate_upload_size(file)

    with destination.open("wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            buffer.write(chunk)

    await file.seek(0)
    return safe_name


@router.post("/convert-file")
async def convert_file(
    file: UploadFile = File(...),
    from_format: str = Form(...),
    to_format: str = Form(...),
) -> FileResponse:
    """Converte arquivos enviados e devolve o resultado como download."""

    source_format = _normalize_format(from_format)
    target_format = _normalize_format(to_format)

    try:
        with tempfile.TemporaryDirectory(prefix="polaryix-convert-") as temp_dir:
            workdir = Path(temp_dir)
            input_path = workdir / f"input-{uuid4().hex}.{source_format.lower()}"
            safe_name = await _save_upload(file, input_path)
            output_name = _output_filename(safe_name, target_format)
            output_path = workdir / output_name

            if source_format in IMAGE_FORMATS and target_format in IMAGE_FORMATS:
                _convert_image(input_path, output_path, target_format)
            elif target_format == "ZIP":
                _convert_to_zip(input_path, output_path, safe_name)
            elif source_format in TEXT_FORMATS and target_format in TEXT_FORMATS:
                _convert_text(input_path, output_path)
            elif source_format in VIDEO_FORMATS | AUDIO_FORMATS and target_format in VIDEO_FORMATS | AUDIO_FORMATS:
                _convert_media(input_path, output_path, target_format)
            else:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Conversão {source_format} para {target_format} ainda não é suportada.",
                )

            if not output_path.exists() or output_path.stat().st_size == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="A conversão não gerou um arquivo válido.",
                )

            final_path = settings.processed_path / "conversions" / f"{uuid4().hex}-{output_name}"
            final_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(output_path, final_path)

    except FileSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return FileResponse(
        final_path,
        media_type="application/octet-stream",
        filename=output_name,
    )


@router.post("/download-link")
async def download_link(
    url: str = Form(...),
    media_type: str = Form("video"),
) -> FileResponse:
    """Baixa vídeo ou áudio a partir de uma URL suportada pelo yt-dlp."""

    if yt_dlp is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Download por link requer yt-dlp instalado no ambiente.",
        )

    normalized_url = url.strip()
    if not SAFE_URL_PATTERN.match(normalized_url):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe uma URL http ou https válida.")

    requested_media = media_type.strip().lower()
    if requested_media not in {"video", "audio"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="media_type deve ser video ou audio.")

    output_dir = settings.processed_path / "link_downloads"
    output_dir.mkdir(parents=True, exist_ok=True)
    download_id = uuid4().hex
    output_template = str(output_dir / f"{download_id}.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    if requested_media == "audio":
        ydl_opts.update(
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }
        )
    else:
        ydl_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as downloader:
            info = downloader.extract_info(normalized_url, download=True)
            prepared_path = Path(downloader.prepare_filename(info))

        if requested_media == "audio":
            prepared_path = prepared_path.with_suffix(".mp3")

        if not prepared_path.exists():
            candidates = sorted(output_dir.glob(f"{download_id}.*"), key=lambda path: path.stat().st_mtime, reverse=True)
            prepared_path = candidates[0] if candidates else prepared_path

        if not prepared_path.exists() or prepared_path.stat().st_size == 0:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Download não gerou arquivo válido.")

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Não foi possível baixar esse link: {exc}",
        ) from exc

    title = info.get("title") if isinstance(info, dict) else "polaryix-download"
    safe_title = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(title)).strip("-") or "polaryix-download"
    filename = f"{safe_title}{prepared_path.suffix}"

    return FileResponse(
        prepared_path,
        media_type="application/octet-stream",
        filename=filename,
    )
