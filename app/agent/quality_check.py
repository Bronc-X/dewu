from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageStat

from app.agent.product_protection import estimate_product_change_score
from app.config import settings
from app.models import BackgroundMeta, ItemStatus


def _edge_mask(alpha: Image.Image) -> Image.Image:
    return alpha.point(lambda value: 255 if 8 < value < 245 else 0)


def _edge_spill_score(rgba_path: Path) -> float:
    image = Image.open(rgba_path).convert("RGBA")
    rgb = image.convert("RGB")
    alpha = image.getchannel("A")
    edge = _edge_mask(alpha)
    if ImageStat.Stat(edge).mean[0] < 0.4:
        return 0
    masked = Image.composite(rgb, Image.new("RGB", image.size), edge)
    stat = ImageStat.Stat(masked)
    red, green, blue = stat.mean
    return max(0.0, green - max(red, blue))


def _edge_softness_score(mask_path: Path) -> tuple[float, float]:
    alpha = np.asarray(Image.open(mask_path).convert("L")).astype(np.float32)
    transitional = ((alpha > 8) & (alpha < 245)).mean() * 100
    hard_edges = cv2.Canny(alpha.astype(np.uint8), 40, 140).mean() / 255 * 100
    return transitional, hard_edges


def _foreground_background_luma_gap(final_path: Path, mask_path: Path) -> float:
    final = np.asarray(Image.open(final_path).convert("RGB")).astype(np.float32)
    alpha = np.asarray(Image.open(mask_path).convert("L")).astype(np.float32) / 255
    luma = final[:, :, 0] * 0.2126 + final[:, :, 1] * 0.7152 + final[:, :, 2] * 0.0722
    fg_edge = cv2.dilate((alpha > 0.05).astype(np.uint8), np.ones((23, 23), np.uint8), iterations=1).astype(bool) & (alpha > 0.55)
    bg_near = cv2.dilate((alpha > 0.05).astype(np.uint8), np.ones((65, 65), np.uint8), iterations=1).astype(bool) & (alpha < 0.02)
    if fg_edge.sum() < 50:
        fg_edge = alpha > 0.65
    if fg_edge.sum() < 50 or bg_near.sum() < 50:
        return 0
    return float(abs(luma[fg_edge].mean() - luma[bg_near].mean()))


