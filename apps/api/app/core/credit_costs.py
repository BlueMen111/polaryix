from __future__ import annotations


CONVERSION_CREDIT_COST = 3
YOUTUBE_VIDEO_CREDIT_COST = 7
MP3_DOWNLOAD_CREDIT_COST = 4


def conversion_credit_cost(amount: int = 1) -> int:
    return max(int(amount), 0) * CONVERSION_CREDIT_COST


def link_download_credit_cost(download_format: str, media_type: str) -> int:
    option = download_format.strip().lower()
    normalized_media = media_type.strip().lower()

    if option == "mp3" or normalized_media == "audio":
        return MP3_DOWNLOAD_CREDIT_COST

    if option in {"mp4", "hd", "4k"}:
        return YOUTUBE_VIDEO_CREDIT_COST

    return CONVERSION_CREDIT_COST
