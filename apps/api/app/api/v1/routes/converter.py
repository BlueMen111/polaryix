from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

try:
    import yt_dlp
except Exception:  # pragma: no cover - optional runtime dependency guard
    yt_dlp = None

from app.core.config.settings import settings
from app.core.conversion.compatibility import (
    CONVERTIBLE_AUDIO_FORMATS,
    CONVERTIBLE_TABULAR_FORMATS,
    CONVERTIBLE_TEXT_FORMATS,
    CONVERTIBLE_VIDEO_FORMATS,
    REGISTERED_FORMATS,
    registered_extensions_for_format,
    validate_conversion,
)
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

VIDEO_FORMATS = CONVERTIBLE_VIDEO_FORMATS
AUDIO_FORMATS = CONVERTIBLE_AUDIO_FORMATS
TEXT_FORMATS = CONVERTIBLE_TEXT_FORMATS
TABULAR_FORMATS = CONVERTIBLE_TABULAR_FORMATS
ARCHIVE_FORMATS = {"ZIP"}
FREE_BATCH_LIMIT = 2
BASIC_BATCH_LIMIT = 30
PRO_BATCH_LIMIT = 600

SUPPORTED_FORMATS = REGISTERED_FORMATS
SAFE_URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")
PREMIUM_DOWNLOAD_OPTIONS = {"hd"}
PLAN_MONTHLY_CREDITS = {"basic": "basic_monthly_credits", "pro": "pro_monthly_credits"}


def _normalize_format(value: str) -> str:
    normalized = value.strip().upper().lstrip(".")

    if normalized not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato não suportado: {value}",
        )

    return normalized


def _validate_conversion_or_raise(source_format: str, target_format: str) -> None:
    result = validate_conversion(source_format, target_format)
    if not result.allowed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=result.message)


def _usage_path() -> Path:
    return settings.storage_path / "usage" / "credits.json"


def _read_usage() -> dict:
    path = _usage_path()
    if not path.exists():
        return {}

    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def _write_usage(data: dict) -> None:
    import json

    path = _usage_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _usage_key(request: Request) -> str:
    client_id = request.headers.get("x-polaryix-client-id", "").strip()
    if client_id:
        return f"client:{client_id[:120]}"

    host = request.client.host if request.client else "anonymous"
    return f"ip:{host}"


def _consume_credits(request: Request, amount: int, is_premium: bool = False, premium_plan: str = "basic") -> None:
    if amount <= 0:
        return

    now = datetime.now(UTC)
    plan = premium_plan.strip().lower()
    period = now.strftime("%Y-%m") if is_premium else now.strftime("%Y-%m-%d")
    limit = getattr(settings, PLAN_MONTHLY_CREDITS.get(plan, "basic_monthly_credits")) if is_premium else settings.free_daily_credits
    key = f"{_usage_key(request)}:{'premium' if is_premium else 'free'}:{plan if is_premium else 'daily'}:{period}"

    usage = _read_usage()
    current = int(usage.get(key, {}).get("used", 0))

    if current + amount > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Você não tem créditos suficientes. Limite: {limit}, usados: {current}, necessário: {amount}.",
        )

    usage[key] = {
        "used": current + amount,
        "limit": limit,
        "period": period,
        "plan": plan if is_premium else "free",
        "updated_at": now.isoformat(),
    }
    _write_usage(usage)


def _credit_bucket(request: Request, is_premium: bool = False, premium_plan: str = "basic") -> tuple[str, int, str, datetime]:
    now = datetime.now(UTC)
    plan = premium_plan.strip().lower()
    limit = getattr(settings, PLAN_MONTHLY_CREDITS.get(plan, "basic_monthly_credits")) if is_premium else settings.free_daily_credits

    if is_premium:
        period = now.strftime("%Y-%m")
        next_month = datetime(now.year + int(now.month == 12), 1 if now.month == 12 else now.month + 1, 1, tzinfo=UTC)
        return f"{_usage_key(request)}:premium:{plan}:{period}", limit, period, next_month

    return f"{_usage_key(request)}:free:rolling", limit, "24h", now + timedelta(hours=24)


