import asyncio
import time
from pathlib import Path

from app.agent.background_matcher import background_path, choose_background, load_backgrounds
from app.agent.product_protection import protect_candidate_or_revert
from app.agent.quality_check import evaluate_result
from app.agent.reporting import copy_final_to_bucket, create_zip, normalize_report_paths, render_html_report
from app.api_clients.photoroom import PhotoRoomClient
from app.api_clients.vision_api import VisionApiClient
from app.config import settings
from app.image_ops.compose import add_contact_shadow, composite_foreground, harmonize_light
from app.image_ops.despill import remove_green_spill
from app.image_ops.matting import create_alpha_matte, detect_screen_type
from app.models import BatchStatus, ImageItemReport, ItemStatus
from app.storage import get_batch_paths, load_report, save_report


def _status_value(status: ItemStatus) -> str:
    return "pass" if status == ItemStatus.pass_ else status.value


def _relative_to_batch(batch_id: str, path: Path) -> str:
    root = get_batch_paths(batch_id).root.resolve()
    return str(path.resolve().relative_to(root)).replace("\\", "/")


def _final_filename(item: ImageItemReport) -> str:
    original = Path(item.input).stem
    return f"{original}_final.png"


def _has_existing_final(batch_id: str, item: ImageItemReport) -> bool:
    if not item.final:
        return False
    return (get_batch_paths(batch_id).root / item.final).exists()


def _status_from_value(value: str) -> ItemStatus:
    if value == "pass":
        return ItemStatus.pass_
    if value == "review":
        return ItemStatus.review
    if value == "fail":
        return ItemStatus.fail
    return ItemStatus.review


async def process_batch(batch_id: str) -> None:
    report = load_report(batch_id)
    report.status = BatchStatus.processing
    save_report(report)

    backgrounds = load_backgrounds()
    vision = VisionApiClient()
    photoroom = PhotoRoomClient()
    used_background_ids: list[str] = [
        item.background_id for item in report.items if item.background_id
    ]

    try:
        for item in report.items:
            completed = item.status in {
                ItemStatus.pass_,
                ItemStatus.review,
                ItemStatus.fail,
            }
            if completed and _has_existing_final(batch_id, item):
                continue
            background_id = await _process_item(
                batch_id,
                item,
                backgrounds,
                vision,
                photoroom,
                used_background_ids,
            )
            if background_id:
                used_background_ids.append(background_id)
            save_report(report)

        report.status = BatchStatus.completed
        normalize_report_paths(report)
        save_report(report)
        render_html_report(report)
        archive = create_zip(report)
        report.zip_path = str(archive)
        save_report(report)
    except Exception as exc:
        report.status = BatchStatus.failed
        for item in report.items:
            if item.status in {ItemStatus.queued, ItemStatus.processing}:
                item.status = ItemStatus.fail
                item.reason = f"处理流程异常：{exc}"
                item.suggestion = "请检查服务日志、背景库和 API 配置后重试。"
        normalize_report_paths(report)
        save_report(report)
        render_html_report(report)


