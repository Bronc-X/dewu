import asyncio
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.experiment_photoroom_cutout_image2_backgrounds import CodexImageClient


OUTPUT_DIR = ROOT / "app" / "web" / "static" / "generated" / "background-presets"
MANIFEST_PATH = OUTPUT_DIR / "image2_manifest.json"

THEMES = [
    (
        "01-wood",
        "Wood",
        "empty warm wood studio interior, wooden floor and wood wall details, soft daylight, clean full-body standing area in the center",
    ),
    (
        "02-minimalist",
        "Minimalist",
        "empty minimalist premium studio, warm off-white wall, pale gray floor, subtle tonal gradient and soft contact shadow zone",
    ),
    (
        "03-snow",
        "Snow",
        "empty snowy outdoor lifestyle scene, clean snow ground, soft overcast daylight, gentle winter texture, clear central standing area",
    ),
    (
        "04-monstera",
        "Monstera",
        "empty bright botanical interior, monstera leaves and potted greenery near both sides, cream wall, clean floor in the center",
    ),
    (
        "05-stone-countertop",
        "Stone countertop",
        "empty refined stone studio set, light stone floor or platform and warm wall, subtle stone texture, soft daylight",
    ),
    (
        "06-kitchen-countertop",
        "Kitchen countertop",
        "empty modern kitchen-inspired studio set, muted cabinets in background, clean stone surface and floor plane, natural daylight",
    ),
    (
        "07-wood-countertop",
        "Wood countertop",
        "empty warm wood surface studio, wooden platform and neutral wall, soft side light, clear contact shadow area",
    ),
    (
        "08-indoor-plant",
        "Indoor plant",
        "empty sunlit indoor plant corner, potted greenery near sides, warm neutral wall, clean central floor area",
    ),
    (
        "09-soil",
        "Soil",
        "empty earthy editorial studio, soil-toned textured ground and backdrop, warm natural light, clean central standing area",
    ),
    (
        "10-marble",
        "Marble",
        "empty elegant marble studio, light marble wall and floor with delicate gray veining, soft commercial lighting",
    ),
    (
        "11-sand-dunes",
        "Sand dunes",
        "empty desert sand dunes fashion ecommerce scene, low-saturation dunes, warm natural light, flat foreground for standing model",
    ),
    (
        "12-mountain-sunset",
        "Mountain sunset",
        "empty mountain sunset fashion campaign scene, distant mountains, warm soft rim light, clean flat foreground platform",
    ),
    (
        "13-tulip-studio",
        "Tulip studio",
        "empty bright flower studio, tulips near edges, soft cream wall, clean central floor area, fresh daylight",
    ),
    (
        "14-garden-flowers",
        "Garden flowers",
        "empty refined garden flower lifestyle scene, soft depth of field flowers around sides, natural daylight, clear standing space",
    ),
    (
        "15-floral-wall",
        "Floral wall",
        "empty subtle floral wall studio, gentle color accents, clean ecommerce subject space, soft shadow on floor",
    ),
    (
        "16-graffiti",
        "Graffiti",
        "empty tasteful urban graffiti wall scene, realistic concrete floor, colorful wall behind the subject area, soft daylight",
    ),
]


def prompt_for(label: str, scene: str) -> str:
    return (
        "Create a photorealistic ecommerce AI background preset preview for replacing the background behind a full-body fashion model. "
        "The image must clearly show the real scene that will be applied, not an abstract mood board and not a diagram. "
        "Leave a clean central negative-space area where a cutout model can stand naturally. "
        "Include a believable floor or ground plane with realistic perspective and a subtle contact-shadow area. "
        "No person, no mannequin, no product, no text, no logo, no watermark. "
        "Do not use UI labels or decorative frames inside the image. "
        "Style should feel like PhotoRoom AI Background preset thumbnails: clean, premium, commercial, practical. "
        f"Theme: {label}. Scene: {scene}."
    )


def save_webp(source: Path, destination: Path) -> None:
    with Image.open(source) as image:
        image = image.convert("RGB")
        width, height = image.size
        side = min(width, height)
        left = (width - side) // 2
        top = max(0, (height - side) // 2)
        image = image.crop((left, top, left + side, top + side))
        image = image.resize((420, 420), Image.Resampling.LANCZOS)
        image.save(destination, "WEBP", quality=82, method=6)


async def generate_one(client: CodexImageClient, slug: str, label: str, scene: str) -> dict:
    png_path = OUTPUT_DIR / f"{slug}.png"
    webp_path = OUTPUT_DIR / f"{slug}.webp"
    if png_path.exists() and png_path.stat().st_size > 100_000:
        save_webp(png_path, webp_path)
        return {"slug": slug, "label": label, "status": "existing", "png": str(png_path), "webp": str(webp_path)}

    last_error = ""
    for attempt in range(1, 7):
        try:
            print(f"[{slug}] image-2 attempt {attempt}", flush=True)
            result = await client.generate_background(prompt_for(label, scene), png_path)
            save_webp(png_path, webp_path)
            return {
                "slug": slug,
                "label": label,
                "status": "generated",
                "png": str(png_path),
                "webp": str(webp_path),
                "result": result,
            }
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            print(f"[{slug}] failed attempt {attempt}: {last_error}", flush=True)
            await asyncio.sleep(min(45, attempt * 8))
    return {"slug": slug, "label": label, "status": "failed", "error": last_error}


async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = CodexImageClient(model="gpt-image-2", quality="medium")
    results = []
    for slug, label, scene in THEMES:
        result = await generate_one(client, slug, label, scene)
        results.append(result)
        MANIFEST_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    failures = [item for item in results if item["status"] == "failed"]
    if failures:
        raise SystemExit(f"{len(failures)} image-2 generations failed. See {MANIFEST_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
