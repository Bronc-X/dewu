from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.image_ops.common import open_oriented, resize_to_long_edge, save_png


def detect_screen_type(input_path: Path) -> str:
    image = resize_to_long_edge(open_oriented(input_path).convert("RGB"))
    rgb = np.asarray(image).astype(np.float32)
    screen = _estimate_screen_color(rgb)
    screen_red, screen_green, screen_blue = screen
    if screen_green > screen_red * 1.15 and screen_green > screen_blue * 1.15:
        return "green"
    if screen.mean() > 205 and (screen.max() - screen.min()) < 24:
        return "white"
    return "unsupported"


def _smoothstep(edge0: float, edge1: float, value: np.ndarray) -> np.ndarray:
    x = np.clip((value - edge0) / max(edge1 - edge0, 1e-6), 0, 1)
    return x * x * (3 - 2 * x)


def _estimate_screen_color(rgb: np.ndarray) -> np.ndarray:
    height, width, _ = rgb.shape
    border = max(10, min(height, width) // 20)
    samples = np.concatenate(
        [
            rgb[:border, :, :].reshape(-1, 3),
            rgb[-border:, :, :].reshape(-1, 3),
            rgb[:, :border, :].reshape(-1, 3),
            rgb[:, -border:, :].reshape(-1, 3),
        ],
        axis=0,
    )
    return np.median(samples, axis=0)


def _remove_tiny_foreground(alpha: np.ndarray) -> np.ndarray:
    hard = (alpha > 32).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(hard, connectivity=8)
    if count <= 1:
        return alpha
    image_area = alpha.shape[0] * alpha.shape[1]
    keep = np.zeros_like(hard)
    for label in range(1, count):
        area = stats[label, cv2.CC_STAT_AREA]
        width = stats[label, cv2.CC_STAT_WIDTH]
        height = stats[label, cv2.CC_STAT_HEIGHT]
        slender = max(width, height) > 120 and min(width, height) < 18
        if area > image_area * 0.00035 or slender:
            keep[labels == label] = 1
    return (alpha * keep).astype(np.uint8)


def _keep_only_border_connected_background(background_score: np.ndarray, threshold: float) -> np.ndarray:
    hard_background = (background_score > threshold).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(hard_background, connectivity=8)
    if count <= 1:
        return background_score

    border_labels = np.unique(
        np.concatenate(
            [
                labels[0, :],
                labels[-1, :],
                labels[:, 0],
                labels[:, -1],
            ]
        )
    )
    image_area = background_score.shape[0] * background_score.shape[1]
    protect_hole = np.zeros_like(hard_background, dtype=bool)
    for label in range(1, count):
        if label in border_labels:
            continue
        area = stats[label, cv2.CC_STAT_AREA]
        if area <= image_area * 0.0035:
            protect_hole[labels == label] = True

    capped = np.minimum(background_score, 0.18)
    return np.where(protect_hole, capped, background_score)


def _grabcut_refine(image_bgr: np.ndarray, background_score: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    mask = np.full(alpha.shape, cv2.GC_PR_FGD, dtype=np.uint8)
    mask[background_score > 0.82] = cv2.GC_BGD
    mask[background_score > 0.62] = cv2.GC_PR_BGD
    mask[background_score < 0.16] = cv2.GC_FGD

    height, width = alpha.shape
    border = max(6, min(height, width) // 80)
    mask[:border, :] = cv2.GC_BGD
    mask[-border:, :] = cv2.GC_BGD
    mask[:, :border] = cv2.GC_BGD
    mask[:, -border:] = cv2.GC_BGD

    bg_model = np.zeros((1, 65), np.float64)
    fg_model = np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(image_bgr, mask, None, bg_model, fg_model, 2, cv2.GC_INIT_WITH_MASK)
    except cv2.error:
        return alpha

    foreground = (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)
    refined = alpha.copy()
    refined[~foreground] = np.minimum(refined[~foreground], 12)
    refined[(mask == cv2.GC_FGD) & (refined > 80)] = 255
    return refined


def create_alpha_matte(input_path: Path, rgba_path: Path, mask_path: Path) -> None:
    image = resize_to_long_edge(open_oriented(input_path).convert("RGB"))
    rgb = np.asarray(image).astype(np.float32)
    screen = _estimate_screen_color(rgb)
    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    screen_red, screen_green, screen_blue = screen
    screen_is_green = screen_green > screen_red * 1.15 and screen_green > screen_blue * 1.15
    screen_is_white = screen.mean() > 205 and (screen.max() - screen.min()) < 24

    color_distance = np.linalg.norm(rgb - screen.reshape(1, 1, 3), axis=2)
    if screen_is_green:
        dominance = green - np.maximum(red, blue)
        green_similarity = _smoothstep(12, 92, dominance)
        color_similarity = 1 - _smoothstep(28, 118, color_distance)
        background_score = np.clip(green_similarity * 0.62 + color_similarity * 0.55, 0, 1)
    elif screen_is_white:
        brightness = rgb.mean(axis=2)
        chroma = rgb.max(axis=2) - rgb.min(axis=2)
        white_similarity = _smoothstep(195, 245, brightness) * (1 - _smoothstep(14, 48, chroma))
        color_similarity = 1 - _smoothstep(18, 78, color_distance)
        background_score = np.clip(white_similarity * 0.68 + color_similarity * 0.48, 0, 1)
    else:
        color_similarity = 1 - _smoothstep(32, 128, color_distance)
        background_score = np.clip(color_similarity, 0, 1)

    background_score = _keep_only_border_connected_background(background_score, threshold=0.52)
    alpha = ((1 - background_score) * 255).astype(np.uint8)
    alpha = cv2.medianBlur(alpha, 5)
    alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1)
    alpha = _remove_tiny_foreground(alpha)

    image_bgr = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2BGR)
    alpha = _grabcut_refine(image_bgr, background_score, alpha)
    alpha = np.where(alpha > 235, 255, alpha)
    alpha = np.where(alpha < 22, 0, alpha)
    fg_core = cv2.erode((alpha > 210).astype(np.uint8), np.ones((7, 7), np.uint8), iterations=1).astype(bool)
    alpha[fg_core] = 255

    soft = cv2.bilateralFilter(alpha, d=7, sigmaColor=36, sigmaSpace=6)
    confident_fg = alpha > 246
    confident_bg = alpha < 6
    alpha = np.where(confident_fg, 255, np.where(confident_bg, 0, soft)).astype(np.uint8)
    alpha = cv2.GaussianBlur(alpha, (0, 0), sigmaX=0.85, sigmaY=0.85)

    rgba = image.convert("RGBA")
    rgba.putalpha(Image.fromarray(alpha, mode="L"))
    save_png(rgba, rgba_path)
    save_png(Image.fromarray(alpha, mode="L"), mask_path)
