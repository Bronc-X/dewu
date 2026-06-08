from pathlib import Path

from PIL import Image, ImageDraw
import json


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "backgrounds"


def make_background(index: int, kind: str, sit_support: bool) -> tuple[str, dict]:
    width, height = 1024, 1536
    image = Image.new("RGB", (width, height), (205, 211, 213))
    draw = ImageDraw.Draw(image)
    sky = (200, 207, 210)
    ground = (126, 133, 133) if kind != "mountain" else (118, 124, 121)
    wall = (178, 184, 186)
    draw.rectangle((0, 0, width, int(height * 0.58)), fill=sky)
    draw.rectangle((0, int(height * 0.58), width, height), fill=ground)
    if kind == "street":
        draw.rectangle((0, int(height * 0.18), width, int(height * 0.58)), fill=wall)
        for x in range(0, width, 120):
            draw.line((x, int(height * 0.58), x + 80, height), fill=(106, 112, 112), width=2)
    elif kind == "mountain":
        draw.polygon([(0, 600), (220, 390), (450, 610)], fill=(145, 152, 149))
        draw.polygon([(320, 620), (690, 340), (1024, 610)], fill=(136, 143, 141))
        draw.rectangle((0, int(height * 0.62), width, height), fill=ground)
    elif kind == "steps":
        draw.rectangle((0, 230, width, 890), fill=wall)
        for step in range(5):
            y = 760 + step * 95
            draw.rectangle((0, y, width, y + 42), fill=(155 - step * 7, 161 - step * 7, 162 - step * 7))
            draw.line((0, y, width, y), fill=(105, 111, 112), width=3)
    else:
        draw.rectangle((0, 260, width, 860), fill=wall)
        draw.rectangle((100, 790, 924, 910), fill=(145, 151, 151))
        draw.rectangle((100, 910, 924, 960), fill=(112, 118, 118))

    filename = f"B{index:02d}_{kind}.png"
    image.save(OUT / filename)
    metadata = {
        "id": f"B{index:02d}",
        "file": filename,
        "scene_type": kind,
        "pose_fit": ["sitting"] if sit_support else ["standing"],
        "sit_support": sit_support,
        "ground_type": "stone" if kind in {"mountain", "steps"} else "concrete",
        "lighting_direction": "front_left",
        "color_temperature": "cool_neutral",
        "depth_of_field": "sharp",
        "style": ["clean_ecommerce", "outdoor", kind],
        "risk_notes": ["placeholder_background"],
    }
    return filename, metadata


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plan = (
        ["street"] * 6
        + ["mountain"] * 5
        + ["steps"] * 4
        + ["mountain"] * 3
        + ["bench"] * 2
    )
    metadata = []
    for index, kind in enumerate(plan, start=1):
        sit_support = kind in {"steps", "bench"} or index in {16, 17, 18}
        _, item = make_background(index, kind, sit_support)
        metadata.append(item)
    (OUT / "backgrounds.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Created {len(metadata)} placeholder backgrounds in {OUT}")


if __name__ == "__main__":
    main()

