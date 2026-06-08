from pathlib import Path
from shutil import copy2

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

from app.image_ops.common import open_oriented, save_png


def _sharpness(image: Image.Image) -> float:
    gray = cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _ensure_background_not_blurry(background: Image.Image) -> Image.Image:
    if _sharpness(background) >= 70:
        return background
    return ImageEnhance.Sharpness(background).enhance(1.8)


def prepare_background(background_path: Path, target_size: tuple[int, int]) -> Image.Image:
    background = open_oriented(background_path).convert("RGB")
    background = _ensure_background_not_blurry(background)
    target_w, target_h = target_size
    bg_w, bg_h = background.size
    scale = max(target_w / bg_w, target_h / bg_h)
    resized = background.resize((int(bg_w * scale), int(bg_h * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def _weighted_stats(rgb: np.ndarray, weight: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    weight = np.clip(weight.astype(np.float32), 0, 1)
    total = max(float(weight.sum()), 1.0)
    mean = (rgb * weight[:, :, None]).sum(axis=(0, 1)) / total
    var = (((rgb - mean.reshape(1, 1, 3)) ** 2) * weight[:, :, None]).sum(axis=(0, 1)) / total
    std = np.sqrt(np.maximum(var, 1.0))
    return mean, std


def _match_foreground_to_background(foreground: Image.Image, background: Image.Image) -> Image.Image:
    rgba = np.asarray(foreground.convert("RGBA")).astype(np.float32)
    bg = np.asarray(background.convert("RGB")).astype(np.float32)
    rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3] / 255.0
    fg_weight = alpha > 0.2
    if fg_weight.sum() < 50:
        return foreground

    ys, _ = np.where(fg_weight)
    top = int(ys.min())
    bottom = int(ys.max())
    local_y = np.indices(alpha.shape)[0]
    lower_context = local_y >= top + int((bottom - top) * 0.22)

    dilated = cv2.dilate((alpha > 0.02).astype(np.uint8), np.ones((45, 45), np.uint8), iterations=1)
    local_bg_weight = (dilated == 1) & (alpha < 0.02) & lower_context
    if local_bg_weight.sum() < 100:
        local_bg_weight = (dilated == 1) & (alpha < 0.02)
    if local_bg_weight.sum() < 100:
        local_bg_weight = alpha < 0.02

    fg_mean, fg_std = _weighted_stats(rgb, fg_weight.astype(np.float32))
    bg_mean, bg_std = _weighted_stats(bg, local_bg_weight.astype(np.float32))

    std_ratio = np.clip(bg_std / np.maximum(fg_std, 1), 0.82, 1.18)
    corrected = (rgb - fg_mean.reshape(1, 1, 3)) * std_ratio.reshape(1, 1, 3) + bg_mean.reshape(1, 1, 3)
    delta = np.clip(corrected - rgb, -48, 48)
    corrected = rgb + delta
    corrected = rgb * 0.44 + corrected * 0.56

    edge = ((alpha > 0.03) & (alpha < 0.96)).astype(np.float32)
    edge = cv2.GaussianBlur(edge, (0, 0), sigmaX=2.2, sigmaY=2.2)
    edge_mix = edge[:, :, None] * 0.50
    rgb = rgb * (1 - edge_mix) + corrected * edge_mix

    global_mix = np.clip(alpha[:, :, None] * 0.34, 0, 0.34)
    rgb = rgb * (1 - global_mix) + corrected * global_mix
    rgba[:, :, :3] = np.clip(rgb, 0, 255)
    return Image.fromarray(rgba.astype(np.uint8), mode="RGBA")


def _wrap_edge_light(foreground: Image.Image, background: Image.Image) -> Image.Image:
    rgba = np.asarray(foreground.convert("RGBA")).astype(np.float32)
    bg = np.asarray(background.convert("RGB")).astype(np.float32)
    rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3] / 255.0

    if (alpha > 0.02).sum() < 50:
        return foreground

    soft_edge = ((alpha > 0.03) & (alpha < 0.98)).astype(np.float32)
    contour = cv2.morphologyEx(
        (alpha > 0.18).astype(np.uint8),
        cv2.MORPH_GRADIENT,
        np.ones((5, 5), np.uint8),
    ).astype(np.float32)
    edge = np.clip(soft_edge + contour, 0, 1)
    edge = cv2.GaussianBlur(edge, (0, 0), sigmaX=1.8, sigmaY=1.8)
    if edge.max() <= 0:
        return foreground

    bg_blur = cv2.GaussianBlur(bg, (0, 0), sigmaX=5.0, sigmaY=5.0)
    fg_luma = rgb[:, :, 0] * 0.2126 + rgb[:, :, 1] * 0.7152 + rgb[:, :, 2] * 0.0722
    bg_luma = bg_blur[:, :, 0] * 0.2126 + bg_blur[:, :, 1] * 0.7152 + bg_blur[:, :, 2] * 0.0722
    luma_delta = np.clip(bg_luma - fg_luma, -20, 8)

    wrap_weight = np.clip(edge * alpha * 0.12, 0, 0.12)
    luma_weight = np.clip(edge * alpha * 0.26, 0, 0.26)
    rgb = (
        rgb * (1 - wrap_weight[:, :, None])
        + bg_blur * wrap_weight[:, :, None]
        + luma_delta[:, :, None] * luma_weight[:, :, None]
    )
    rgba[:, :, :3] = np.clip(rgb, 0, 255)
    return Image.fromarray(rgba.astype(np.uint8), mode="RGBA")


def composite_foreground(rgba_path: Path, background_path: Path, output_path: Path, used_background_path: Path) -> None:
    foreground = Image.open(rgba_path).convert("RGBA")
    background = prepare_background(background_path, foreground.size)
    matched_foreground = _match_foreground_to_background(foreground, background)
    matched_foreground = _wrap_edge_light(matched_foreground, background)
    result = Image.alpha_composite(background.convert("RGBA"), matched_foreground)
    save_png(result.convert("RGB"), output_path)
    used_background_path.parent.mkdir(parents=True, exist_ok=True)
    copy2(background_path, used_background_path)


def add_contact_shadow(composite_path: Path, mask_path: Path, output_path: Path) -> None:
    composite = Image.open(composite_path).convert("RGBA")
    mask = Image.open(mask_path).convert("L")
    width, height = composite.size

    alpha = np.asarray(mask).astype(np.float32) / 255.0
    foreground = alpha > 0.12
    ys, xs = np.where(foreground)
    if len(xs) == 0:
        save_png(composite.convert("RGB"), output_path)
        return

    bottom = int(ys.max())
    band_top = max(0, bottom - int(height * 0.10))
    lower_band = foreground & (np.indices(foreground.shape)[0] >= band_top)
    band_ys, band_xs = np.where(lower_band)
    if len(band_xs) < 20:
        band_xs = xs

    left = int(np.percentile(band_xs, 8))
    right = int(np.percentile(band_xs, 92))
    contact_width = max(42, right - left)
    center_x = int((left + right) / 2)
    center_y = min(height - 1, bottom + int(height * 0.018))
    ellipse_w = int(contact_width * 1.18)
    ellipse_h = max(18, int(height * 0.035))

    lower = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(lower)
    draw.ellipse(
        (
            center_x - ellipse_w // 2,
            center_y - ellipse_h // 2,
            center_x + ellipse_w // 2,
            center_y + ellipse_h // 2,
        ),
        fill=62,
    )
    lower = lower.filter(ImageFilter.GaussianBlur(radius=max(8, width // 90)))

    silhouette = mask.crop((0, int(height * 0.72), width, height))
    silhouette = silhouette.filter(ImageFilter.GaussianBlur(radius=max(12, width // 85)))
    silhouette_layer = Image.new("L", (width, height), 0)
    silhouette_layer.paste(silhouette, (0, int(height * 0.735)))
    lower = ImageChops.lighter(lower, silhouette_layer.point(lambda value: int(value * 0.05)))

    contact_alpha = np.zeros((height, width), dtype=np.float32)
    for x in np.unique(xs):
        column_ys = np.where(foreground[:, x])[0]
        if len(column_ys) == 0:
            continue
        y = int(column_ys.max())
        if y < bottom - int(height * 0.28):
            continue
        y1 = min(height, y + 1)
        y2 = min(height, y + max(3, int(height * 0.018)))
        contact_alpha[y1:y2, max(0, x - 1) : min(width, x + 2)] = 120
    contact_alpha = cv2.dilate(contact_alpha.astype(np.uint8), np.ones((3, 7), np.uint8), iterations=1)
    contact_alpha = cv2.GaussianBlur(contact_alpha, (0, 0), sigmaX=4.2, sigmaY=2.4).astype(np.float32)

    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    broad_alpha = np.asarray(lower).astype(np.float32) * 0.48
    shadow_alpha = np.maximum(broad_alpha, contact_alpha * 0.38)
    shadow_alpha *= np.clip(1 - alpha * 1.22, 0, 1)
    shadow.putalpha(Image.fromarray(np.clip(shadow_alpha, 0, 255).astype(np.uint8), mode="L"))
    base = Image.open(composite_path).convert("RGBA")
    with_shadow = Image.alpha_composite(base, shadow)
    save_png(with_shadow.convert("RGB"), output_path)


def harmonize_light(composite_path: Path, output_path: Path) -> None:
    image = Image.open(composite_path).convert("RGB")
    image = ImageEnhance.Color(image).enhance(0.96)
    image = ImageEnhance.Contrast(image).enhance(1.025)
    image = ImageEnhance.Brightness(image).enhance(0.99)
    save_png(image, output_path)
