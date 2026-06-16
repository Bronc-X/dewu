import argparse
import asyncio
import base64
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.api_clients.image_api import ImageApiClient
from app.api_clients.errors import ProviderError
from app.api_clients.photoroom import PhotoRoomClient
from app.config import settings
from app.image_ops.compose import add_contact_shadow, composite_foreground, harmonize_light
from app.image_ops.despill import remove_green_spill


DEFAULT_INPUT_DIR = (
    ROOT
    / "data"
    / "client_batches"
    / "2026-06-14_photoroom_50_v4"
    / "07_delivery"
    / "manual_test_10_from_link_raw"
)
DEFAULT_OUTPUT_DIR = ROOT / "data" / "experiments" / "2026-06-15_photoroom_cutout_image2"
CODEX_CONFIG_PATH = Path.home() / ".codex" / "config.toml"
CODEX_AUTH_PATH = Path.home() / ".codex" / "auth.json"

THEMES = [
    (
        "wood",
        "A warm wood-toned minimalist ecommerce studio background for a fashion model, "
        "natural soft daylight, subtle wall-floor transition, realistic ground contact area, "
        "gentle shadows, clean commercial style, no people, no product, no text, no logo.",
    ),
    (
        "minimalist",
        "A clean minimalist studio background for fashion ecommerce, soft off-white and pale "
        "warm gray tones, gentle same-color gradient, realistic floor plane, subtle shadows, "
        "large negative space, no people, no product, no text, no logo.",
    ),
    (
        "monstera",
        "A bright modern indoor background with large monstera leaves and tasteful potted "
        "green plants near the sides, soft window light, clean floor, realistic contact area, "
        "commercial fashion catalog style, no people, no product, no text, no logo.",
    ),
    (
        "countertop",
        "A clean neutral countertop and wall background adapted for fashion ecommerce, subtle "
        "stone texture, warm natural light, realistic floor/contact plane, soft shadows, "
        "uncluttered composition, no people, no product, no text, no logo.",
    ),
    (
        "plant",
        "A calm plant-filled indoor ecommerce background with potted greenery, soft natural "
        "window light, neutral wall, clean floor, realistic contact shadows, no people, no "
        "product, no text, no logo.",
    ),
    (
        "marble",
        "A polished light marble studio background with delicate gray veining, soft commercial "
        "lighting, realistic floor plane, gentle shadow gradient, elegant but uncluttered, no "
        "people, no product, no text, no logo.",
    ),
    (
        "sand_dunes",
        "A low-saturation desert sand dunes fashion ecommerce background, warm natural light, "
        "subtle distant dunes, clean flat foreground area for shoes, realistic shadows, no "
        "people, no product, no text, no logo.",
    ),
    (
        "mountain_sunset",
        "A restrained mountain sunset fashion ecommerce background, soft golden light, distant "
        "mountains, clean flat foreground platform, realistic contact shadows, not dramatic, "
        "no people, no product, no text, no logo.",
    ),
    (
        "flower",
        "An elegant floral ecommerce background with fresh flowers arranged near the sides and "
        "floor, soft pastel colors, clean central negative space, natural light, realistic "
        "ground contact, no people, no product, no text, no logo.",
    ),
    (
        "graffiti",
        "A clean urban graffiti wall fashion ecommerce background, colorful street art kept "
        "behind the subject, neutral concrete floor, soft daylight, realistic contact shadows, "
        "no people, no product, no readable text, no logo.",
    ),
]


class CodexImageClient:
    def __init__(self, *, model: str, quality: str) -> None:
        auth = json.loads(CODEX_AUTH_PATH.read_text(encoding="utf-8"))
        self.api_key = auth["OPENAI_API_KEY"]
        self.base_url = self._codex_base_url()
        self.model = model
        self.quality = quality

    def enabled(self) -> bool:
        return bool(self.api_key and self.base_url)

    async def generate_background(self, prompt: str, output_path: Path) -> dict:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1536",
            "quality": self.quality,
            "output_format": "png",
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        last_error = ""
        async with httpx.AsyncClient(timeout=240) as client:
            for attempt in range(1, 4):
                response = await client.post(
                    f"{self.base_url.rstrip('/')}/images/generations",
                    headers=headers,
                    json=payload,
                )
                if response.status_code < 500:
                    response.raise_for_status()
                    data = response.json()
                    item = data["data"][0]
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    if "b64_json" in item:
                        output_path.write_bytes(base64.b64decode(item["b64_json"]))
                    elif "url" in item:
                        image_response = await client.get(item["url"])
                        image_response.raise_for_status()
                        output_path.write_bytes(image_response.content)
                    else:
                        raise RuntimeError("Image response had no b64_json or url.")
                    break
                last_error = f"{response.status_code} {response.text[:500]}"
                if attempt == 3:
                    response.raise_for_status()
                await asyncio.sleep(2 * attempt)
            else:
                raise RuntimeError(f"Image generation failed: {last_error}")

        return {
            "provider": "codex_auth_image_api",
            "purpose": "generate_background",
            "output": str(output_path),
            "used_external_api": True,
            "base_url": self.base_url,
            "model": self.model,
            "quality": self.quality,
            "revised_prompt": item.get("revised_prompt", ""),
        }

    def _codex_base_url(self) -> str:
        text = CODEX_CONFIG_PATH.read_text(encoding="utf-8")
        active_provider = ""
        base_url = ""
        in_active_provider = False
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if line.startswith("model_provider"):
                active_provider = line.split("=", 1)[1].strip().strip('"')
            elif active_provider and line == f"[model_providers.{active_provider}]":
                in_active_provider = True
            elif line.startswith("[") and line.endswith("]"):
                in_active_provider = False
            elif in_active_provider and line.startswith("base_url"):
                base_url = line.split("=", 1)[1].strip().strip('"')
                break
        if not base_url:
            raise RuntimeError(f"Could not find base_url for active Codex provider {active_provider!r}.")
        return base_url