def _current_usage(request: Request, is_premium: bool = False, premium_plan: str = "basic") -> dict:
    now = datetime.now(UTC)
    key, limit, period, fallback_reset_at = _credit_bucket(request, is_premium, premium_plan)
    usage = _read_usage()
    record = usage.get(key, {})
    used = int(record.get("used", 0))
    reset_at = record.get("reset_at")

    if is_premium:
        reset_at = fallback_reset_at.isoformat()
    elif reset_at is None:
        used = 0
        reset_at = fallback_reset_at.isoformat()
    else:
        try:
            parsed_reset = datetime.fromisoformat(reset_at)
        except ValueError:
            parsed_reset = now
        if parsed_reset <= now:
            used = 0
            reset_at = fallback_reset_at.isoformat()

    return {
        "key": key,
        "used": used,
        "limit": limit,
        "remaining": max(limit - used, 0),
        "period": period,
        "reset_at": reset_at,
        "plan": premium_plan.strip().lower() if is_premium else "free",
        "is_premium": is_premium,
    }


def _consume_credits(request: Request, amount: int, is_premium: bool = False, premium_plan: str = "basic") -> None:
    if amount <= 0:
        return

    usage = _read_usage()
    current_usage = _current_usage(request, is_premium, premium_plan)
    key = current_usage["key"]
    current = int(current_usage["used"])
    limit = int(current_usage["limit"])

    if current + amount > limit:
        detail = (
            "Seus tokens gratuitos acabaram. Eles renovam apos 24h, mas voce pode se tornar Premium para ter acesso ilimitado de uso."
            if not is_premium
            else f"Voce nao tem creditos suficientes neste ciclo. Limite: {limit}, usados: {current}, necessario: {amount}."
        )
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)

    usage[key] = {
        "used": current + amount,
        "limit": limit,
        "period": current_usage["period"],
        "plan": current_usage["plan"],
        "reset_at": current_usage["reset_at"],
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _write_usage(usage)


def _download_credit_cost(download_format: str, media_type: str) -> int:
    option = download_format.strip().lower()
    if option == "mp3" or media_type.strip().lower() == "audio":
        return 2
    if option in {"mp4", "hd"}:
        return 5
    return 1


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
        return "Esse formato não está disponível para o link informado. Tente MP4, MP3 ou Full HD no Premium."

    return message


def _link_download_options(download_format: str, is_premium: bool = False) -> tuple[str, str]:
    option = download_format.strip().lower()

    if option in PREMIUM_DOWNLOAD_OPTIONS and not is_premium:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Essa qualidade é exclusiva do Premium. Use MP4 ou MP3 no plano gratuito.",
        )

    if option == "mp3":
        return "audio", "bestaudio/best"

    if option == "mp4":
        return "video", "bestvideo[height<=720]+bestaudio/best[height<=720]/best"

    if option == "hd":
        return "video", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Formato de download inválido. Use mp4, mp3 ou hd.",
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


def _read_tabular(input_path: Path, source_format: str):
    try:
        import pandas as pd
    except Exception as exc:  # pragma: no cover - dependency guard
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Conversão de planilhas requer pandas instalado no ambiente.",
        ) from exc

    try:
        if source_format == "CSV":
            return pd.read_csv(input_path, sep=None, engine="python")

        if source_format == "JSON":
            return pd.read_json(input_path)

        if source_format == "HTML":
            tables = pd.read_html(input_path)
            if not tables:
                raise ValueError("Nenhuma tabela encontrada no HTML.")
            return tables[0]

        if source_format == "XML":
            return pd.read_xml(input_path)

        if source_format == "XLSX":
            return pd.read_excel(input_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Não foi possível ler o arquivo {source_format} enviado para conversão.",
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Leitura tabular {source_format} ainda não é suportada.",
    )


def _convert_tabular(input_path: Path, output_path: Path, source_format: str, target_format: str) -> None:
    dataframe = _read_tabular(input_path, source_format)

    try:
        if target_format == "CSV":
            dataframe.to_csv(output_path, index=False)
            return

        if target_format == "JSON":
            dataframe.to_json(output_path, orient="records", force_ascii=False, indent=2)
            return

        if target_format == "HTML":
            dataframe.to_html(output_path, index=False)
            return

        if target_format == "XML":
            dataframe.to_xml(output_path, index=False)
            return

        if target_format == "XLSX":
            dataframe.to_excel(output_path, index=False, engine="openpyxl")
            return
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Não foi possível gerar o arquivo {target_format}.",
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Escrita tabular {target_format} ainda não é suportada.",
    )


