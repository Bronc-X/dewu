import json
from pathlib import Path

from app.config import settings
from app.models import BackgroundMeta


def _chair_safe_backgrounds(backgrounds: list[BackgroundMeta]) -> list[BackgroundMeta]:
    return [
        bg
        for bg in backgrounds
        if "safe_for_existing_chair" in bg.risk_notes
        and "sitting" in bg.pose_fit
        and bg.scene_type == "street"
        and bg.depth_of_field == "sharp"
    ]


def load_backgrounds() -> list[BackgroundMeta]:
    metadata_path = settings.background_dir / "backgrounds.json"
    if not metadata_path.exists():
        return []
    raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    return [BackgroundMeta.model_validate(item) for item in raw]


def choose_background(
    backgrounds: list[BackgroundMeta],
    pose: str,
    risk_tags: list[str],
    index: int,
    used_background_ids: list[str] | None = None,
) -> BackgroundMeta:
    if not backgrounds:
        raise FileNotFoundError("背景库为空，请先生成背景图和 backgrounds.json。")

    if pose == "sitting":
        candidates = [
            bg
            for bg in backgrounds
            if bg.sit_support and "sitting" in bg.pose_fit and bg.depth_of_field == "sharp"
        ]
        if {"seated_support", "transparent_prop", "hand_prop"} & set(risk_tags):
            support_safe = _chair_safe_backgrounds(backgrounds) or [
                bg
                for bg in backgrounds
                if "standing" in bg.pose_fit
                and bg.scene_type == "street"
                and bg.depth_of_field == "sharp"
            ]
            candidates = support_safe or candidates
        stable_sitting = [
            bg
            for bg in candidates
            if "floating_risk" not in bg.risk_notes and bg.id != "B04"
        ]
        candidates = stable_sitting or candidates
    else:
        candidates = [
            bg
            for bg in backgrounds
            if "standing" in bg.pose_fit and bg.depth_of_field == "sharp"
        ]
        clean_generated = [
            bg
            for bg in candidates
            if "safe_for_existing_chair" in bg.risk_notes
        ]
        candidates = clean_generated or candidates

    if {"transparent_prop", "hand_prop"} & set(risk_tags):
        stable = _chair_safe_backgrounds(backgrounds) or [
            bg
            for bg in candidates
            if bg.ground_type in {"concrete", "stone"} and bg.depth_of_field == "sharp"
        ]
        candidates = stable or candidates

    if "white_screen_edge" in risk_tags:
        preferred = [
            bg
            for bg in candidates
            if bg.scene_type in {"steps", "bench", "street"} and bg.color_temperature == "cool_neutral"
        ]
        candidates = preferred or candidates

    if not candidates:
        candidates = backgrounds
    used_counts = {bg.id: 0 for bg in candidates}
    for bg_id in used_background_ids or []:
        if bg_id in used_counts:
            used_counts[bg_id] += 1
    min_used = min(used_counts.values())
    least_used = sorted(
        [bg for bg in candidates if used_counts.get(bg.id, 0) == min_used],
        key=lambda bg: bg.id,
    )
    if len(least_used) == len(candidates):
        return least_used[(index - 1) % len(least_used)]
    return least_used[0]


def background_path(meta: BackgroundMeta) -> Path:
    return settings.background_dir / meta.file