def _background_blur_score(final_path: Path, mask_path: Path) -> float:
    final = np.asarray(Image.open(final_path).convert("RGB"))
    alpha = np.asarray(Image.open(mask_path).convert("L")) / 255
    bg = alpha < 0.02
    if bg.mean() < 0.1:
        return 999
    gray = cv2.cvtColor(final, cv2.COLOR_RGB2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return float(np.var(lap[bg]))


def _hair_edge_luma_gap(final_path: Path, mask_path: Path) -> float:
    final = np.asarray(Image.open(final_path).convert("RGB")).astype(np.float32)
    alpha = np.asarray(Image.open(mask_path).convert("L")).astype(np.float32) / 255
    height = alpha.shape[0]
    edge = (alpha > 0.04) & (alpha < 0.92)
    upper_edge = edge.copy()
    upper_edge[int(height * 0.55):, :] = False
    if upper_edge.sum() < 30:
        upper_edge = edge
    around = cv2.dilate(edge.astype(np.uint8), np.ones((23, 23), np.uint8), iterations=1).astype(bool) & (alpha < 0.02)
    if upper_edge.sum() < 30 or around.sum() < 30:
        return 0
    luma = final[:, :, 0] * 0.2126 + final[:, :, 1] * 0.7152 + final[:, :, 2] * 0.0722
    return float(abs(luma[upper_edge].mean() - luma[around].mean()))


def evaluate_result(
    original_path: Path,
    final_path: Path,
    rgba_path: Path,
    mask_path: Path,
    background: BackgroundMeta,
    pose: str,
    support_required: bool,
    support_kept: bool,
) -> tuple[ItemStatus, str, str, list[str]]:
    risk_tags: list[str] = []
    reasons: list[str] = []
    suggestions: list[str] = []

    product_change = estimate_product_change_score(original_path, final_path, mask_path)
    spill_score = _edge_spill_score(rgba_path)
    transitional_alpha, hard_edge_score = _edge_softness_score(mask_path)
    luma_gap = _foreground_background_luma_gap(final_path, mask_path)
    blur_score = _background_blur_score(final_path, mask_path)
    hair_gap = _hair_edge_luma_gap(final_path, mask_path)

    if product_change > settings.product_change_fail_threshold:
        risk_tags.append("product_changed")
        reasons.append("商品区域与原图差异偏大，鞋型、衣服图案或 Logo 可能被处理影响。")
        suggestions.append("建议使用更严格的商品保护 mask 后重跑。")
    elif product_change > settings.product_change_review_threshold:
        risk_tags.append("product_change_near_limit")
        reasons.append("商品区域有轻微变化风险，建议人工近看鞋型、Logo 和衣服图案。")
        suggestions.append("建议确认商品主体没有被修边或光照处理误伤。")

    if spill_score > 12:
        risk_tags.append("edge_green_spill")
        reasons.append("头发、皮肤或衣物边缘仍有绿色反光残留，近看会有棚拍痕迹。")
        suggestions.append("建议提高边缘去色溢强度，或换用更干净的背景重跑。")

    if transitional_alpha < 0.22 and hard_edge_score > 1.4:
        risk_tags.append("edge_feather_too_hard")
        reasons.append("前景边缘过硬，羽化层不足，人物像直接贴在背景上。")
        suggestions.append("建议提高 soft alpha 过渡范围，尤其是头发、袖口和腿部边缘。")
    elif transitional_alpha > 11.5:
        risk_tags.append("edge_feather_too_soft")
        reasons.append("前景边缘过软，局部羽化范围偏大，细节会显得发糊。")
        suggestions.append("建议收窄边缘羽化并保留高置信主体区域。")

    if luma_gap > 58:
        risk_tags.append("lighting_mismatch")
        reasons.append("主体与邻近背景的亮度差偏大，棚拍光和外景光仍不够统一。")
        suggestions.append("建议重新执行前景亮度和色温匹配。")

    if blur_score < 42:
        risk_tags.append("background_too_blurry")
        reasons.append("背景清晰度偏低，容易产生人物贴在虚化背景前的假感。")
        suggestions.append("建议换用清晰外景背景，或增强背景锐度后重跑。")

    if hair_gap > 46:
        risk_tags.append("hair_edge_lighting_mismatch")
        reasons.append("头发或上半身边缘与周围背景亮度差偏大，边缘光不够贴合。")
        suggestions.append("建议加强头发边缘局部亮度匹配和去色溢处理。")

    if support_required and not support_kept and not background.sit_support:
        risk_tags.append("chair_logic_error")
        reasons.append("模特为坐姿，但当前背景没有合理支撑物，画面逻辑不成立。")
        suggestions.append("建议换用台阶、矮墙或长椅背景重跑。")

    if pose == "sitting" and not background.sit_support and not support_kept:
        risk_tags.append("floating_subject")
        reasons.append("坐姿主体缺少明确承托关系，容易产生悬空或蹲姿不自然的问题。")
        suggestions.append("建议保留原椅子，或改用可坐背景。")

    fatal = {"product_changed", "chair_logic_error", "background_too_blurry"}
    if any(tag in fatal for tag in risk_tags):
        status = ItemStatus.fail
    elif risk_tags:
        status = ItemStatus.review
    else:
        status = ItemStatus.pass_

    if not reasons:
        reasons.append("抠图边缘、羽化、亮度匹配、背景清晰度和头发边缘光照均通过基础检查，商品外观未发现明显变化。")
        suggestions.append("可作为正式图使用。")

    return status, "；".join(reasons), "；".join(suggestions), risk_tags