async def _process_item(
    batch_id: str,
    item: ImageItemReport,
    backgrounds,
    vision: VisionApiClient,
    photoroom: PhotoRoomClient,
    used_background_ids: list[str],
) -> str | None:
    paths = get_batch_paths(batch_id)
    start = time.perf_counter()
    item.status = ItemStatus.processing

    batch_root = paths.root
    input_path = Path(item.input)
    if not input_path.is_absolute() and not input_path.exists():
        input_path = batch_root / input_path
    screen_type = detect_screen_type(input_path)
    if screen_type == "unsupported":
        item.status = ItemStatus.fail
        item.reason = "输入图不是可识别的绿幕或白幕图，已停止处理，避免把已有背景、墙体或山景误抠进主体。"
        item.suggestion = "请上传原始绿幕/白幕商品上身图；如果是已经合成过的图片，需要先走人工/模型级重抠图流程。"
        item.risk_tags = ["unsupported_input_background"]
        item.elapsed_seconds = round(time.perf_counter() - start, 2)
        return None
    analysis = await vision.analyze_subject(input_path)
    pose = analysis["pose"]
    support_required = bool(analysis["support_required"])
    support_kept = bool(analysis["support_kept"])
    scene_level = str(analysis.get("scene_level", "L1_product_safe"))
    risk_tags = list(analysis.get("risk_tags", []))
    item.external_calls.append(analysis["external_call"])

    best_report: tuple[
        ItemStatus,
        str,
        str,
        str,
        str,
        list[str],
        Path,
        dict[str, str],
        str,
        dict[str, float | int | str],
        list[dict],
    ] | None = None
    max_attempts = settings.max_retries_per_image + 1

    for attempt in range(1, max_attempts + 1):
        item.attempts = attempt
        background = choose_background(
            backgrounds,
            pose,
            risk_tags,
            item.index + attempt - 1,
            used_background_ids,
            scene_level,
        )
        bg_path = background_path(background)
        if not bg_path.exists():
            raise FileNotFoundError(f"背景图不存在：{bg_path}")

        stem = f"input_{item.index:02d}_try_{attempt}"
        matte_path = paths.debug_matte / f"{stem}_rgba.png"
        mask_path = paths.debug_matte / f"{stem}_alpha.png"
        despill_path = paths.debug_matte / f"{stem}_despill.png"
        composite_path = paths.debug_composite / f"{stem}_composite.png"
        harmonized_path = paths.debug_final / f"{stem}_harmonized.png"
        shadow_path = paths.debug_final / f"{stem}_shadow.png"
        protected_path = paths.debug_final / f"{stem}_protected.png"
        used_bg_path = paths.background_used / f"{stem}_{background.id}{bg_path.suffix}"

        if settings.matting_provider == "photoroom":
            matting_call = await photoroom.remove_background(input_path, matte_path, mask_path)
            item.external_calls.append(matting_call)
        elif settings.matting_provider == "local":
            create_alpha_matte(input_path, matte_path, mask_path)
        else:
            raise RuntimeError(f"Unsupported MATTING_PROVIDER: {settings.matting_provider}")

        remove_green_spill(matte_path, despill_path)

        if settings.compositing_provider == "photoroom":
            composite_call = await photoroom.edit_image(
                input_path,
                shadow_path,
                background_image_path=bg_path,
                lighting_mode="ai.auto",
                shadow_mode="ai.soft",
                remove_background=True,
                max_width=settings.processing_long_edge,
                max_height=settings.processing_long_edge,
            )
            item.external_calls.append(composite_call)
            composite_path = shadow_path
            harmonized_path = shadow_path
        elif settings.compositing_provider == "local":
            composite_foreground(despill_path, bg_path, composite_path, used_bg_path)
            harmonize_light(composite_path, harmonized_path)
            add_contact_shadow(harmonized_path, mask_path, shadow_path)
        else:
            raise RuntimeError(f"Unsupported COMPOSITING_PROVIDER: {settings.compositing_provider}")

        used_bg_path.parent.mkdir(parents=True, exist_ok=True)
        if not used_bg_path.exists():
            used_bg_path.write_bytes(bg_path.read_bytes())
        protected_final_path, product_guard = protect_candidate_or_revert(
            original_path=input_path,
            candidate_path=shadow_path,
            fallback_path=harmonized_path,
            mask_path=mask_path,
            output_path=protected_path,
        )

        status, reason, suggestion, evaluated_risks = evaluate_result(
            original_path=input_path,
            final_path=protected_final_path,
            rgba_path=despill_path,
            mask_path=mask_path,
            background=background,
            pose=pose,
            support_required=support_required,
            support_kept=support_kept,
        )
        quality_payload = {
            "status": _status_value(status),
            "reason": reason,
            "suggestion": suggestion,
            "risk_tags": evaluated_risks,
            "background_id": background.id,
            "pose": pose,
            "scene_level": background.scene_level,
            "target_scene_level": scene_level,
            "product_consistency": "strict",
        }
        quality_payload = await vision.explain_quality(
            quality_payload, input_path, protected_final_path
        )
        if quality_payload.get("external_call"):
            item.external_calls.append(quality_payload["external_call"])
        status = _status_from_value(str(quality_payload.get("status", _status_value(status))))
        reason = str(quality_payload.get("reason", reason))
        reason_en = str(quality_payload.get("reason_en", ""))
        suggestion = str(quality_payload.get("suggestion", suggestion))
        suggestion_en = str(quality_payload.get("suggestion_en", ""))
        evaluated_risks = [
            str(tag) for tag in quality_payload.get("risk_tags", evaluated_risks)
        ]

        debug = {
            "rgba": str(matte_path),
            "alpha": str(mask_path),
            "despill": str(despill_path),
            "composite": str(composite_path),
            "harmonized": str(harmonized_path),
            "final_debug": str(shadow_path),
            "protected_final": str(protected_final_path),
            "background_used": str(used_bg_path),
        }
        metrics = {
            "product_change_score": product_guard["candidate_score"],
            "product_change_fallback_score": product_guard["fallback_score"],
        }
        best_report = (
            status,
            reason,
            reason_en,
            suggestion,
            suggestion_en,
            evaluated_risks,
            protected_final_path,
            debug,
            background.id,
            metrics,
            [product_guard],
        )
        if status != ItemStatus.fail:
            break
        await asyncio.sleep(0)

    if best_report is None:
        raise RuntimeError("处理失败，未生成任何候选结果。")

    (
        status,
        reason,
        reason_en,
        suggestion,
        suggestion_en,
        evaluated_risks,
        final_debug_path,
        debug,
        background_id,
        metrics,
        guardrails,
    ) = best_report
    final_path = copy_final_to_bucket(final_debug_path, _status_value(status), batch_id, _final_filename(item))

    item.status = status
    item.final = _relative_to_batch(batch_id, final_path)
    item.background_id = background_id
    item.reason = reason
    item.reason_en = reason_en
    item.suggestion = suggestion
    item.suggestion_en = suggestion_en
    item.risk_tags = evaluated_risks
    item.debug = {key: _relative_to_batch(batch_id, Path(value)) for key, value in debug.items()}
    item.metrics = metrics
    item.guardrails = guardrails
    item.elapsed_seconds = round(time.perf_counter() - start, 2)
    return background_id
