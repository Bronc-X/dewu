import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.api_clients.image_api import ImageApiClient
from app.config import settings


PROMPTS = {
    "street": (
        "Create a photorealistic vertical 2:3 clean commercial ecommerce outdoor background. "
        "Empty urban concrete floor with a neutral cool gray wall, soft overcast daylight, "
        "central negative space for a full-body fashion model. No people, no products, no text, "
        "no logos, no signs, no vehicles near the center, no watermark. Sharp or mild depth of "
        "field only, not overly blurred. The foreground floor must be clear, flat, and suitable "
        "for realistic shoe contact shadows. Cool gray low-saturation palette, clean streetwear "
        "ecommerce look."
    ),
    "mountain": (
        "Create a photorealistic vertical 2:3 clean commercial ecommerce outdoor background. "
        "Empty stone platform or flat rock ground in a low-saturation mountain outdoor setting, "
        "soft overcast daylight, cool gray tone. Leave central negative space for a full-body "
        "fashion model. No people, no products, no text, no logos, no watermark. The foreground "
        "must have a clear flat contact area for shoes, with mild background depth only. Avoid "
        "dramatic landscape, strong fog, strong backlight, or fantasy mood."
    ),
    "steps": (
        "Create a photorealistic vertical 2:3 clean commercial ecommerce outdoor background. "
        "Modern outdoor concrete steps or stone steps, cool gray tone, soft natural daylight. "
        "The center must have a clear sitting surface and clean floor/contact area for compositing "
        "a seated fashion model. No people, no products, no text, no logos, no watermark. No clutter, "
        "no strong shadows, no dramatic perspective. Commercial fashion ecommerce style, clean and realistic."
    ),
    "bench": (
        "Create a photorealistic vertical 2:3 clean commercial ecommerce outdoor background. "
        "Minimal outdoor low wall or simple bench with a clear sitting surface, cool gray low-saturation "
        "palette, soft overcast daylight. Leave central space for a seated fashion model. No people, "
        "no products, no text, no logos, no watermark. The ground must be clean and suitable for contact "
        "shadows. Avoid ornate furniture, strong branding, busy streets, or heavy blur."
    ),
}


def metadata_item(index: int, kind: str, filename: str) -> dict:
    sit_support = kind in {"steps", "bench"} or index in {16, 17, 18}
    scene_level = {
        "street": "L1_product_safe",
        "steps": "L2_pose_matched",
        "bench": "L2_pose_matched",
        "mountain": "L3_contextual",
    }.get(kind, "L1_product_safe")
    priority = {
        "street": 10,
        "steps": 20,
        "bench": 25,
        "mountain": 35,
    }.get(kind, 50)
    return {
        "id": f"B{index:02d}",
        "file": filename,
        "scene_type": kind,
        "scene_level": scene_level,
        "priority": priority,
        "pose_fit": ["sitting"] if sit_support else ["standing"],
        "sit_support": sit_support,
        "ground_type": "stone" if kind in {"mountain", "steps"} else "concrete",
        "lighting_direction": "front_left",
        "color_temperature": "cool_neutral",
        "depth_of_field": "sharp",
        "style": ["clean_ecommerce", "outdoor", kind],
        "risk_notes": [],
    }


async def main() -> None:
    client = ImageApiClient()
    if not client.enabled():
        raise RuntimeError("请先在 .env 中填写 OPENAI_API_KEY 或 IMAGE_API_KEY。")
    settings.background_dir.mkdir(parents=True, exist_ok=True)
    plan = (
        ["street"] * 6
        + ["mountain"] * 5
        + ["steps"] * 4
        + ["mountain"] * 3
        + ["bench"] * 2
    )
    metadata = []
    for index, kind in enumerate(plan, start=1):
        filename = f"B{index:02d}_{kind}.png"
        output = settings.background_dir / filename
        prompt = PROMPTS[kind] + f" Variation number {index}, keep it commercially usable and uncluttered."
        print(f"Generating {filename}...")
        await client.generate_background(prompt, output)
        metadata.append(metadata_item(index, kind, filename))
    (settings.background_dir / "backgrounds.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Generated {len(metadata)} backgrounds in {settings.background_dir}")


if __name__ == "__main__":
    asyncio.run(main())
