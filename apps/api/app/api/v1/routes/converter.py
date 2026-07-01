from __future__ import annotations

import re
import json
import logging
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone

UTC = timezone.utc
from functools import partial
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from starlette.background import BackgroundTask

try:
    import yt_dlp
except Exception:  # pragma: no cover - optional runtime dependency guard
    yt_dlp = None

from app.core.config.settings import settings
from app.core.auth_store import consume_user_credits, get_current_user, public_user
from app.core.conversion_history import create_conversion_record, update_conversion_record
from app.core.conversion_queue import submit_conversion_job
from app.core.credit_costs import CONVERSION_CREDIT_COST, link_download_credit_cost
from app.core.public_stats import record_public_operation
from app.core.youtube_diagnostics import (
    YOUTUBE_ANTI_BOT_MESSAGE,
    YoutubeDownloadError,
    diagnose_youtube_cookies,
    is_youtube_anti_bot_error,
    sanitized_ytdlp_command,
    youtube_cookie_file_path,
    youtube_preview_fallback,
)
from app.core.conversion.compatibility import (
    CONVERTIBLE_AUDIO_FORMATS,
    CONVERTIBLE_TABULAR_FORMATS,
    CONVERTIBLE_TEXT_FORMATS,
    CONVERTIBLE_VIDEO_FORMATS,
    REGISTERED_FORMATS,
    registered_extensions_for_format,
    validate_conversion,
)
from app.core.premium import FREE_PLAN, get_plan_limits
from app.core.security.file_security import FileSecurityError, validate_file_name, validate_upload_size


router = APIRouter(prefix="/converter", tags=["Converter"])
logger = logging.getLogger("polaryix.converter")

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
PRO_BATCH_LIMIT = 60

SUPPORTED_FORMATS = REGISTERED_FORMATS
SAFE_URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")
PREMIUM_DOWNLOAD_OPTIONS = {"hd", "4k"}
PLAN_MONTHLY_CREDITS = {"basic": "basic_monthly_credits", "pro": "pro_monthly_credits"}
LINK_DOWNLOAD_JOBS: dict[str, dict] = {}
ACTIVE_CONVERSIONS: dict[str, int] = {}
YTDLP_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.youtube.com/",
}


def _yt_dlp_cookiefile() -> str | None:
    path = youtube_cookie_file_path()
    return str(path) if path else None


def _apply_ytdlp_runtime_options(options: dict) -> dict:
    cookiefile = _yt_dlp_cookiefile()
    if cookiefile:
        options["cookiefile"] = cookiefile
    if settings.ytdlp_js_runtimes:
        js_runtimes = {}
        for raw_runtime in settings.ytdlp_js_runtimes.split(","):
            runtime = raw_runtime.strip()
            if not runtime:
                continue
            name, _, path = runtime.partition(":")
            js_runtimes[name.lower()] = {"path": path or None}
        if js_runtimes:
            options["js_runtimes"] = js_runtimes
    if settings.ytdlp_remote_components:
        options["remote_components"] = [part.strip() for part in settings.ytdlp_remote_components.split(",") if part.strip()]
    return options


def _youtube_download_error_detail(exc: YoutubeDownloadError) -> dict:
    return exc.as_detail()


def _raise_if_youtube_environment_error(exc: Exception, url: str) -> None:
    if _link_platform(url) != "youtube":
        return

    if is_youtube_anti_bot_error(exc):
        diagnostic = diagnose_youtube_cookies()
        if diagnostic.ok:
            logger.warning(
                "[youtube] cookies look authenticated but session/IP was refused by YouTube: url=%s command=%s",
                _safe_url_for_log(url),
                sanitized_ytdlp_command(url),
            )
        else:
            logger.warning(
                "[youtube] cookies file exists but is not authenticated: reason=%s url=%s command=%s",
                diagnostic.reason,
                _safe_url_for_log(url),
                sanitized_ytdlp_command(url),
            )

        logger.warning("[youtube] anti-bot blocked by YouTube: url=%s", _safe_url_for_log(url))
        raise YoutubeDownloadError(
            reason="YOUTUBE_ANTI_BOT_BLOCKED" if diagnostic.ok else diagnostic.reason,
            message=YOUTUBE_ANTI_BOT_MESSAGE if diagnostic.ok else (diagnostic.message or YOUTUBE_ANTI_BOT_MESSAGE),
            fallback_available=True,
        ) from exc


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


