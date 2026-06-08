from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.image_ops.common import save_png


def remove_green_spill(rgba_path: Path, output_path: Path) -> None:
    image = Image.open(rgba_path).convert("RGBA")
    array = np.asarray(image).astype(np.float32)
    red = array[:, :, 0]
    green = array[:, :, 1]
    blue = array[:, :, 2]
    alpha = array[:, :, 3]

    edge = ((alpha > 4) & (alpha < 252)).astype(np.uint8)
    edge = cv2.dilate(edge, np.ones((5, 5), np.uint8), iterations=1).astype(bool)
    green_spill = edge & (green > red * 1.03) & (green > blue * 1.03)
    neutral_green = (red * 0.52 + blue * 0.48)
    array[:, :, 1] = np.where(green_spill, green * 0.28 + neutral_green * 0.72, green)

    rgb = array[:, :, :3]
    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    saturation = maxc - minc
    white_edge = edge & (maxc > 210) & (saturation < 28)
    mean = rgb.mean(axis=2, keepdims=True)
    rgb = np.where(white_edge[:, :, None], rgb * 0.82 + mean * 0.18, rgb)
    array[:, :, :3] = rgb

    array = np.clip(array, 0, 255).astype(np.uint8)
    save_png(Image.fromarray(array, mode="RGBA"), output_path)
