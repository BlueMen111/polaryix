from __future__ import annotations

import io
import logging
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw, ImageFont, UnidentifiedImageError

from app.core.config.settings import settings

try:
    from rembg import remove as rembg_remove
except Exception:  # pragma: no cover - optional dependency
    rembg_remove = None


logger = logging.getLogger("polaryix.image_tools")

IMAGE_TOOL_COSTS = {
    "remove_background": 1,
    "optimize_image": 2,
    "remaster_image": 5,
}

SUPPORTED_IMAGE_FORMATS = {
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".webp": "WEBP",
}


def process_image_tool(job: dict) -> dict:
    operation = str(job.get("operation") or "")
    input_path = Path(str(job.get("input_path") or ""))
    if operation not in IMAGE_TOOL_COSTS:
        raise RuntimeError("Ferramenta de imagem invalida.")
    if not input_path.exists() or input_path.stat().st_size == 0:
        raise RuntimeError("Arquivo original nao encontrado.")

    output_dir = settings.processed_path / "image_tools"
    output_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as image:
        original_format = _detect_format(input_path, image)
        original_size = image.size

        if operation == "remove_background":
            result = remove_background(input_path, image)
            extension = ".png"
            save_format = "PNG"
        elif operation == "optimize_image":
            result = optimize_image(image)
            extension = _output_extension(input_path, original_format)
            save_format = original_format
        else:
            result = remaster_image(image)
            if not bool(job.get("is_premium")):
                result = apply_watermark(result)
                logger.info("Watermark applied to image tool job: %s", job.get("id"))
            extension = _output_extension(input_path, original_format)
            save_format = original_format

        if result.size != original_size:
            result = result.resize(original_size, Image.Resampling.LANCZOS)

        output_name = f"{Path(str(job.get('original_filename') or input_path.name)).stem}-polaryix-{operation}{extension}"
        output_path = output_dir / f"{uuid4().hex}-{output_name}"
        _save_image(result, output_path, save_format)

    return {"output_path": str(output_path), "file_size": output_path.stat().st_size}


def remove_background(input_path: Path, image: Image.Image) -> Image.Image:
    if rembg_remove is not None:
        data = input_path.read_bytes()
        output = rembg_remove(data)
        return Image.open(io.BytesIO(output)).convert("RGBA")

    rgba = image.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    border_samples: list[tuple[int, int, int]] = []
    for x in range(width):
        border_samples.append(pixels[x, 0][:3])
        border_samples.append(pixels[x, height - 1][:3])
    for y in range(height):
        border_samples.append(pixels[0, y][:3])
        border_samples.append(pixels[width - 1, y][:3])

    bg = tuple(sum(channel) // len(border_samples) for channel in zip(*border_samples))
    threshold = 34
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            distance = abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2])
            if distance < threshold:
                pixels[x, y] = (r, g, b, 0)
            elif distance < threshold * 2:
                pixels[x, y] = (r, g, b, int(a * min(1, distance / (threshold * 2))))
    return rgba


def optimize_image(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image)
    if image.mode in {"RGBA", "LA"}:
        return image.convert("RGBA")
    if image.mode == "P" and "transparency" in image.info:
        return image.convert("RGBA")
    return image.convert("RGB")


def remaster_image(image: Image.Image) -> Image.Image:
    original = ImageOps.exif_transpose(image).convert("RGBA")
    enhanced = original.filter(ImageFilter.MedianFilter(size=3))
    enhanced = ImageEnhance.Contrast(enhanced).enhance(1.1)
    enhanced = ImageEnhance.Color(enhanced).enhance(1.06)
    enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.35)
    detail = enhanced.filter(ImageFilter.UnsharpMask(radius=1.3, percent=120, threshold=4))
    detail.putalpha(original.getchannel("A"))
    return detail


def apply_watermark(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    overlay = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    text = "PolarYix"
    font_size = max(14, min(rgba.size) // 15)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    padding = max(10, min(rgba.size) // 35)
    position = (rgba.width - text_width - padding, rgba.height - text_height - padding)
    draw.text(position, text, fill=(255, 255, 255, 86), font=font)
    draw.text((position[0] + 1, position[1] + 1), text, fill=(6, 19, 52, 70), font=font)
    return Image.alpha_composite(rgba, overlay)


def _detect_format(path: Path, image: Image.Image) -> str:
    suffix_format = SUPPORTED_IMAGE_FORMATS.get(path.suffix.lower())
    detected = (image.format or suffix_format or "PNG").upper()
    if detected == "JPG":
        return "JPEG"
    return detected if detected in {"PNG", "JPEG", "WEBP"} else "PNG"


def _output_extension(path: Path, image_format: str) -> str:
    suffix = path.suffix.lower()
    if suffix in SUPPORTED_IMAGE_FORMATS and SUPPORTED_IMAGE_FORMATS[suffix] == image_format:
        return suffix
    return ".jpg" if image_format == "JPEG" else f".{image_format.lower()}"


def _save_image(image: Image.Image, output_path: Path, image_format: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_kwargs: dict[str, object] = {"optimize": True}

    if image_format == "JPEG":
        image = _flatten_for_jpeg(image)
        save_kwargs.update({"quality": 88, "progressive": True})
    elif image_format == "PNG":
        image = image.convert("RGBA")
        save_kwargs.update({"compress_level": 9})
    elif image_format == "WEBP":
        save_kwargs.update({"quality": 86, "method": 6})
        if image.mode not in {"RGBA", "RGB"}:
            image = image.convert("RGBA")
    else:
        image_format = "PNG"
        image = image.convert("RGBA")

    image.save(output_path, image_format, **save_kwargs)


def _flatten_for_jpeg(image: Image.Image) -> Image.Image:
    if image.mode not in {"RGBA", "LA", "P"}:
        return image.convert("RGB")

    rgba = image.convert("RGBA")
    background = Image.new("RGB", rgba.size, (255, 255, 255))
    background.paste(rgba, mask=rgba.getchannel("A"))
    return background


def validate_image_file(path: Path) -> None:
    try:
        with Image.open(path) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Imagem invalida ou corrompida.") from exc