def _convert_to_zip(input_path: Path, output_path: Path, original_name: str) -> None:
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(input_path, arcname=Path(original_name).name)


async def _save_upload(file: UploadFile, destination: Path, source_format: str) -> str:
    safe_name = validate_file_name(file.filename or "arquivo")
    size_bytes = await validate_upload_size(file)

    if size_bytes <= 0:
        raise FileSecurityError("O arquivo enviado está vazio.")

    extension = Path(safe_name).suffix.lower()
    expected_extensions = registered_extensions_for_format(source_format)

    if extension and extension not in expected_extensions:
        expected = ", ".join(sorted(expected_extensions))
        raise FileSecurityError(
            f"A extensão do arquivo não corresponde ao formato selecionado. "
            f"Para {source_format}, use: {expected}."
        )

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
    _validate_conversion_or_raise(source_format, target_format)

    output_name = _output_filename(original_name, target_format)
    output_path = workdir / f"{uuid4().hex}-{output_name}"

    if source_format in IMAGE_FORMATS and target_format in IMAGE_FORMATS:
        _convert_image(input_path, output_path, target_format)
    elif target_format == "ZIP":
        _convert_to_zip(input_path, output_path, original_name)
    elif source_format in TABULAR_FORMATS and target_format in TABULAR_FORMATS:
        _convert_tabular(input_path, output_path, source_format, target_format)
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


@router.get("/usage")
async def get_usage(
    request: Request,
    is_premium: bool = False,
    premium_plan: str = "basic",
) -> dict:
    """Retorna os créditos usados/restantes do cliente atual."""

    current_usage = _current_usage(request, is_premium, premium_plan)
    return {
        "used": current_usage["used"],
        "limit": current_usage["limit"],
        "remaining": current_usage["remaining"],
        "reset_at": current_usage["reset_at"],
        "plan": current_usage["plan"],
        "is_premium": current_usage["is_premium"],
    }


@router.post("/convert-file")
async def convert_file(
    request: Request,
    file: UploadFile = File(...),
    from_format: str = Form(...),
    to_format: str = Form(...),
    is_premium: bool = Form(False),
    premium_plan: str = Form("basic"),
) -> FileResponse:
    """Converte arquivos enviados e devolve o resultado como download."""

    source_format = _normalize_format(from_format)
    target_format = _normalize_format(to_format)
    _validate_conversion_or_raise(source_format, target_format)

    try:
        with tempfile.TemporaryDirectory(prefix="polaryix-convert-") as temp_dir:
            workdir = Path(temp_dir)
            input_path = workdir / f"input-{uuid4().hex}.{source_format.lower()}"
            safe_name = await _save_upload(file, input_path, source_format)
            _consume_credits(request, 1, is_premium, premium_plan)
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
    request: Request,
    files: list[UploadFile] = File(...),
    from_format: str = Form(...),
    to_format: str = Form(...),
    is_premium: bool = Form(False),
    premium_plan: str = Form("basic"),
) -> FileResponse:
    """Converte múltiplos arquivos e devolve um ZIP com os resultados."""

    source_format = _normalize_format(from_format)
    target_format = _normalize_format(to_format)
    _validate_conversion_or_raise(source_format, target_format)
    limit = (PRO_BATCH_LIMIT if premium_plan.strip().lower() == "pro" else BASIC_BATCH_LIMIT) if is_premium else FREE_BATCH_LIMIT

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
            saved_files: list[tuple[Path, str]] = []
            converted: list[tuple[Path, str]] = []

            for index, file in enumerate(files, start=1):
                input_path = workdir / f"input-{index}-{uuid4().hex}.{source_format.lower()}"
                safe_name = await _save_upload(file, input_path, source_format)
                saved_files.append((input_path, safe_name))

            _consume_credits(request, len(saved_files), is_premium, premium_plan)

            for input_path, safe_name in saved_files:
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
    request: Request,
    url: str = Form(...),
    media_type: str = Form("video"),
    download_format: str = Form("mp4"),
    is_premium: bool = Form(False),
    premium_plan: str = Form("basic"),
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

    selected_download_format = download_format or ("mp3" if media_type == "audio" else "mp4")
    requested_media, ytdlp_format = _link_download_options(selected_download_format, is_premium)
    _consume_credits(request, _download_credit_cost(selected_download_format, media_type), is_premium, premium_plan)

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
