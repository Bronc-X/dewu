import shutil
import zipfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models import BatchReport, ImageItemReport, ItemStatus
from app.storage import get_batch_paths, html_report_path, save_report, zip_path

REPORT_TEXT = {
    "zh": {
        "html_lang": "zh-CN",
        "title": "批次报告",
        "pass": "通过",
        "review": "可参考",
        "fail": "未通过",
        "image": "图片",
        "original": "原图",
        "matte": "抠图",
        "composite": "初合成",
        "final": "最终图",
        "background": "背景",
        "elapsed": "耗时",
        "seconds": "秒",
        "product_change_score": "商品变化分",
        "fallback_score": "回退基线",
        "protection": "保护",
        "reverted": "已回退",
        "ready": "可作为正式图使用。",
    },
    "en": {
        "html_lang": "en",
        "title": "Batch Report",
        "pass": "Pass",
        "review": "Review",
        "fail": "Fail",
        "image": "Image",
        "original": "Original",
        "matte": "Matte",
        "composite": "Composite",
        "final": "Final",
        "background": "Background",
        "elapsed": "Elapsed",
        "seconds": "s",
        "product_change_score": "Product Change Score",
        "fallback_score": "Fallback Baseline",
        "protection": "Protection",
        "reverted": "Reverted",
        "ready": "Ready for delivery.",
    },
}


def _relative_to_batch(batch_id: str, path: str | None) -> str | None:
    if not path:
        return None
    candidate = Path(path)
    if not candidate.is_absolute():
        return str(candidate).replace("\\", "/")
    root = get_batch_paths(batch_id).root.resolve()
    target = candidate.resolve()
    try:
        return str(target.relative_to(root)).replace("\\", "/")
    except ValueError:
        return None


def normalize_report_paths(report: BatchReport) -> None:
    for item in report.items:
        item.final = _relative_to_batch(report.batch_id, item.final)
        item.input = _relative_to_batch(report.batch_id, item.input) or item.input
        item.debug = {
            key: value
            for key, path in item.debug.items()
            if (value := _relative_to_batch(report.batch_id, path))
        }


def _item_status_label(status: object, lang: str) -> str:
    key = getattr(status, "value", str(status))
    text = REPORT_TEXT[lang]
    return {
        "queued": "排队中" if lang == "zh" else "Queued",
        "processing": "处理中" if lang == "zh" else "Processing",
        "pass": text["pass"],
        "review": text["review"],
        "fail": text["fail"],
    }.get(key, str(key))


def _english_quality_reason(item: ImageItemReport) -> str:
    risks = set(item.risk_tags)
    if "product_changed" in risks:
        return "Protected product pixels changed too much compared with the original image."
    if "edge_green_spill" in risks:
        return "Foreground edges still show green-screen spill."
    if "lighting_mismatch" in risks:
        return "Foreground and background lighting do not match closely enough."
    if "background_too_blurry" in risks:
        return "The background is too blurry for a reliable ecommerce result."
    if item.status == ItemStatus.pass_:
        return "Matting, edge quality, lighting, background clarity, and product consistency passed the checks."
    if item.status == ItemStatus.review:
        return "The item should be reviewed before delivery."
    if item.status == ItemStatus.fail:
        return "The item failed the production quality gate."
    return "Quality analysis is not available yet."


def _english_quality_suggestion(item: ImageItemReport) -> str:
    risks = set(item.risk_tags)
    if "product_changed" in risks:
        return "Rerun with a stricter product-protection mask."
    if "edge_green_spill" in risks:
        return "Increase edge despill strength or use a cleaner background candidate."
    if "lighting_mismatch" in risks:
        return "Rerun foreground brightness and color-temperature matching."
    if "background_too_blurry" in risks:
        return "Use a sharper background or enhance background sharpness before rerunning."
    if item.status == ItemStatus.pass_:
        return REPORT_TEXT["en"]["ready"]
    return "Review the image and rerun with a safer scene if needed."


def _localized_item(item: ImageItemReport, lang: str) -> dict:
    data = item.model_dump(mode="json")
    data["status_label"] = _item_status_label(item.status, lang)
    data["reason_label"] = item.reason if lang == "zh" else (item.reason_en or _english_quality_reason(item))
    data["suggestion_label"] = item.suggestion if lang == "zh" else (item.suggestion_en or _english_quality_suggestion(item))
    return data


def render_html_report(report: BatchReport, lang: str = "zh") -> None:
    lang = "en" if lang == "en" else "zh"
    env = Environment(
        loader=FileSystemLoader("app/web/templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report.html")
    localized_items = [_localized_item(item, lang) for item in report.items]
    html = template.render(
        report=report,
        items=localized_items,
        lang=lang,
        t=REPORT_TEXT[lang],
        status_labels={
            "queued": _item_status_label("queued", lang),
            "processing": _item_status_label("processing", lang),
            "pass": _item_status_label("pass", lang),
            "review": _item_status_label("review", lang),
            "fail": _item_status_label("fail", lang),
        },
    )
    html_report_path(report.batch_id, lang).write_text(html, encoding="utf-8")


def create_zip(report: BatchReport) -> Path:
    path = zip_path(report.batch_id)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    root = get_batch_paths(report.batch_id).root
    if path.exists():
        path.unlink()
    if tmp_path.exists():
        tmp_path.unlink()
    render_html_report(report, "zh")
    render_html_report(report, "en")
    save_report(report)
    with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for directory in [
            "input",
            "final_pass",
            "final_review",
            "final_fail",
            "debug_matte",
            "debug_composite",
            "debug_final",
            "background_used",
        ]:
            current = root / directory
            if current.exists():
                for file in current.rglob("*"):
                    if file.is_file():
                        archive.write(file, file.relative_to(root))
        for file in [root / "report.json", root / "report_zh.html", root / "report_en.html"]:
            if file.exists():
                archive.write(file, file.name)
    tmp_path.replace(path)
    return path


def copy_final_to_bucket(source: Path, report_status: str, batch_id: str, filename: str) -> Path:
    paths = get_batch_paths(batch_id)
    buckets = {
        "pass": paths.final_pass,
        "review": paths.final_review,
        "fail": paths.final_fail,
    }
    target = buckets[report_status] / filename
    shutil.copy2(source, target)
    return target