def source_images(input_dir: Path, limit: int) -> list[Path]:
    images = [
        path
        for path in sorted(input_dir.iterdir())
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    ]
    return images[:limit]


async def remove_background_with_retries(
    photoroom: PhotoRoomClient,
    image_path: Path,
    cutout_path: Path,
    alpha_path: Path,
) -> dict:
    for attempt in range(1, 4):
        try:
            return await photoroom.remove_background(image_path, cutout_path, alpha_path)
        except ProviderError:
            if attempt == 3:
                raise
            await asyncio.sleep(2 * attempt)
    raise RuntimeError("unreachable")


async def process_one(
    index: int,
    image_path: Path,
    theme: tuple[str, str],
    output_dir: Path,
    image_client,
) -> dict:
    theme_name, prompt = theme
    stem = f"{index:02d}_{Path(image_path).stem}_{theme_name}"
    cutout_path = output_dir / "01_cutouts" / f"{stem}_cutout.png"
    alpha_path = output_dir / "01_cutouts" / f"{stem}_alpha.png"
    despill_path = output_dir / "02_despill" / f"{stem}_despill.png"
    background_path = output_dir / "03_backgrounds" / f"{stem}_background.png"
    composite_path = output_dir / "04_composites" / f"{stem}_composite.png"
    harmonized_path = output_dir / "04_composites" / f"{stem}_harmonized.png"
    final_path = output_dir / "05_final" / f"{stem}_final.png"
    used_bg_path = output_dir / "06_background_used" / f"{stem}_background.png"

    photoroom = PhotoRoomClient()
    if cutout_path.exists() and alpha_path.exists():
        cutout_call = {
            "provider": "photoroom",
            "purpose": "remove_background",
            "input": str(image_path),
            "output": str(cutout_path),
            "alpha": str(alpha_path),
            "cached": True,
        }
    else:
        cutout_call = await remove_background_with_retries(
            photoroom,
            image_path,
            cutout_path,
            alpha_path,
        )

    if not despill_path.exists():
        remove_green_spill(cutout_path, despill_path)

    if background_path.exists():
        background_call = {
            "provider": "openai_compatible",
            "purpose": "generate_background",
            "output": str(background_path),
            "cached": True,
        }
    else:
        background_call = await image_client.generate_background(prompt, background_path)
    composite_foreground(despill_path, background_path, composite_path, used_bg_path)
    harmonize_light(composite_path, harmonized_path)
    add_contact_shadow(harmonized_path, alpha_path, final_path)

    return {
        "index": index,
        "input": str(image_path),
        "theme": theme_name,
        "prompt": prompt,
        "cutout": str(cutout_path),
        "alpha": str(alpha_path),
        "background": str(background_path),
        "final": str(final_path),
        "calls": [cutout_call, background_call],
    }


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Experiment: PhotoRoom cutout + Image API background + local composite."
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--model", default="gpt-image-2")
    parser.add_argument("--quality", default="medium")
    parser.add_argument(
        "--use-codex-auth",
        action="store_true",
        help="Use ~/.codex/auth.json and the active Codex provider base_url for image generation.",
    )
    parser.add_argument(
        "--background-provider",
        default="openai_compatible",
        choices=["openai_compatible", "local", "adobe_firefly"],
        help="Provider used by ImageApiClient for background generation.",
    )
    args = parser.parse_args()

    if args.use_codex_auth:
        image_client = CodexImageClient(model=args.model, quality=args.quality)
    else:
        settings.background_provider = args.background_provider
        settings.image_model = args.model
        settings.image_quality = args.quality
        image_client = ImageApiClient()
    if not image_client.enabled():
        raise RuntimeError(
            "Image background generation is not configured. Set OPENAI_API_KEY or "
            "IMAGE_API_KEY for openai_compatible/local, or configure Adobe Firefly."
        )

    images = source_images(args.input_dir, args.limit)
    if not images:
        raise FileNotFoundError(f"No images found in {args.input_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for index, image_path in enumerate(images, start=1):
        theme = THEMES[(index - 1) % len(THEMES)]
        print(f"[{index}/{len(images)}] {image_path.name} -> {theme[0]}", flush=True)
        results.append(await process_one(index, image_path, theme, args.output_dir, image_client))

    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Done: {manifest_path}")


if __name__ == "__main__":
    asyncio.run(main())