def _delete_temporary_file(path: Path) -> None:
    try:
        resolved = path.resolve()
        processed_root = settings.processed_path.resolve()
        if processed_root not in resolved.parents and resolved != processed_root:
            return
        if resolved.exists() and resolved.is_file():
            resolved.unlink()
    except OSError:
        return


def _usage_key(request: Request) -> str:
    client_id = request.headers.get("x-polaryix-client-id", "").strip()
    if client_id:
        return f"client:{client_id[:120]}"

    host = request.client.host if request.client else "anonymous"
    return f"ip:{host}"


def _request_account(request: Request, is_premium: bool = False, premium_plan: str = "basic") -> dict:
    user = get_current_user(request, required=False)
    if user:
        profile = public_user(user)
        return {
            "usage_key": f"user:{profile['id']}",
            "user_id": profile["id"],
            "is_authenticated": True,
            "is_premium": bool(profile["is_premium"]),
            "premium_plan": profile["plan"],
            "billing": profile["billing"],
            "limits": get_plan_limits(profile["plan"], profile["billing"], bool(profile["is_premium"])),
            "credits_remaining": int(profile["credits_remaining"]),
        }

    limits = FREE_PLAN

    return {
        "usage_key": _usage_key(request),
        "user_id": None,
        "is_authenticated": False,
        "is_premium": False,
        "premium_plan": limits.plan,
        "billing": limits.billing,
        "limits": limits,
        "credits_remaining": None,
    }


def _account_user(account: dict) -> dict | None:
    if not account.get("user_id"):
        return None
    return {
        "id": account.get("user_id"),
        "is_premium": bool(account.get("is_premium")),
        "plan": account.get("premium_plan") or "free",
        "billing": account.get("billing") or "daily",
    }


def _begin_conversion(account: dict, amount: int) -> None:
    key = str(account["usage_key"])
    limit = int(account["limits"].max_concurrent_conversions)
    current = ACTIVE_CONVERSIONS.get(key, 0)
    if current + amount > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Seu plano permite {limit} conversões simultâneas.",
        )
    ACTIVE_CONVERSIONS[key] = current + amount


def _finish_conversion(account: dict, amount: int) -> None:
    key = str(account["usage_key"])
    ACTIVE_CONVERSIONS[key] = max(ACTIVE_CONVERSIONS.get(key, 0) - amount, 0)


def _consume_account_credits(request: Request, account: dict, amount: int) -> None:
    if account.get("user_id"):
        consume_user_credits(str(account["user_id"]), amount)
        return

    _consume_credits(request, amount, bool(account["is_premium"]), str(account["premium_plan"]))


def _check_plan_file_size(file_size_bytes: int, account: dict) -> None:
    max_mb = int(account["limits"].max_file_size_mb)
    plan = str(account.get("premium_plan") or account["limits"].plan)
    if plan == "free":
        max_mb = settings.max_free_file_size_mb
    elif plan == "basic":
        max_mb = settings.max_basic_file_size_mb
    elif plan == "pro":
        max_mb = settings.max_pro_file_size_mb

    max_bytes = max_mb * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise FileSecurityError(f"Arquivo grande demais para seu plano. Limite atual: {max_mb} MB.")


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


