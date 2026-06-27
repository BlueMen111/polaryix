from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import zipfile
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
FREE_BATCH_LIMIT = 2
PREMIUM_BATCH_LIMIT = 10

SUPPORTED_FORMATS = IMAGE_FORMATS.keys() | VIDEO_FORMATS | AUDIO_FORMATS | TEXT_FORMATS | ARCHIVE_FORMATS
SAFE_URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")
PREMIUM_DOWNLOAD_OPTIONS = {"hd", "best"}


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


def _clean_error_message(value: object) -> str:
    message = ANSI_PATTERN.sub("", str(value)).strip()

    if "Instagram sent an empty media response" in message or "cookies" in message.lower():
        return (
            "O Instagram não liberou essa mídia publicamente. Abra o post no navegador sem login para confirmar se ele é público. "
            "Se exigir conta/login, será necessário configurar cookies no servidor para baixar esse conteúdo."
        )

    if "requested format is not available" in message.lower():
        return "Esse formato não está disponível para o link informado. Tente MP4 compatível, 720p ou MP3."

    return message


def _link_download_options(download_format: str) -> tuple[str, str]:
    option = download_format.strip().lower()

    if option in PREMIUM_DOWNLOAD_OPTIONS:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Essa qualidade é exclusiva do Premium. Use MP4 compatível, 720p ou MP3 no plano gratuito.",
        )

    if option == "mp3":
        return "audio", "bestaudio/best"

    if option == "720p":
        return "video", "bestvideo[height<=720]+bestaudio/best[height<=720]/best"

    if option == "mp4":
        return "video", "bestvideo[height<=720]+bestaudio/best[height<=720]/best"

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Formato de download inválido. Use mp4, mp3, 720p, hd ou best.",
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


def _transcode_to_compatible_mp4(input_path: Path, output_path: Path) -> None:
    _ensure_ffmpeg_available()

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "Erro ao preparar MP4 compatível."
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


def _convert_text(input_path: Path, output_path: Path) -> None:
    data = input_path.read_bytes()
    output_path.write_bytes(data)


def _convert_to_zip(input_path: Path, output_path: Path, original_name: str) -> None:
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


def _convert_stored_file(
    input_path: Path,
    original_name: str,
    source_format: str,
    target_format: str,
    workdir: Path,
) -> tuple[Path, str]:
    output_name = _output_filename(original_name, target_format)
    output_path = workdir / f"{uuid4().hex}-{output_name}"

    if source_format in IMAGE_FORMATS and target_format in IMAGE_FORMATS:
        _convert_image(input_path, output_path, target_format)
    elif target_format == "ZIP":
        _convert_to_zip(input_path, output_path, original_name)
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

    return output_path, output_name


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
            output_path, output_name = _convert_stored_file(input_path, safe_name, source_format, target_format, workdir)

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


@router.post("/convert-batch")
async def convert_batch(
    files: list[UploadFile] = File(...),
    from_format: str = Form(...),
    to_format: str = Form(...),
    is_premium: bool = Form(False),
) -> FileResponse:
    """Converte múltiplos arquivos e devolve um ZIP com os resultados."""

    source_format = _normalize_format(from_format)
    target_format = _normalize_format(to_format)
    limit = PREMIUM_BATCH_LIMIT if is_premium else FREE_BATCH_LIMIT

    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Envie pelo menos um arquivo.")

    if len(files) > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Limite de {limit} arquivos por lote para este plano.",
        )

    try:
        with tempfile.TemporaryDirectory(prefix="polaryix-batch-") as temp_dir:
            workdir = Path(temp_dir)
            converted: list[tuple[Path, str]] = []

            for index, file in enumerate(files, start=1):
                input_path = workdir / f"input-{index}-{uuid4().hex}.{source_format.lower()}"
                safe_name = await _save_upload(file, input_path)
                converted.append(_convert_stored_file(input_path, safe_name, source_format, target_format, workdir))

            zip_name = f"polaryix-conversoes-{uuid4().hex[:8]}.zip"
            zip_path = workdir / zip_name

            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                used_names: set[str] = set()
                for output_path, output_name in converted:
                    archive_name = output_name
                    if archive_name in used_names:
                        archive_name = f"{Path(output_name).stem}-{uuid4().hex[:6]}{Path(output_name).suffix}"
                    used_names.add(archive_name)
                    archive.write(output_path, arcname=archive_name)

            final_path = settings.processed_path / "conversions" / zip_name
            final_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(zip_path, final_path)

    except FileSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return FileResponse(
        final_path,
        media_type="application/zip",
        filename=zip_name,
    )


@router.post("/download-link")
async def download_link(
    url: str = Form(...),
    media_type: str = Form("video"),
    download_format: str = Form("mp4"),
) -> FileResponse:
    """Baixa vídeo/áudio por URL e devolve um arquivo compatível."""

    if yt_dlp is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Download por link requer yt-dlp instalado no ambiente.",
        )

    normalized_url = url.strip()
    if not SAFE_URL_PATTERN.match(normalized_url):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe uma URL http ou https válida.")

    requested_media, ytdlp_format = _link_download_options(download_format or ("mp3" if media_type == "audio" else "mp4"))

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
                "format": ytdlp_format,
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
        ydl_opts["format"] = ytdlp_format
        ydl_opts["merge_output_format"] = "mp4"

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

        if requested_media == "video":
            compatible_path = output_dir / f"{download_id}-compatible.mp4"
            _transcode_to_compatible_mp4(prepared_path, compatible_path)
            prepared_path = compatible_path

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Não foi possível baixar esse link: {_clean_error_message(exc)}",
        ) from exc

    title = info.get("title") if isinstance(info, dict) else "polaryix-download"
    safe_title = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(title)).strip("-") or "polaryix-download"
    filename = f"{safe_title}{prepared_path.suffix}"

    return FileResponse(
        prepared_path,
        media_type="application/octet-stream",
        filename=filename,
    )


@router.post("/link-preview")
async def link_preview(url: str = Form(...)) -> dict:
    """Obtém metadados públicos de uma URL suportada sem baixar o arquivo."""

    if yt_dlp is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Preview por link requer yt-dlp instalado no ambiente.",
        )

    normalized_url = url.strip()
    if not SAFE_URL_PATTERN.match(normalized_url):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe uma URL http ou https válida.")

    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True}) as downloader:
            info = downloader.extract_info(normalized_url, download=False)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Não foi possível carregar o preview desse link: {_clean_error_message(exc)}",
        ) from exc

    return {
        "title": info.get("title") or "Mídia encontrada",
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "uploader": info.get("uploader") or info.get("channel"),
        "webpage_url": info.get("webpage_url") or normalized_url,
    }
