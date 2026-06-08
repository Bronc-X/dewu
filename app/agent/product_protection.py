from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from app.config import settings


def estimate_product_change_score(original_path: Path, final_path: Path, mask_path: Path) -> float:
    """Return a lightweight difference score for protected foreground pixels.

    v0 uses this as a conservative local guard. A real production version should
    replace or augment this with product-specific visual comparison.
    """
    original = Image.open(original_path).convert("RGB")
    final = Image.open(final_path).convert("RGB").resize(original.size)
    mask = Image.open(mask_path).convert("L").resize(original.size)

    diff = ImageChops.difference(original, final)
    masked = Image.composite(diff, Image.new("RGB", original.size), mask)
    stat = ImageStat.Stat(masked)
    mask_stat = ImageStat.Stat(mask)
    mask_mean = mask_stat.mean[0] / 255
    if mask_mean <= 0:
        return 0
    return sum(stat.mean) / 3 / max(mask_mean, 0.01)


def protect_candidate_or_revert(
    original_path: Path,
    candidate_path: Path,
    fallback_path: Path,
    mask_path: Path,
    output_path: Path,
) -> tuple[Path, dict]:
    """Keep a local/model-edited candidate only when protected pixels stay stable."""
    candidate_score = estimate_product_change_score(original_path, candidate_path, mask_path)
    fallback_score = estimate_product_change_score(original_path, fallback_path, mask_path)
    reverted = candidate_score > settings.product_change_fail_threshold
    selected = fallback_path if reverted else candidate_path
    if selected != output_path:
        output_path.write_bytes(selected.read_bytes())
        selected = output_path
    return selected, {
        "name": "product_protection",
        "candidate_score": round(candidate_score, 2),
        "fallback_score": round(fallback_score, 2),
        "review_threshold": settings.product_change_review_threshold,
        "fail_threshold": settings.product_change_fail_threshold,
        "reverted": reverted,
        "selected": "fallback" if reverted else "candidate",
    }
