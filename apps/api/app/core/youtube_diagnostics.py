from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from app.core.config.settings import settings


YOUTUBE_AUTH_COOKIE_NAMES = {
    "LOGIN_INFO",
    "SID",
    "SSID",
    "APISID",
    "SAPISID",
    "__Secure-1PSID",
    "__Secure-3PSID",
}

YOUTUBE_ANTI_BOT_SIGNALS = (
    "sign in to confirm you're not a bot",
    "sign in to confirm you\u2019re not a bot",
    "confirm you're not a bot",
    "confirm you\u2019re not a bot",
    "use --cookies-from-browser or --cookies",
)

YOUTUBE_ANTI_BOT_MESSAGE = (
    "O YouTube recusou a sessao/cookie atual na VPS. O yt-dlp esta funcionando, "
    "mas o Google marcou a sessao/IP como suspeita. Reexporte cookies recentes "
    "de uma conta logada ou use uma conta dedicada aquecida para o servidor."
)

YOUTUBE_COOKIES_NOT_AUTHENTICATED_MESSAGE = (
    "O arquivo de cookies do YouTube existe, mas nao contem cookies de login. "
    "Reexporte os cookies estando logado no YouTube."
)


@dataclass(slots=True)
class YoutubeCookieDiagnostic:
    ok: bool
    reason: str
    message: str | None = None
    cookie_names: set[str] | None = None


class YoutubeDownloadError(Exception):
    def __init__(self, reason: str, message: str, fallback_available: bool = False) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message
        self.fallback_available = fallback_available

    def as_detail(self) -> dict:
        return {
            "ok": False,
            "reason": self.reason,
            "message": self.message,
            "fallback_available": self.fallback_available,
        }


def youtube_cookie_file_path() -> Path | None:
    configured = settings.youtube_cookies_file or settings.ytdlp_cookies_file
    if not configured:
        default_path = settings.storage_path / "cookies" / "youtube.txt"
        if default_path.exists() and default_path.is_file():
            return default_path
        return None

    path = Path(configured)
    if path.exists() and path.is_file():
        return path
    return None


def read_youtube_cookie_names(path: Path) -> set[str]:
    names: set[str] = set()
    try:
        for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = re.split(r"\s+", line)
            if len(parts) >= 7:
                names.add(parts[5])
    except OSError:
        return set()
    return names


def diagnose_youtube_cookies(path: Path | None = None) -> YoutubeCookieDiagnostic:
    cookie_path = path or youtube_cookie_file_path()
    if cookie_path is None:
        return YoutubeCookieDiagnostic(
            ok=False,
            reason="YOUTUBE_COOKIES_NOT_CONFIGURED",
            message="O arquivo de cookies do YouTube nao foi configurado no servidor.",
            cookie_names=set(),
        )

    cookie_names = read_youtube_cookie_names(cookie_path)
    if not (cookie_names & YOUTUBE_AUTH_COOKIE_NAMES):
        return YoutubeCookieDiagnostic(
            ok=False,
            reason="YOUTUBE_COOKIES_NOT_AUTHENTICATED",
            message=YOUTUBE_COOKIES_NOT_AUTHENTICATED_MESSAGE,
            cookie_names=cookie_names,
        )

    return YoutubeCookieDiagnostic(
        ok=True,
        reason="YOUTUBE_COOKIES_LOOK_AUTHENTICATED",
        cookie_names=cookie_names,
    )


def is_youtube_anti_bot_error(error: object) -> bool:
    message = str(error).lower()
    return any(signal in message for signal in YOUTUBE_ANTI_BOT_SIGNALS)


def youtube_video_id(url: str) -> str | None:
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


def youtube_preview_fallback(url: str) -> dict | None:
    video_id = youtube_video_id(url)
    if not video_id:
        return None

    return {
        "title": "Video do YouTube",
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        "duration": None,
        "uploader": "YouTube",
        "webpage_url": url,
        "provider": "youtube",
        "status": "download_blocked_external",
    }


def sanitized_ytdlp_command(url: str) -> str:
    cookie_path = youtube_cookie_file_path()
    cookie_label = str(cookie_path) if cookie_path else "<sem-cookies>"
    parsed = urlparse(url)
    video_id = youtube_video_id(url)
    safe_url = parsed._replace(query=urlencode({"v": video_id}) if video_id else "", fragment="").geturl()
    return (
        "yt-dlp --js-runtimes <configured> --remote-components <configured> "
        f"--cookies {cookie_label} --no-playlist --dump-json {safe_url}"
    )
