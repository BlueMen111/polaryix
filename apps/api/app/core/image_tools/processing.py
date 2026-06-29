from __future__ import annotations

import logging
import threading
from collections import deque
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw, ImageFont, UnidentifiedImageError

from app.core.config.settings import settings


logger = logging.getLogger("polaryix.image_tools")
_rembg_sessions: dict[str, object] = {}
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

WATERMARK_OPERATIONS = {"upscale_image", "remaster_image"}

REMOVE_BACKGROUND_DEFAULTS = {
    "alpha_threshold": 8,
    "edge_smooth": 0.65,
    "remove_small_artifacts": True,
    "preserve_details": True,
    "model": "birefnet-general",
    "fallback_model": "isnet-general-use",
    "use_alpha_matting": False,
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
            result = remove_background(input_path, image, job.get("tool_options") or {})
            transparency_ratio = _transparency_ratio(result)
            if transparency_ratio < 0.005:
                raise RuntimeError("Nao foi possivel remover o fundo automaticamente nesta imagem. Tente uma imagem com maior contraste entre o objeto e o fundo.")
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
            if should_apply_watermark(job, operation):
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


def remove_background(input_path: Path, image: Image.Image, options: dict | None = None) -> Image.Image:
    rembg_remove = _get_rembg_remove()

    rgba = ImageOps.exif_transpose(image).convert("RGBA")
    settings_options = {**REMOVE_BACKGROUND_DEFAULTS, **(options or {})}
    model_name = str(settings_options.get("model") or "u2net")
    with _rembg_lock:
        session = _get_rembg_session(model_name)
        try:
            result = _run_rembg_remove(rembg_remove, rgba, session, bool(settings_options.get("use_alpha_matting", False)))
        except Exception as exc:
            fallback_model = str(settings_options.get("fallback_model") or "isnet-general-use")
            logger.warning("Remove background model %s failed; falling back to %s: %s", model_name, fallback_model, exc)
            session = _get_rembg_session(fallback_model)
            result = _run_rembg_remove(rembg_remove, rgba, session, False)
    return _post_process_background_result(rgba, result.convert("RGBA"), settings_options)


def warmup_remove_background_model() -> None:
    _get_rembg_remove()


def _get_rembg_remove():
    try:
        import onnxruntime  # noqa: F401
        from rembg import new_session, remove as rembg_remove
    except Exception as exc:
        raise RuntimeError("A remocao de fundo ainda nao esta disponivel no servidor. A dependencia rembg[cpu] precisa ser instalada.") from exc

    return rembg_remove


def _get_rembg_session(model_name: str):
    try:
        from rembg import new_session
    except Exception as exc:
        raise RuntimeError("A remocao de fundo ainda nao esta disponivel no servidor. A dependencia rembg[cpu] precisa ser instalada.") from exc

    normalized = model_name if model_name in {"u2net", "isnet-general-use", "birefnet-general", "bria-rmbg"} else "birefnet-general"
    if normalized not in _rembg_sessions:
        _rembg_sessions[normalized] = new_session(normalized)
    return _rembg_sessions[normalized]


def _run_rembg_remove(rembg_remove, image: Image.Image, session, use_alpha_matting: bool) -> Image.Image:
    if use_alpha_matting:
        try:
            return rembg_remove(
                image,
                session=session,
                alpha_matting=True,
                alpha_matting_foreground_threshold=245,
                alpha_matting_background_threshold=8,
                alpha_matting_erode_size=3,
                post_process_mask=True,
            )
        except Exception as exc:
            logger.warning("Remove background alpha matting failed; retrying without matting: %s", exc)

    return rembg_remove(
        image,
        session=session,
        alpha_matting=False,
        post_process_mask=True,
    )


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


def is_premium_user(user: dict | None) -> bool:
    if not user:
        return False

    plan = str(user.get("plan") or "").strip().lower()
    role = str(user.get("role") or "").strip().lower()
    subscription_status = str(user.get("subscription_status") or "").strip().lower()

    if role == "vip":
        return True
    if subscription_status == "active":
        return True
    if plan in {"premium", "vip", "basic", "pro"}:
        return True
    return bool(user.get("is_premium")) and plan != "free"


def should_apply_watermark(user: dict | None, operation: str) -> bool:
    normalized_operation = "upscale_image" if operation == "remaster_image" else operation
    if is_premium_user(user):
        return False
    if user and "should_apply_watermark" in user:
        return bool(user.get("should_apply_watermark")) and normalized_operation in WATERMARK_OPERATIONS
    return normalized_operation in WATERMARK_OPERATIONS


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


def _post_process_background_result(original: Image.Image, result: Image.Image, options: dict) -> Image.Image:
    alpha_threshold = int(_float_option(options, "alpha_threshold", REMOVE_BACKGROUND_DEFAULTS["alpha_threshold"], 1, 120))
    edge_smooth = _float_option(options, "edge_smooth", REMOVE_BACKGROUND_DEFAULTS["edge_smooth"], 0, 4)
    remove_small_artifacts = bool(options.get("remove_small_artifacts", REMOVE_BACKGROUND_DEFAULTS["remove_small_artifacts"]))
    preserve_details = bool(options.get("preserve_details", REMOVE_BACKGROUND_DEFAULTS["preserve_details"]))

    rgba = result.convert("RGBA")
    alpha = rgba.getchannel("A")
    if preserve_details:
        alpha = alpha.point(lambda value: 0 if value < alpha_threshold else value)
    else:
        alpha = alpha.point(lambda value: 255 if value >= alpha_threshold else 0)

    if remove_small_artifacts:
        alpha = _remove_small_alpha_components(alpha, alpha_threshold)

    if edge_smooth > 0:
        alpha = alpha.filter(ImageFilter.GaussianBlur(radius=edge_smooth))
        alpha = alpha.point(lambda value: 0 if value < max(2, alpha_threshold // 3) else value)

    cleaned = Image.new("RGBA", rgba.size)
    cleaned.paste(original.convert("RGBA"), (0, 0), alpha)
    cleaned.putalpha(alpha)
    return cleaned


def _remove_small_alpha_components(alpha: Image.Image, threshold: int) -> Image.Image:
    try:
        import numpy as np
    except Exception:
        return _remove_small_alpha_components_pillow(alpha, threshold)

    values = np.array(alpha, dtype=np.uint8)
    foreground = values >= threshold
    height, width = foreground.shape
    visited = np.zeros_like(foreground, dtype=bool)
    keep = np.zeros_like(foreground, dtype=bool)
    min_area = max(24, int(width * height * 0.00035))

    for y in range(height):
        for x in range(width):
            if not foreground[y, x] or visited[y, x]:
                continue

            component: list[tuple[int, int]] = []
            queue: deque[tuple[int, int]] = deque([(x, y)])
            visited[y, x] = True
            while queue:
                cx, cy = queue.popleft()
                component.append((cx, cy))
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < width and 0 <= ny < height and foreground[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        queue.append((nx, ny))

            if len(component) >= min_area:
                for cx, cy in component:
                    keep[cy, cx] = True

    cleaned = np.where(keep, values, 0).astype(np.uint8)
    return Image.fromarray(cleaned, mode="L")


def _remove_small_alpha_components_pillow(alpha: Image.Image, threshold: int) -> Image.Image:
    mask = alpha.point(lambda value: 255 if value >= threshold else 0)
    mask = mask.filter(ImageFilter.MedianFilter(size=3))
    return Image.composite(alpha, Image.new("L", alpha.size, 0), mask)


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
