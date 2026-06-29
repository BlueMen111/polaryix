from __future__ import annotations

import logging
import threading
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw, ImageFont, UnidentifiedImageError

from app.core.config.settings import settings


logger = logging.getLogger("polaryix.image_tools")
_rembg_session = None
_rembg_lock = threading.Lock()

IMAGE_TOOL_COSTS = {
    "remove_background": 1,
    "optimize_image": 2,
    "upscale_image": 5,
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

        if operation == "remaster_image":
            operation = "upscale_image"

        if operation == "remove_background":
            logger.info("Starting background removal for job %s", job.get("id"))
            result = remove_background(input_path, image)
            transparency_ratio = _transparency_ratio(result)
            if transparency_ratio < 0.005:
                raise RuntimeError("Nao foi possivel identificar o fundo automaticamente nesta imagem. Tente uma imagem com melhor contraste entre o objeto e o fundo.")
            extension = ".png"
            save_format = "PNG"
            output_name = f"{Path(str(job.get('original_filename') or input_path.name)).stem}-polaryix-remove-background{extension}"
            output_path = output_dir / f"{uuid4().hex}-{output_name}"
            _save_image(result, output_path, save_format)
            logger.info("Background removal saved for job %s: %s", job.get("id"), output_path)
            return {
                "output_path": str(output_path),
                "file_size": output_path.stat().st_size,
                "original_size": input_path.stat().st_size,
                "final_size": output_path.stat().st_size,
                "message": f"Fundo removido. Transparencia detectada em {round(transparency_ratio * 100, 1)}% da imagem.",
            }
        elif operation == "optimize_image":
            logger.info("Starting image optimization for job %s", job.get("id"))
            result = optimize_image(image)
            extension = _output_extension(input_path, original_format)
            save_format = original_format
            output_name = f"{Path(str(job.get('original_filename') or input_path.name)).stem}-polaryix-optimized{extension}"
            output_path = output_dir / f"{uuid4().hex}-{output_name}"
            _save_image(result, output_path, save_format, optimize_operation=True)
            original_bytes = input_path.stat().st_size
            final_bytes = output_path.stat().st_size
            refund_credits = False
            message = None
            if final_bytes >= original_bytes:
                output_path.write_bytes(input_path.read_bytes())
                final_bytes = output_path.stat().st_size
                refund_credits = True
                message = "A imagem ja estava otimizada. Nenhuma reducao significativa foi possivel."
                logger.info("Image already optimized for job %s; credits will be refunded.", job.get("id"))
            reduction = max(0, round((1 - (final_bytes / max(original_bytes, 1))) * 100, 1))
            return {
                "output_path": str(output_path),
                "file_size": final_bytes,
                "original_size": original_bytes,
                "final_size": final_bytes,
                "reduction_percent": reduction,
                "refund_credits": refund_credits,
                "message": message,
            }
        else:
            logger.info("Starting image upscaling for job %s", job.get("id"))
            result = upscale_image(image, job.get("tool_options") or {}, bool(job.get("is_premium")))
            if not bool(job.get("is_premium")):
                result = apply_watermark(result)
                logger.info("Watermark applied to image tool job: %s", job.get("id"))
            extension = _output_extension(input_path, original_format)
            save_format = original_format

        if operation != "upscale_image" and result.size != original_size:
            result = result.resize(original_size, Image.Resampling.LANCZOS)

        output_name = f"{Path(str(job.get('original_filename') or input_path.name)).stem}-polaryix-upscale{extension}"
        output_path = output_dir / f"{uuid4().hex}-{output_name}"
        _save_image(result, output_path, save_format)

    return {
        "output_path": str(output_path),
        "file_size": output_path.stat().st_size,
        "original_size": input_path.stat().st_size,
        "final_size": output_path.stat().st_size,
        "message": f"{original_size[0]}x{original_size[1]} -> {result.size[0]}x{result.size[1]}",
    }


def remove_background(input_path: Path, image: Image.Image) -> Image.Image:
    global _rembg_session
    rembg_remove = _get_rembg_remove()

    rgba = ImageOps.exif_transpose(image).convert("RGBA")
    with _rembg_lock:
        result = rembg_remove(
            rgba,
            session=_rembg_session,
            alpha_matting=True,
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10,
            alpha_matting_erode_size=10,
            post_process_mask=True,
        )
    return result.convert("RGBA")


def warmup_remove_background_model() -> None:
    _get_rembg_remove()


def _get_rembg_remove():
    global _rembg_session
    try:
        import onnxruntime  # noqa: F401
        from rembg import new_session, remove as rembg_remove
    except Exception as exc:
        raise RuntimeError("A remocao de fundo ainda nao esta disponivel no servidor. A dependencia rembg[cpu] precisa ser instalada.") from exc

    with _rembg_lock:
        if _rembg_session is None:
            _rembg_session = new_session("u2net")
    return rembg_remove


def optimize_image(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image)
    if image.mode in {"RGBA", "LA"}:
        return image.convert("RGBA")
    if image.mode == "P" and "transparency" in image.info:
        return image.convert("RGBA")
    return image.convert("RGB")


def remaster_image(image: Image.Image) -> Image.Image:
    return upscale_image(image, {"scale": 1, "keep_original_size": True}, False)


def upscale_image(image: Image.Image, options: dict, is_premium: bool) -> Image.Image:
    original = ImageOps.exif_transpose(image).convert("RGBA")
    scale = int(options.get("scale") or 2)
    if scale not in {1, 2, 4}:
        scale = 2
    if not is_premium:
        scale = 2

    keep_original_size = bool(options.get("keep_original_size", False))
    sharpness = _float_option(options, "sharpness", 1.45 if is_premium else 1.3, 0.7, 2.4)
    denoise = _float_option(options, "denoise", 0.25 if is_premium else 0.18, 0.0, 1.0)
    contrast = _float_option(options, "contrast", 1.08 if is_premium else 1.05, 0.8, 1.6)
    detail = _float_option(options, "detail", 1.2 if is_premium else 1.08, 0.8, 1.8)
    intensity = _float_option(options, "intensity", 1.0, 0.4, 1.6)

    target_size = (original.width * scale, original.height * scale)
    upscaled = original.resize(target_size, Image.Resampling.LANCZOS)
    if denoise > 0:
        upscaled = upscaled.filter(ImageFilter.MedianFilter(size=3))
    upscaled = ImageEnhance.Contrast(upscaled).enhance(1 + ((contrast - 1) * intensity))
    upscaled = ImageEnhance.Color(upscaled).enhance(1 + (0.05 * intensity))
    upscaled = upscaled.filter(ImageFilter.UnsharpMask(radius=1.1, percent=int(110 * detail * intensity), threshold=3))
    upscaled = ImageEnhance.Sharpness(upscaled).enhance(sharpness)

    if keep_original_size:
        upscaled = upscaled.resize(original.size, Image.Resampling.LANCZOS)
    return upscaled


def _float_option(options: dict, key: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(options.get(key, default))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


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


def _save_image(image: Image.Image, output_path: Path, image_format: str, optimize_operation: bool = False) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_kwargs: dict[str, object] = {"optimize": True}

    if image_format == "JPEG":
        image = _flatten_for_jpeg(image)
        save_kwargs.update({"quality": 80 if optimize_operation else 88, "progressive": True})
    elif image_format == "PNG":
        image = image.convert("RGBA")
        save_kwargs.update({"compress_level": 9})
        if optimize_operation and image.getchannel("A").getextrema() == (255, 255):
            image = image.convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    elif image_format == "WEBP":
        save_kwargs.update({"quality": 80 if optimize_operation else 86, "method": 6})
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


def _transparency_ratio(image: Image.Image) -> float:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    histogram = alpha.histogram()
    transparent_pixels = sum(histogram[:250])
    total_pixels = max(rgba.width * rgba.height, 1)
    return transparent_pixels / total_pixels


def validate_image_file(path: Path) -> None:
    try:
        with Image.open(path) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Imagem invalida ou corrompida.") from exc