def _consume_credits_for_usage_key(
    usage_key: str,
    amount: int,
    is_premium: bool = False,
    premium_plan: str = "basic",
) -> None:
    if amount <= 0:
        return

    now = datetime.now(UTC)
    usage = _read_usage()
    plan = premium_plan.strip().lower()
    limit = getattr(settings, PLAN_MONTHLY_CREDITS.get(plan, "basic_monthly_credits")) if is_premium else settings.free_daily_credits

    if is_premium:
        period = now.strftime("%Y-%m")
        reset_at = datetime(now.year + int(now.month == 12), 1 if now.month == 12 else now.month + 1, 1, tzinfo=UTC).isoformat()
        key = f"{usage_key}:premium:{plan}:{period}"
    else:
        period = "24h"
        key = f"{usage_key}:free:rolling"
        record = usage.get(key, {})
        reset_at = record.get("reset_at")
        try:
            parsed_reset = datetime.fromisoformat(reset_at) if reset_at else now
        except ValueError:
            parsed_reset = now
        if not reset_at or parsed_reset <= now:
            reset_at = (now + timedelta(hours=24)).isoformat()
            usage[key] = {"used": 0, "limit": limit, "period": period, "plan": "free", "reset_at": reset_at}

    current = int(usage.get(key, {}).get("used", 0))
    if current + amount > limit:
        detail = (
            f"Seus tokens gratuitos acabaram. Necessario: {amount}, restantes: {max(limit - current, 0)}. "
            "Eles renovam apos 24h, mas voce pode se tornar Premium para ter acesso ilimitado de uso."
            if not is_premium
            else f"Voce nao tem creditos suficientes neste ciclo. Limite: {limit}, usados: {current}, necessario: {amount}."
        )
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)

    usage[key] = {
        "used": current + amount,
        "limit": limit,
        "period": period,
        "plan": plan if is_premium else "free",
        "reset_at": reset_at,
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
            f"Seus tokens gratuitos acabaram. Necessario: {amount}, restantes: {max(limit - current, 0)}. "
            "Eles renovam apos 24h, mas voce pode se tornar Premium para ter acesso ilimitado de uso."
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
    return link_download_credit_cost(download_format, media_type)


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


def _link_platform(url: str | None) -> str:
    if not url:
        return "generic"

    hostname = (urlparse(url).hostname or "").lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]

    if hostname in {"youtube.com", "youtu.be", "music.youtube.com", "m.youtube.com"} or hostname.endswith(".youtube.com"):
        return "youtube"
    if hostname == "instagram.com" or hostname.endswith(".instagram.com"):
        return "instagram"
    if hostname == "tiktok.com" or hostname.endswith(".tiktok.com"):
        return "tiktok"
    return "generic"


def _safe_url_for_log(url: str | None) -> str:
    if not url:
        return ""

    parsed = urlparse(url)
    platform = _link_platform(url)
    if platform == "youtube":
        video_id = _youtube_video_id(url)
        query = urlencode({"v": video_id}) if video_id else ""
        return parsed._replace(query=query, fragment="").geturl()

    return parsed._replace(query="", fragment="").geturl()


def _youtube_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]

    if hostname == "youtu.be":
        return parsed.path.strip("/").split("/")[0] or None

    if hostname == "youtube.com" or hostname.endswith(".youtube.com"):
        query_id = parse_qs(parsed.query).get("v", [None])[0]
        if query_id:
            return query_id
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live"}:
            return path_parts[1]

    return None


