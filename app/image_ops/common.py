from pathlib import Path

from PIL import Image, ImageOps

from app.config import settings


def open_oriented(path: Path) -> Image.Image:
    return ImageOps.exif_transpose(Image.open(path))


def resize_to_long_edge(image: Image.Image, long_edge: int | None = None) -> Image.Image:
    long_edge = long_edge or settings.processing_long_edge
    width, height = image.size
    current = max(width, height)
    if current <= long_edge:
        return image.copy()
    scale = long_edge / current
    return image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)


def save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)