def _youtube_oembed_preview(url: str) -> dict | None:
    video_id = _youtube_video_id(url)
    if not video_id:
        return None

    preview = {
        "title": "Video do YouTube",
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        "duration": None,
        "uploader": "YouTube",
        "webpage_url": url,
    }

    try:
        query = urlencode({"url": url, "format": "json"})
        with urlopen(f"https://www.youtube.com/oembed?{query}", timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
        preview.update(
            {
                "title": data.get("title") or preview["title"],
                "thumbnail": data.get("thumbnail_url") or preview["thumbnail"],
                "uploader": data.get("author_name") or preview["uploader"],
            }
        )
    except Exception:
        pass

    return preview


def _clean_error_message(value: object, url: str | None = None) -> str:
    message = ANSI_PATTERN.sub("", str(value)).strip()
    lower_message = message.lower()
    platform = _link_platform(url)

    if platform == "instagram" and ("instagram sent an empty media response" in lower_message or "cookies" in lower_message):
        return (
            "O Instagram não liberou essa mídia publicamente. Abra o post no navegador sem login para confirmar se ele é público. "
            "Se exigir conta/login, será necessário configurar cookies no servidor para baixar esse conteúdo."
        )

    if platform == "youtube":
        if is_youtube_anti_bot_error(message):
            diagnostic = diagnose_youtube_cookies()
            return YOUTUBE_ANTI_BOT_MESSAGE if diagnostic.ok else (diagnostic.message or YOUTUBE_ANTI_BOT_MESSAGE)

        private_signals = (
            "private video",
            "this video is private",
            "members-only",
            "sign in to confirm your age",
            "confirm your age",
            "this video may be inappropriate",
            "requires payment",
            "not available in your country",
        )
        if any(signal in lower_message for signal in private_signals):
            return "Este vídeo do YouTube parece estar privado, restrito ou exigindo autenticação."

        technical_signals = (
            "cookies",
            "http error",
            "forbidden",
            "unable to download",
            "unable to extract",
            "timed out",
            "timeout",
            "temporary failure",
            "network is unreachable",
            "connection reset",
            "requested format is not available",
            "nsig",
            "signature",
            "ffmpeg",
        )
        if any(signal in lower_message for signal in technical_signals):
            return (
                "Não foi possível preparar este vídeo do YouTube no servidor. O link parece público, "
                "mas o servidor não conseguiu obter os dados do vídeo. Verifique se yt-dlp/ffmpeg "
                "estão instalados e atualizados, e tente novamente."
            )

    if "requested format is not available" in lower_message:
        return "Esse formato não está disponível para o link informado. Tente MP4, MP3 ou Full HD no Premium."

    if platform == "youtube" and ("http error 403" in lower_message or "forbidden" in lower_message):
        return (
            "Não foi possível preparar este vídeo do YouTube no servidor. O link parece público, "
            "mas o servidor não conseguiu obter os dados do vídeo. Verifique se yt-dlp/ffmpeg "
            "estão instalados e atualizados, e tente novamente."
        )

    if "http error 403" in lower_message or "forbidden" in lower_message:
        return "A plataforma bloqueou temporariamente o acesso a essa mídia pública. Tente novamente em instantes."

    return message


def _link_download_options(download_format: str, is_premium: bool = False) -> tuple[str, str]:
    requested_media, candidates = _link_download_candidates(download_format, is_premium)
    return requested_media, candidates[0]


def _link_download_candidates(download_format: str, is_premium: bool = False) -> tuple[str, list[str]]:
    option = download_format.strip().lower()

    if option in PREMIUM_DOWNLOAD_OPTIONS and not is_premium:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Essa qualidade é exclusiva do Premium. Use MP4 ou MP3 no plano gratuito.",
        )

    if option == "mp3":
        return "audio", ["bestaudio[ext=m4a]/bestaudio/best"]

    if option == "mp4":
        return (
            "video",
            [
                "bestvideo[height<=720][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<=720]+bestaudio",
                "best[height<=720][ext=mp4]/best[height<=720]",
                "bestvideo[height<=480][vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[height<=480][ext=mp4]/best[height<=480]",
                "18/best[ext=mp4]/best",
            ],
        )

    if option == "hd":
        return (
            "video",
            [
                "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                "best[height<=1080][ext=mp4]/best[height<=1080]/best",
                "bestvideo[height<=720][vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[height<=720]",
            ],
        )

    if option == "4k":
        return (
            "video",
            [
                "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
                "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
                "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                "best[height<=1080][ext=mp4]/best[height<=1080]/best",
            ],
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Formato de download inválido. Use mp4, mp3 ou 4k.",
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


def _is_compatible_mp4(input_path: Path) -> bool:
    if input_path.suffix.lower() != ".mp4" or shutil.which("ffprobe") is None:
        return False

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=codec_type,codec_name,pix_fmt",
        "-of",
        "json",
        str(input_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        return False

    try:
        streams = json.loads(result.stdout).get("streams", [])
    except json.JSONDecodeError:
        return False

    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    has_compatible_video = any(
        stream.get("codec_name") == "h264" and stream.get("pix_fmt") in {"yuv420p", "yuvj420p", None}
        for stream in video_streams
    )
    has_compatible_audio = not audio_streams or any(stream.get("codec_name") == "aac" for stream in audio_streams)

    return has_compatible_video and has_compatible_audio


def _video_height(input_path: Path) -> int | None:
    if shutil.which("ffprobe") is None or not input_path.exists():
        return None

    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=height",
        "-of",
        "json",
        str(input_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return None

    try:
        streams = json.loads(result.stdout).get("streams", [])
    except json.JSONDecodeError:
        return None

    if not streams:
        return None

    try:
        return int(streams[0].get("height"))
    except (TypeError, ValueError):
        return None


def _quality_label(path: Path, requested_media: str, download_format: str) -> str:
    if requested_media == "audio":
        return "MP3"

    height = _video_height(path)
    if height is None:
        return download_format.upper()
    if height >= 2160:
        return "4K"
    if height >= 1440:
        return "1440p"
    if height >= 1080:
        return "1080p"
    if height >= 720:
        return "720p"
    return f"{height}p"


def _update_link_job(job_id: str, **updates: object) -> None:
    job = LINK_DOWNLOAD_JOBS.get(job_id)
    if not job:
        return

    job.update(updates)
    job["updated_at"] = datetime.now(UTC).isoformat()


def _prepare_link_download(
    normalized_url: str,
    media_type: str,
    download_format: str,
    is_premium: bool,
    progress_callback=None,
) -> tuple[Path, str, str]:
    if yt_dlp is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Download por link requer yt-dlp instalado no ambiente.",
        )

    requested_media, ytdlp_formats = _link_download_candidates(download_format, is_premium)
    output_dir = settings.processed_path / "link_downloads"
    output_dir.mkdir(parents=True, exist_ok=True)
    download_id = uuid4().hex

    def emit_progress(percent: int, message: str) -> None:
        if progress_callback:
            progress_callback(percent, message)

    def hook(data: dict) -> None:
        status_value = data.get("status")
        if status_value == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            downloaded = data.get("downloaded_bytes") or 0
            if total:
                percent = 10 + int(min(downloaded / total, 1) * 68)
                emit_progress(percent, "Baixando mídia...")
            else:
                emit_progress(28, "Baixando mídia...")
        elif status_value == "finished":
            emit_progress(78, "Download concluído. Preparando arquivo...")

    ydl_opts = {
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook],
        "socket_timeout": 25,
        "retries": 3,
        "fragment_retries": 3,
        "extractor_retries": 2,
        "file_access_retries": 2,
        "continuedl": True,
        "concurrent_fragment_downloads": 1,
        "http_chunk_size": 10 * 1024 * 1024,
        "http_headers": YTDLP_HTTP_HEADERS,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
            }
        },
    }
    _apply_ytdlp_runtime_options(ydl_opts)

    if requested_media == "audio":
        ydl_opts.update(
            {
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
        ydl_opts["merge_output_format"] = "mp4"

    emit_progress(8, "Iniciando download...")

    info = None
    prepared_path: Path | None = None
    last_error: Exception | None = None

    for index, ytdlp_format in enumerate(ytdlp_formats, start=1):
        attempt_id = download_id if index == 1 else f"{download_id}-{index}"
        attempt_template = str(output_dir / f"{attempt_id}.%(ext)s")
        attempt_opts = {**ydl_opts, "format": ytdlp_format, "outtmpl": attempt_template}

        if index > 1:
            emit_progress(12, "Tentando formato alternativo mais estável...")

        try:
            with yt_dlp.YoutubeDL(attempt_opts) as downloader:
                info = downloader.extract_info(normalized_url, download=True)
                prepared_path = Path(downloader.prepare_filename(info))
            break
        except Exception as exc:
            last_error = exc
            _raise_if_youtube_environment_error(exc, normalized_url)
            logger.warning(
                "Link download attempt failed: platform=%s url=%s format=%s error=%r",
                _link_platform(normalized_url),
                _safe_url_for_log(normalized_url),
                ytdlp_format,
                exc,
            )
            for partial_path in output_dir.glob(f"{attempt_id}*"):
                if partial_path.is_file():
                    partial_path.unlink(missing_ok=True)

    if prepared_path is None:
        raise last_error or RuntimeError("Não foi possível baixar esse link.")

    if requested_media == "audio":
        prepared_path = prepared_path.with_suffix(".mp3")

    if not prepared_path.exists():
        candidates = sorted(output_dir.glob(f"{download_id}*.*"), key=lambda path: path.stat().st_mtime, reverse=True)
        prepared_path = candidates[0] if candidates else prepared_path

    if not prepared_path.exists() or prepared_path.stat().st_size == 0:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Download não gerou arquivo válido.")

    if requested_media == "video":
        emit_progress(86, "Verificando compatibilidade do vídeo...")
        if not _is_compatible_mp4(prepared_path):
            emit_progress(90, "Convertendo para MP4 compatível...")
            compatible_path = output_dir / f"{download_id}-compatible.mp4"
            _transcode_to_compatible_mp4(prepared_path, compatible_path)
            prepared_path = compatible_path

    title = info.get("title") if isinstance(info, dict) else "polaryix-download"
    safe_title = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(title)).strip("-") or "polaryix-download"
    filename = f"{safe_title}{prepared_path.suffix}"
    emit_progress(100, "Arquivo pronto.")

    return prepared_path, filename, _quality_label(prepared_path, requested_media, download_format)


def _run_link_download_job(
    job_id: str,
    normalized_url: str,
    media_type: str,
    download_format: str,
    is_premium: bool,
    premium_plan: str,
    usage_key: str,
    user_id: str | None = None,
    history_id: str | None = None,
) -> None:
    try:
        def progress(percent: int, message: str) -> None:
            _update_link_job(job_id, status="running", progress=max(0, min(percent, 99)), message=message)
            if history_id:
                update_conversion_record(history_id, status="processing", started_at=datetime.now(UTC).isoformat())

        prepared_path, filename, quality_delivered = _prepare_link_download(normalized_url, media_type, download_format, is_premium, progress)
        cost = _download_credit_cost(download_format, media_type)
        if user_id:
            consume_user_credits(user_id, cost)
        else:
            _consume_credits_for_usage_key(usage_key, cost, is_premium, premium_plan)
        if history_id:
            update_conversion_record(
                history_id,
                status="completed",
                finished_at=datetime.now(UTC).isoformat(),
                output_path=str(prepared_path),
                file_size=prepared_path.stat().st_size if prepared_path.exists() else 0,
                download_url=f"/api/v1/me/files/{history_id}/download",
                quality_delivered=quality_delivered,
            )
        record_public_operation("download", event_id=history_id or f"download:{job_id}", amount=1)
        _update_link_job(
            job_id,
            status="ready",
            progress=100,
            message="Download pronto.",
            file_path=str(prepared_path),
            filename=filename,
            download_url=f"/api/v1/converter/download-link/jobs/{job_id}/file",
            quality_delivered=quality_delivered,
        )
    except HTTPException as exc:
        if history_id:
            update_conversion_record(history_id, status="failed", error_message=str(exc.detail), finished_at=datetime.now(UTC).isoformat())
        _update_link_job(job_id, status="error", progress=0, message=str(exc.detail))
    except YoutubeDownloadError as exc:
        if history_id:
            update_conversion_record(history_id, status="failed", error_message=exc.message, finished_at=datetime.now(UTC).isoformat())
        _update_link_job(
            job_id,
            status="error",
            progress=0,
            message=exc.message,
            reason=exc.reason,
            fallback_available=exc.fallback_available,
        )
    except Exception as exc:
        message = f"Nao foi possivel baixar esse link: {_clean_error_message(exc, normalized_url)}"
        if history_id:
            update_conversion_record(history_id, status="failed", error_message=message, finished_at=datetime.now(UTC).isoformat())
        _update_link_job(job_id, status="error", progress=0, message=message)


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


async def _save_upload(file: UploadFile, destination: Path, source_format: str, account: dict | None = None) -> str:
    safe_name = validate_file_name(file.filename or "arquivo")
    size_bytes = await validate_upload_size(file)

    if size_bytes <= 0:
        raise FileSecurityError("O arquivo enviado está vazio.")
    if account is not None:
        _check_plan_file_size(size_bytes, account)

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

    account = _request_account(request, is_premium, premium_plan)
    if account.get("user_id"):
        user = get_current_user(request, required=True)
        profile = public_user(user)
        return {
            "used": max(int(profile["monthly_credits"]) - int(profile["credits_remaining"]), 0),
            "limit": profile["monthly_credits"],
            "remaining": profile["credits_remaining"],
            "reset_at": profile.get("plan_expires_at") or "",
            "plan": profile["plan"],
            "billing": profile["billing"],
            "is_premium": profile["is_premium"],
        }

    current_usage = _current_usage(
        request,
        bool(account["is_premium"]),
        str(account["premium_plan"]),
    )
    return {
        "used": current_usage["used"],
        "limit": current_usage["limit"],
        "remaining": current_usage["remaining"],
        "reset_at": current_usage["reset_at"],
        "plan": current_usage["plan"],
        "billing": "daily",
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
    account = _request_account(request, is_premium, premium_plan)
    _begin_conversion(account, 1)

    try:
        with tempfile.TemporaryDirectory(prefix="polaryix-convert-") as temp_dir:
            workdir = Path(temp_dir)
            input_path = workdir / f"input-{uuid4().hex}.{source_format.lower()}"
            safe_name = await _save_upload(file, input_path, source_format, account)
            future = submit_conversion_job(
                _convert_stored_file,
                input_path,
                safe_name,
                source_format,
                target_format,
                workdir,
                priority_level=int(account["limits"].priority_level),
            )
            output_path, output_name = future.result()
            _consume_account_credits(request, account, CONVERSION_CREDIT_COST)

            final_path = settings.processed_path / "conversions" / f"{uuid4().hex}-{output_name}"
            final_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(output_path, final_path)
            record_public_operation("conversion", amount=1)

    except FileSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        _finish_conversion(account, 1)

    return FileResponse(
        final_path,
        media_type="application/octet-stream",
        filename=output_name,
        background=BackgroundTask(_delete_temporary_file, final_path),
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
    account = _request_account(request, is_premium, premium_plan)
    limit = int(account["limits"].max_concurrent_conversions)

    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Envie pelo menos um arquivo.")

    if len(files) > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Limite de {limit} arquivos por lote para este plano.",
        )

    _begin_conversion(account, len(files))
    try:
        with tempfile.TemporaryDirectory(prefix="polaryix-batch-") as temp_dir:
            workdir = Path(temp_dir)
            saved_files: list[tuple[Path, str]] = []
            converted: list[tuple[Path, str]] = []

            for index, file in enumerate(files, start=1):
                input_path = workdir / f"input-{index}-{uuid4().hex}.{source_format.lower()}"
                safe_name = await _save_upload(file, input_path, source_format, account)
                saved_files.append((input_path, safe_name))

            futures = [
                submit_conversion_job(
                    partial(_convert_stored_file, input_path, safe_name, source_format, target_format, workdir),
                    priority_level=int(account["limits"].priority_level),
                )
                for input_path, safe_name in saved_files
            ]
            for future in futures:
                converted.append(future.result())
            _consume_account_credits(request, account, len(saved_files) * CONVERSION_CREDIT_COST)

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
            record_public_operation("conversion", amount=len(converted))

    except FileSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        _finish_conversion(account, len(files))

    return FileResponse(
        final_path,
        media_type="application/zip",
        filename=zip_name,
        background=BackgroundTask(_delete_temporary_file, final_path),
    )


@router.post("/download-link/jobs")
async def create_download_link_job(
    background_tasks: BackgroundTasks,
    request: Request,
    url: str = Form(...),
    media_type: str = Form("video"),
    download_format: str = Form("mp4"),
    is_premium: bool = Form(False),
    premium_plan: str = Form("basic"),
) -> dict:
    normalized_url = url.strip()
    if not SAFE_URL_PATTERN.match(normalized_url):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe uma URL http ou https válida.")

    account = _request_account(request, is_premium, premium_plan)
    selected_download_format = download_format or ("mp3" if media_type == "audio" else "mp4")
    _link_download_options(selected_download_format, bool(account["is_premium"]))
    logger.info(
        "Link download job requested: platform=%s url=%s format=%s media=%s premium=%s",
        _link_platform(normalized_url),
        _safe_url_for_log(normalized_url),
        selected_download_format,
        media_type,
        bool(account["is_premium"]),
    )

    job_id = uuid4().hex
    now = datetime.now(UTC).isoformat()
    history_id = None
    if account.get("user_id"):
        record = create_conversion_record(
            user_id=account["user_id"],
            user=_account_user(account),
            original_filename=normalized_url,
            original_format="LINK",
            target_format=selected_download_format.upper(),
            status="queued",
            quality_requested=selected_download_format.upper(),
            is_premium_job=bool(account["is_premium"]),
            priority_level=int(account["limits"].priority_level),
            operation_type=f"download_{media_type}",
            extension=selected_download_format.lower(),
            expires_at=(datetime.now(UTC) + timedelta(minutes=settings.link_download_retention_minutes)).isoformat(),
        )
        history_id = str(record["id"])

    LINK_DOWNLOAD_JOBS[job_id] = {
        "id": job_id,
        "history_id": history_id,
        "status": "queued",
        "progress": 3,
        "message": "Download na fila...",
        "filename": None,
        "download_url": None,
        "created_at": now,
        "updated_at": now,
        "expires_at": (datetime.now(UTC) + timedelta(minutes=settings.link_download_retention_minutes)).isoformat(),
    }

    submit_conversion_job(
        _run_link_download_job,
        job_id,
        normalized_url,
        media_type,
        selected_download_format,
        bool(account["is_premium"]),
        str(account["premium_plan"]),
        str(account["usage_key"]),
        account.get("user_id"),
        history_id,
        priority_level=int(account["limits"].priority_level),
    )

    return LINK_DOWNLOAD_JOBS[job_id]


@router.get("/download-link/jobs/{job_id}")
async def get_download_link_job(job_id: str) -> dict:
    job = LINK_DOWNLOAD_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job de download não encontrado.")

    expires_at = job.get("expires_at")
    try:
        is_expired = bool(expires_at and datetime.fromisoformat(str(expires_at)) <= datetime.now(UTC))
    except ValueError:
        is_expired = False

    if is_expired:
        file_path = Path(str(job.get("file_path", "")))
        _delete_temporary_file(file_path)
        LINK_DOWNLOAD_JOBS.pop(job_id, None)
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Download expirado. Prepare o arquivo novamente.")

    return {key: value for key, value in job.items() if key != "file_path"}


@router.get("/download-link/jobs/{job_id}/file")
async def get_download_link_job_file(job_id: str) -> FileResponse:
    job = LINK_DOWNLOAD_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job de download não encontrado.")

    if job.get("status") != "ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="O download ainda não está pronto.")

    expires_at = job.get("expires_at")
    try:
        is_expired = bool(expires_at and datetime.fromisoformat(str(expires_at)) <= datetime.now(UTC))
    except ValueError:
        is_expired = False

    if is_expired:
        file_path = Path(str(job.get("file_path", "")))
        _delete_temporary_file(file_path)
        LINK_DOWNLOAD_JOBS.pop(job_id, None)
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Download expirado. Prepare o arquivo novamente.")

    file_path = Path(str(job.get("file_path", "")))
    if not file_path.exists() or file_path.stat().st_size == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo final não encontrado.")

    def cleanup_downloaded_file() -> None:
        _delete_temporary_file(file_path)
        LINK_DOWNLOAD_JOBS.pop(job_id, None)

    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=str(job.get("filename") or file_path.name),
        background=BackgroundTask(cleanup_downloaded_file),
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

    account = _request_account(request, is_premium, premium_plan)
    selected_download_format = download_format or ("mp3" if media_type == "audio" else "mp4")
    requested_media, ytdlp_format = _link_download_options(selected_download_format, bool(account["is_premium"]))

    output_dir = settings.processed_path / "link_downloads"
    output_dir.mkdir(parents=True, exist_ok=True)
    download_id = uuid4().hex
    output_template = str(output_dir / f"{download_id}.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "http_headers": YTDLP_HTTP_HEADERS,
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }
    _apply_ytdlp_runtime_options(ydl_opts)

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
            if not _is_compatible_mp4(prepared_path):
                compatible_path = output_dir / f"{download_id}-compatible.mp4"
                _transcode_to_compatible_mp4(prepared_path, compatible_path)
                prepared_path = compatible_path

        _consume_account_credits(request, account, _download_credit_cost(selected_download_format, media_type))
        record_public_operation("download", amount=1)

    except HTTPException:
        raise
    except YoutubeDownloadError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_youtube_download_error_detail(exc),
        ) from exc
    except Exception as exc:
        try:
            _raise_if_youtube_environment_error(exc, normalized_url)
        except YoutubeDownloadError as typed_exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_youtube_download_error_detail(typed_exc),
            ) from typed_exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Não foi possível baixar esse link: {_clean_error_message(exc, normalized_url)}",
        ) from exc

    title = info.get("title") if isinstance(info, dict) else "polaryix-download"
    safe_title = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(title)).strip("-") or "polaryix-download"
    filename = f"{safe_title}{prepared_path.suffix}"

    return FileResponse(
        prepared_path,
        media_type="application/octet-stream",
        filename=filename,
        background=BackgroundTask(_delete_temporary_file, prepared_path),
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

    preview_options = _apply_ytdlp_runtime_options(
        {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "socket_timeout": 15,
            "http_headers": YTDLP_HTTP_HEADERS,
            "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
        }
    )

    try:
        with yt_dlp.YoutubeDL(preview_options) as downloader:
            info = downloader.extract_info(normalized_url, download=False)
    except Exception as exc:
        logger.warning(
            "Link preview failed: platform=%s url=%s error=%r",
            _link_platform(normalized_url),
            _safe_url_for_log(normalized_url),
            exc,
        )
        if _link_platform(normalized_url) == "youtube":
            try:
                _raise_if_youtube_environment_error(exc, normalized_url)
            except YoutubeDownloadError as typed_exc:
                preview = _youtube_oembed_preview(normalized_url) or youtube_preview_fallback(normalized_url)
                if preview:
                    preview["status"] = "download_blocked_external"
                    preview["provider"] = "youtube"
                    preview["reason"] = typed_exc.reason
                    preview["message"] = typed_exc.message
                    return preview
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=_youtube_download_error_detail(typed_exc),
                ) from typed_exc
            preview = _youtube_oembed_preview(normalized_url)
            if preview:
                return preview
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Não foi possível carregar o preview desse link: {_clean_error_message(exc, normalized_url)}",
        ) from exc

    return {
        "title": info.get("title") or "Mídia encontrada",
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "uploader": info.get("uploader") or info.get("channel"),
        "webpage_url": info.get("webpage_url") or normalized_url,
    }
