from datetime import datetime
from pathlib import Path
import asyncio
import json
import os
import shutil
import subprocess
import sys
import threading
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.responses import JSONResponse
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.agent.pipeline import process_batch
from app.api_clients.adobe import AdobeFireflyClient, AdobePhotoshopClient
from app.api_clients.errors import ProviderError
from app.api_clients.photoroom import PhotoRoomClient
from app.api_clients.providers import provider_status
from app.config import settings
from app.models import (
    AdobeFireflyGenerateRequest,
    AdobePhotoshopRemoveBackgroundRequest,
    BackgroundFeedbackRequest,
    BatchReport,
    BatchStatus,
    ImageItemReport,
    ItemStatus,
    PhotoRoomEditRequest,
    PhotoRoomMattingRequest,
    PhotoRoomSandboxMode,
    ProjectCreateRequest,
    ProjectRecord,
    ProjectStatus,
    ProjectUpdateRequest,
)
from app.storage import (
    create_batch_dirs,
    ensure_base_dirs,
    get_batch_paths,
    html_report_path,
    list_projects,
    load_project,
    project_assets_dir,
    project_results_dir,
    save_project,
    load_report,
    report_path,
    save_report,
    zip_path,
)

app = FastAPI(title="得物商品上身图背景合成 Agent")
templates = Jinja2Templates(directory="app/web/templates")
ensure_base_dirs()


@app.on_event("startup")
def startup() -> None:
    ensure_base_dirs()
    _resume_interrupted_batches()


app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
app.mount("/data", StaticFiles(directory=str(settings.app_data_dir)), name="data")
app.mount("/background-assets", StaticFiles(directory=str(settings.background_dir)), name="background_assets")

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
ACTIVE_WORKERS: set[str] = set()
ACTIVE_WORKERS_LOCK = threading.Lock()
WORKSPACE_ROOT = Path.cwd().resolve()
PROVIDER_INPUTS_DIR = settings.app_data_dir / "provider_inputs"
PROVIDER_OUTPUTS_DIR = settings.app_data_dir / "provider_outputs"
PHOTOROOM_HISTORY_PATH = PROVIDER_OUTPUTS_DIR / "photoroom_history.json"
BACKGROUND_LEARNING_DIR = settings.app_data_dir / "learning"
BACKGROUND_FEEDBACK_PATH = BACKGROUND_LEARNING_DIR / "background_feedback.jsonl"
DEV_BATCH_PREFIXES = (
    "api_probe",
    "api_two",
    "preview",
    "regression",
    "screen_guard",
    "smoke",
)

UI_TEXT = {
    "zh": {
        "html_lang": "zh-CN",
        "brand": "得物 AI",
        "engine": "智能生图引擎",
        "new_batch": "新建批次",
        "projects": "项目",
        "import": "导入",
        "pipeline": "生成",
        "review": "复核",
        "cutout_nav": "PhotoRoom 抠图",
        "ai_background_nav": "AI 智能背景",
        "review_nav": "结果复核",
        "backgrounds": "背景库",
        "settings": "设置",
        "support": "帮助",
        "search": "搜索工作台...",
        "notifications": "通知",
        "account": "账户",
        "home_title": "智能图像生产工作台",
        "home_intro": "按项目沉淀素材、批次、复核和交付结果，形成可追踪的图像生产链路。",
        "new_listing": "商品上新",
        "style_reuse": "款式复用",
        "campaign": "活动投放",
        "buyer_preview": "买家预览",
        "recent_projects": "最近项目",
        "generation_history": "真实生成记录",
        "create_first_batch": "创建第一个批次",
        "mvp_ready": "当前后端已支持上传图片、生成结果、导出报告和压缩包。",
        "no_history": "暂无批次记录。",
        "project_console": "项目控制台",
        "uploaded_assets": "已导入素材",
        "no_assets": "暂无项目素材",
        "no_assets_hint": "可以从导入页创建批次，或通过接口上传项目素材。",
        "generate": "智能生成",
        "export": "交付导出",
        "recent_batches": "最近批次",
        "no_attached_batches": "暂无绑定批次。",
        "asset_import": "素材导入",
        "import_intro": "按照影棚工具式流程处理商品图：上传 1 到 10 张图片，先抠图，再选背景、调光影，最后进入复核导出。",
        "local_picker": "本机文件选择",
        "local_picker_hint": "浏览器上传不方便时，可用本地选择器。",
        "select_images": "选择图片",
        "drop_title": "拖拽上传素材",
        "drop_hint": "支持 PNG、JPG、JPEG、WEBP，单张也可以处理，最多 10 张。",
        "no_images": "尚未选择图片。",
        "start_generation": "开始批量生成",
        "input_check": "输入检查",
        "exact_required": "支持 1 到 10 张图片",
        "screen_supported": "支持绿幕或白底输入",
        "avoid_duplicate": "处理中请勿重复提交",
        "pipeline_summary": "上传、抠图、背景、光影、阴影、复核、导出。",
        "photoroom_workflow": "PhotoRoom 式流程",
        "workflow_upload": "上传图片",
        "workflow_upload_hint": "单张或批量上传",
        "workflow_cutout": "移除背景",
        "workflow_cutout_hint": "预留抠图接口",
        "workflow_background": "选择背景",
        "workflow_background_hint": "背景图或智能背景提示词",
        "workflow_relight": "光影与阴影",
        "workflow_relight_hint": "预留调光和柔影参数",
        "workflow_export": "复核导出",
        "workflow_export_hint": "查看结果并下载",
        "api_ready": "接口接入准备",
        "api_ready_hint": "前端已连接状态查询和工具端点；填入密钥后即可调用。",
        "api_status": "接口状态",
        "api_configured": "已配置",
        "api_unconfigured": "未配置",
        "api_refresh": "刷新状态",
        "api_remove_bg": "去背景",
        "api_edit": "AI 智能背景",
        "api_relight": "仅调光",
        "api_static_background": "手选背景",
        "api_image_path": "图片路径",
        "api_upload_image": "上传测试图",
        "api_background_image": "背景参考图",
        "api_mode": "处理模式",
        "api_background_prompt": "背景提示词",
        "api_lighting_mode": "光照",
        "api_shadow_mode": "阴影",
        "api_result_placeholder": "选择一张测试图后，可直接调用 PhotoRoom 沙盒。",
        "api_run_sandbox": "运行沙盒",
        "api_download_result": "下载结果",
        "api_no_result": "还没有结果",
        "api_key_required": "需要在 .env 配置 PhotoRoom 密钥。",
        "background_title": "背景库",
        "background_intro": "预览当前固定背景资源，生成时由后端自动匹配。",
        "no_backgrounds": "背景库为空",
        "no_backgrounds_hint": "请先生成占位背景或真实背景库。",
        "settings_title": "系统设置",
        "settings_intro": "这里展示当前后端能力开关，密钥仍由 .env 管理。",
        "guardrails": "保护规则",
        "guardrails_hint": "商品主体保护、变化分数和回退策略由后端管线执行。",
        "smart_monitor": "智能生成监控",
        "processing_assets": "正在处理素材",
        "live_previews": "实时预览",
        "processing_log": "处理日志",
        "completed": "已完成",
        "pass_rate": "通过数",
        "result_review": "结果复核",
        "quality_analysis": "质量分析",
        "suggestions": "建议",
        "download_image": "下载本图",
        "failure_note": "失败原因",
        "review_note": "复核提示",
        "background": "背景",
        "json": "报告",
        "zip": "压缩包",
        "original": "原图",
        "ai_result": "生成图",
        "queued": "排队中",
        "processing": "处理中",
        "completed_status": "已完成",
        "failed": "失败",
        "pass": "通过",
        "fail": "失败",
        "status": "状态",
        "assets": "素材",
        "results": "结果",
        "updated": "更新",
        "files": "个文件",
        "batches": "个批次",
        "start_batch": "启动批次",
        "report": "报告",
        "ready": "就绪",
        "batch": "批次",
        "items": "张",
        "seconds": "秒",
        "attempts": "次尝试",
        "fit": "适应",
        "zoom": "缩放",
        "stage_isolation": "主体识别",
        "stage_matching": "背景匹配",
        "stage_lighting": "光影修复",
        "stage_review": "质检复核",
        "log_runtime": "运行时",
        "loaded_assets": "已载入原始素材",
        "local_pipeline": "本地管线",
        "production_workspace": "生产工作台",
        "mvp_flow": "可运行流程",
        "project": "项目",
        "main_navigation": "主导航",
        "compare_label": "拖动查看前后对比",
        "lighting_metric": "光照",
        "edge_metric": "边缘",
        "alignment_metric": "对齐",
        "scene_level": "场景等级",
        "priority": "优先级",
        "selected_language": "中文",
        "switch_language": "切换到英文",
    },
    "en": {
        "html_lang": "en",
        "brand": "Dewu AI",
        "engine": "Creative Engine",
        "new_batch": "New Batch",
        "projects": "Projects",
        "import": "Import",
        "pipeline": "Pipeline",
        "review": "Review",
        "cutout_nav": "PhotoRoom Cutout",
        "ai_background_nav": "AI Background",
        "review_nav": "Review Results",
        "backgrounds": "Backgrounds",
        "settings": "Settings",
        "support": "Support",
        "search": "Search workspace...",
        "notifications": "Notifications",
        "account": "Account",
        "home_title": "Smart Image Production Workspace",
        "home_intro": "Organize assets, batches, review, and delivery as a traceable production chain.",
        "new_listing": "New Listing",
        "style_reuse": "Style Reuse",
        "campaign": "Campaign",
        "buyer_preview": "Buyer Preview",
        "recent_projects": "Recent Projects",
        "generation_history": "Real Generation Runs",
        "create_first_batch": "Create the first batch",
        "mvp_ready": "The backend can upload images, generate results, and export reports and ZIP packages.",
        "no_history": "No batch history yet.",
        "project_console": "Project Console",
        "uploaded_assets": "Uploaded Assets",
        "no_assets": "No project assets yet",
        "no_assets_hint": "Use Import to create a batch, or upload assets through the API.",
        "generate": "Generate",
        "export": "Export",
        "recent_batches": "Recent Batches",
        "no_attached_batches": "No attached batches.",
        "asset_import": "Asset Import",
        "import_intro": "Use a PhotoRoom-style flow: upload 1 to 10 product photos, remove the background, choose a background, relight, then review and export.",
        "local_picker": "Local File Picker",
        "local_picker_hint": "Use the local picker when browser upload is inconvenient.",
        "select_images": "Select Images",
        "drop_title": "Drag & Drop Assets",
        "drop_hint": "PNG, JPG, JPEG, and WEBP are supported. One image is enough, up to 10 images.",
        "no_images": "No images selected.",
        "start_generation": "Start Batch Generation",
        "input_check": "Input Check",
        "exact_required": "Accepts 1 to 10 images",
        "screen_supported": "Green screen and white background inputs are supported",
        "avoid_duplicate": "Avoid duplicate submit while processing",
        "pipeline_summary": "Upload, cutout, background, relight, shadow, review, export.",
        "photoroom_workflow": "PhotoRoom-Style Flow",
        "workflow_upload": "Upload Images",
        "workflow_upload_hint": "Single or batch upload",
        "workflow_cutout": "Remove Background",
        "workflow_cutout_hint": "PhotoRoom cutout endpoint reserved",
        "workflow_background": "Choose Background",
        "workflow_background_hint": "Background image or AI prompt",
        "workflow_relight": "Relight and Shadow",
        "workflow_relight_hint": "Lighting and soft-shadow parameters reserved",
        "workflow_export": "Review and Export",
        "workflow_export_hint": "Inspect results and download",
        "api_ready": "API Readiness",
        "api_ready_hint": "The frontend is wired to status and tool endpoints. Add the API key to enable calls.",
        "api_status": "API Status",
        "api_configured": "Configured",
        "api_unconfigured": "Not Configured",
        "api_refresh": "Refresh Status",
        "api_remove_bg": "Remove Background",
        "api_edit": "AI Background",
        "api_relight": "Relight Only",
        "api_static_background": "Chosen Background",
        "api_image_path": "Image Path",
        "api_upload_image": "Upload Test Image",
        "api_background_image": "Background Reference",
        "api_mode": "Mode",
        "api_background_prompt": "Background Prompt",
        "api_lighting_mode": "Lighting",
        "api_shadow_mode": "Shadow",
        "api_result_placeholder": "Choose a test image to call the PhotoRoom sandbox.",
        "api_run_sandbox": "Run Sandbox",
        "api_download_result": "Download Result",
        "api_no_result": "No result yet",
        "api_key_required": "Set PHOTOROOM_API_KEY in .env.",
        "background_title": "Backgrounds",
        "background_intro": "Preview the fixed background library used by backend matching.",
        "no_backgrounds": "No backgrounds",
        "no_backgrounds_hint": "Generate placeholder or real backgrounds first.",
        "settings_title": "System Settings",
        "settings_intro": "Current backend capability switches. Secrets remain managed by .env.",
        "guardrails": "Guardrails",
        "guardrails_hint": "Product protection, change scoring, and fallback rules are enforced by the backend pipeline.",
        "smart_monitor": "Smart Generation Monitor",
        "processing_assets": "Processing Assets",
        "live_previews": "Live Render Previews",
        "processing_log": "Processing Log",
        "completed": "Completed",
        "pass_rate": "Pass Count",
        "result_review": "Result Review",
        "quality_analysis": "Quality Analysis",
        "suggestions": "Suggestions",
        "download_image": "Download Image",
        "failure_note": "Failure",
        "review_note": "Review note",
        "background": "Background",
        "json": "Report",
        "zip": "ZIP",
        "original": "Original",
        "ai_result": "AI Result",
        "queued": "Queued",
        "processing": "Processing",
        "completed_status": "Completed",
        "failed": "Failed",
        "pass": "Pass",
        "fail": "Fail",
        "status": "Status",
        "assets": "Assets",
        "results": "Results",
        "updated": "Updated",
        "files": "files",
        "batches": "batches",
        "start_batch": "Start batch",
        "report": "report",
        "ready": "ready",
        "batch": "Batch",
        "items": "assets",
        "seconds": "s",
        "attempts": "attempts",
        "fit": "Fit",
        "zoom": "Zoom",
        "stage_isolation": "Isolation",
        "stage_matching": "Matching",
        "stage_lighting": "Lighting",
        "stage_review": "Review",
        "log_runtime": "runtime",
        "loaded_assets": "Loaded raw assets",
        "local_pipeline": "local pipeline",
        "production_workspace": "Production workspace",
        "mvp_flow": "MVP Flow",
        "project": "Project",
        "main_navigation": "Main navigation",
        "compare_label": "Compare before and after",
        "lighting_metric": "Lighting",
        "edge_metric": "Edge",
        "alignment_metric": "Align",
        "scene_level": "Scene Level",
        "priority": "Priority",
        "selected_language": "English",
        "switch_language": "Switch to Chinese",
    },
}


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    lang = _ui_lang(request)
    latest_batch = _latest_batch_summary(lang)
    projects = _localized_projects(list_projects(), lang)
    photoroom_history = _recent_photoroom_history(limit=10, lang=lang)
    photoroom_groups = _recent_photoroom_groups(limit=10, lang=lang)
    return templates.TemplateResponse(
        "index.html",
        _template_context(request, {
            "request": request,
            "history_items": _recent_batch_history(lang=lang),
            "photoroom_history": photoroom_history,
            "photoroom_groups": photoroom_groups,
            "latest_photoroom": photoroom_history[0] if photoroom_history else None,
            "current_batch_id": "",
            "projects": projects,
            "provider_status": provider_status(),
            "latest_batch": latest_batch,
            "active_nav": "projects",
            "min_images": settings.min_images_per_batch,
            "max_images": settings.max_images_per_batch,
        }),
    )


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status_code=204)


@app.post("/batches")
async def create_batch(
    request: Request,
    files: list[UploadFile] = File(...),
) -> RedirectResponse:
    lang = _ui_lang(request)
    _validate_batch_image_count(len(files), lang=lang)

    batch_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:8]
    paths = create_batch_dirs(batch_id)
    items: list[ImageItemReport] = []

    for index, upload in enumerate(files, start=1):
        suffix = Path(upload.filename or "").suffix.lower() or ".png"
        if suffix not in IMAGE_SUFFIXES:
            raise HTTPException(status_code=400, detail=f"不支持的文件格式：{suffix}")
        filename = f"input_{index:02d}{suffix}"
        destination = paths.input / filename
        destination.write_bytes(await upload.read())
        items.append(
            ImageItemReport(
                index=index,
                input=str(destination.relative_to(paths.root)).replace("\\", "/"),
            )
        )

    report = BatchReport(
        batch_id=batch_id,
        status=BatchStatus.queued,
        total=len(items),
        items=items,
    )
    save_report(report)
    _start_batch_worker(batch_id)
    return RedirectResponse(url=f"/batches/{batch_id}?lang={lang}", status_code=303)


@app.post("/batches/pick-local")
def create_batch_from_local_picker(request: Request) -> RedirectResponse:
    lang = _ui_lang(request)
    selected = _pick_local_images()
    _validate_batch_image_count(len(selected), lang=lang)

    batch_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:8]
    paths = create_batch_dirs(batch_id)
    items: list[ImageItemReport] = []

    for index, source in enumerate(selected, start=1):
        suffix = source.suffix.lower()
        if suffix not in IMAGE_SUFFIXES:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")
        filename = f"input_{index:02d}{suffix}"
        destination = paths.input / filename
        shutil.copy2(source, destination)
        items.append(
            ImageItemReport(
                index=index,
                input=str(destination.relative_to(paths.root)).replace("\\", "/"),
            )
        )

    report = BatchReport(
        batch_id=batch_id,
        status=BatchStatus.queued,
        total=len(items),
        items=items,
    )
    save_report(report)
    _start_batch_worker(batch_id)
    return RedirectResponse(url=f"/batches/{batch_id}?lang={lang}", status_code=303)


@app.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail(request: Request, project_id: str) -> HTMLResponse:
    lang = _ui_lang(request)
    project = _load_project_or_404(project_id)
    project_view = project.model_dump(mode="json")
    project_view["type_label"] = _project_type_label(project.project_type, lang)
    project_view["status_label"] = _project_status_label(project.status, lang)
    assets = [
        {
            "filename": path.name,
            "url": f"/data/projects/{project_id}/assets/{path.name}",
            "size": path.stat().st_size,
            "updated_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        }
        for path in sorted(project_assets_dir(project_id).glob("*"))
        if path.is_file()
    ]
    batches = []
    for attached_batch_id in project.batch_ids:
        try:
            attached_report = load_report(attached_batch_id)
        except Exception:
            continue
        batches.append(
            {
                "batch_id": attached_batch_id,
                "display_time": _batch_display_time(attached_batch_id, report_path(attached_batch_id)),
                "status": _status_label(attached_report.status, _ui_lang(request)),
                "progress": _batch_progress(attached_report),
                "total": attached_report.total,
                "pass_count": attached_report.pass_count,
                "review_count": attached_report.review_count,
                "fail_count": attached_report.fail_count,
            }
        )
    return templates.TemplateResponse(
        "index.html",
        _template_context(request, {
            "request": request,
            "view": "project",
            "project": project_view,
            "assets": assets,
            "project_batches": batches,
            "history_items": _recent_batch_history(lang=_ui_lang(request)),
            "current_batch_id": "",
            "provider_status": provider_status(),
            "active_nav": "projects",
            "min_images": settings.min_images_per_batch,
            "max_images": settings.max_images_per_batch,
        }),
    )


@app.get("/import", response_class=HTMLResponse)
def import_workspace(request: Request) -> HTMLResponse:
    lang = _ui_lang(request)
    active_tool = _active_photo_tool(request)
    photoroom_history = _recent_photoroom_history(limit=10, lang=lang)
    photoroom_groups = _recent_photoroom_groups(limit=8, lang=lang)
    return templates.TemplateResponse(
        "index.html",
        _template_context(request, {
            "request": request,
            "view": "import",
            "history_items": _recent_batch_history(lang=lang),
            "photoroom_history": photoroom_history,
            "photoroom_groups": photoroom_groups,
            "latest_photoroom": photoroom_history[0] if photoroom_history else None,
            "current_batch_id": "",
            "provider_status": provider_status(),
            "active_nav": active_tool,
            "active_tool": active_tool,
            "min_images": settings.min_images_per_batch,
            "max_images": settings.max_images_per_batch,
        }),
    )


@app.get("/review", response_class=HTMLResponse)
def review_workspace(request: Request) -> HTMLResponse:
    lang = _ui_lang(request)
    photoroom_history = _recent_photoroom_history(limit=20, lang=lang)
    photoroom_groups = _recent_photoroom_groups(limit=20, lang=lang)
    return templates.TemplateResponse(
        "index.html",
        _template_context(request, {
            "request": request,
            "view": "review",
            "history_items": _recent_batch_history(lang=lang),
            "photoroom_history": photoroom_history,
            "photoroom_groups": photoroom_groups,
            "latest_photoroom": photoroom_history[0] if photoroom_history else None,
            "current_batch_id": "",
            "provider_status": provider_status(),
            "active_nav": "review",
            "min_images": settings.min_images_per_batch,
            "max_images": settings.max_images_per_batch,
        }),
    )


@app.get("/backgrounds", response_class=HTMLResponse)
def background_library(request: Request) -> HTMLResponse:
    lang = _ui_lang(request)
    backgrounds = _load_background_library(lang)
    return templates.TemplateResponse(
        "index.html",
        _template_context(request, {
            "request": request,
            "view": "backgrounds",
            "backgrounds": backgrounds,
            "history_items": _recent_batch_history(lang=lang),
            "photoroom_history": _recent_photoroom_history(limit=8, lang=lang),
            "current_batch_id": "",
            "provider_status": provider_status(),
            "active_nav": "backgrounds",
            "min_images": settings.min_images_per_batch,
            "max_images": settings.max_images_per_batch,
        }),
    )


@app.post("/backgrounds/upload")
async def upload_backgrounds(
    request: Request,
    files: list[UploadFile] = File(...),
) -> RedirectResponse:
    lang = _ui_lang(request)
    if not files:
        raise HTTPException(status_code=400, detail="at least one background image is required")
    settings.background_dir.mkdir(parents=True, exist_ok=True)
    for upload in files:
        suffix = Path(upload.filename or "").suffix.lower() or ".png"
        if suffix not in IMAGE_SUFFIXES:
            raise HTTPException(status_code=400, detail=f"unsupported file type: {suffix}")
        filename = (
            datetime.now().strftime("user_%Y%m%d_%H%M%S_")
            + uuid4().hex[:8]
            + "_"
            + _safe_name(upload.filename or f"background{suffix}")
        )
        destination = settings.background_dir / filename
        destination.write_bytes(await upload.read())
    return RedirectResponse(url=f"/backgrounds?lang={lang}", status_code=303)


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        _template_context(request, {
            "request": request,
            "view": "settings",
            "history_items": _recent_batch_history(lang=_ui_lang(request)),
            "current_batch_id": "",
            "provider_status": provider_status(),
            "active_nav": "settings",
            "min_images": settings.min_images_per_batch,
            "max_images": settings.max_images_per_batch,
        }),
    )


def _pick_local_images() -> list[Path]:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Local file picker unavailable: {exc}") from exc

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update()
    try:
        filenames = filedialog.askopenfilenames(
            parent=root,
            title=f"Select {settings.min_images_per_batch} to {settings.max_images_per_batch} product images",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.webp"),
                ("All files", "*.*"),
            ],
        )
    finally:
        root.destroy()
    return [Path(filename) for filename in filenames]


def _validate_batch_image_count(count: int, *, lang: str = "zh") -> None:
    minimum = settings.min_images_per_batch
    maximum = settings.max_images_per_batch
    if minimum <= count <= maximum:
        return
    if lang == "en":
        detail = f"Please upload {minimum} to {maximum} images."
    else:
        detail = f"请上传 {minimum} 到 {maximum} 张图片。"
    raise HTTPException(status_code=400, detail=detail)


def _start_batch_worker(batch_id: str) -> None:
    with ACTIVE_WORKERS_LOCK:
        if batch_id in ACTIVE_WORKERS:
            return
        ACTIVE_WORKERS.add(batch_id)
    threading.Thread(target=_run_batch_worker, args=(batch_id,), daemon=False).start()


def _run_batch_worker(batch_id: str) -> None:
    try:
        asyncio.run(process_batch(batch_id))
    finally:
        with ACTIVE_WORKERS_LOCK:
            ACTIVE_WORKERS.discard(batch_id)


def _resume_interrupted_batches() -> None:
    batches_dir = settings.app_data_dir / "batches"
    if not batches_dir.exists():
        return
    for report_file in sorted(batches_dir.glob("*/report.json")):
        batch_id = report_file.parent.name
        try:
            report = load_report(batch_id)
        except Exception:
            continue
        if report.status in {BatchStatus.queued, BatchStatus.processing}:
            _start_batch_worker(batch_id)


def _batch_display_time(batch_id: str, fallback_path: Path) -> str:
    try:
        parsed = datetime.strptime(batch_id[:15], "%Y%m%d_%H%M%S")
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        timestamp = datetime.fromtimestamp(fallback_path.stat().st_mtime)
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def _ui_lang(request: Request) -> str:
    lang = request.query_params.get("lang", "zh").lower()
    return "en" if lang.startswith("en") else "zh"


def _active_photo_tool(request: Request) -> str:
    tool = request.query_params.get("tool", "cutout").lower()
    return "cutout" if tool in {"cutout", "remove_background"} else "ai_background"


def _lang_url(request: Request, lang: str) -> str:
    params = dict(request.query_params)
    params["lang"] = lang
    query = "&".join(f"{key}={value}" for key, value in params.items())
    return f"{request.url.path}?{query}" if query else request.url.path


def _template_context(request: Request, context: dict) -> dict:
    lang = _ui_lang(request)
    merged = {
        "lang": lang,
        "t": UI_TEXT[lang],
        "lang_switch_url": _lang_url(request, "en" if lang == "zh" else "zh"),
        "other_lang_label": UI_TEXT[lang]["switch_language"],
    }
    merged.update(context)
    return merged


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _safe_name(filename: str) -> str:
    allowed = []
    for char in filename:
        if char.isalnum() or char in {".", "-", "_"}:
            allowed.append(char)
        else:
            allowed.append("_")
    safe = "".join(allowed).strip("._")
    return safe or "file"


def _item_status_label(status: object, lang: str = "zh") -> str:
    key = getattr(status, "value", str(status))
    text = UI_TEXT.get(lang, UI_TEXT["zh"])
    return {
        "queued": text["queued"],
        "processing": text["processing"],
        "pass": text["pass"],
        "review": text["review"],
        "fail": text["fail"],
    }.get(key, str(key))


def _status_label(status: BatchStatus, lang: str = "en") -> str:
    text = UI_TEXT.get(lang, UI_TEXT["en"])
    return {
        BatchStatus.queued: text["queued"],
        BatchStatus.processing: text["processing"],
        BatchStatus.completed: text["completed_status"],
        BatchStatus.failed: text["failed"],
    }.get(status, status.value)


def _localized_item(item: ImageItemReport, lang: str) -> dict:
    data = item.model_dump(mode="json")
    data["status_label"] = _item_status_label(item.status, lang)
    data["reason_label"] = item.reason if lang == "zh" else (item.reason_en or _english_quality_reason(item))
    data["suggestion_label"] = item.suggestion if lang == "zh" else (item.suggestion_en or _english_quality_suggestion(item))
    return data


def _english_quality_reason(item: ImageItemReport) -> str:
    risks = set(item.risk_tags)
    if "product_changed" in risks:
        return "Protected product pixels changed too much compared with the original image."
    if "product_change_near_limit" in risks:
        return "Product consistency is near the review limit; inspect shape, logo, and clothing pattern."
    if "edge_green_spill" in risks:
        return "Foreground edges still show green-screen spill."
    if "edge_feather_too_hard" in risks:
        return "Foreground edges are too hard and may look pasted onto the scene."
    if "edge_feather_too_soft" in risks:
        return "Foreground edges are too soft and may blur fine detail."
    if "lighting_mismatch" in risks:
        return "Foreground and background lighting do not match closely enough."
    if "background_too_blurry" in risks:
        return "The background is too blurry for a reliable ecommerce result."
    if "hair_edge_lighting_mismatch" in risks:
        return "Hair or upper-body edge lighting does not match the surrounding scene."
    if {"chair_logic_error", "floating_subject", "support_logic_error"} & risks:
        return "The pose needs a visible support relationship with the selected scene."
    if item.status == ItemStatus.fail:
        return "The item failed the production quality gate."
    if item.status == ItemStatus.review:
        return "The item should be reviewed before delivery."
    if item.status == ItemStatus.pass_:
        return "Matting, edge quality, lighting, background clarity, and product consistency passed the local checks."
    return "Quality analysis is not available yet."


def _english_quality_suggestion(item: ImageItemReport) -> str:
    risks = set(item.risk_tags)
    if "product_changed" in risks:
        return "Rerun with a stricter product-protection mask."
    if "product_change_near_limit" in risks:
        return "Inspect the product area before approving the image."
    if "edge_green_spill" in risks:
        return "Increase edge despill strength or use a cleaner background candidate."
    if "edge_feather_too_hard" in risks:
        return "Increase soft-alpha transition around hair, sleeves, and leg edges."
    if "edge_feather_too_soft" in risks:
        return "Narrow the feathering range while preserving high-confidence subject pixels."
    if "lighting_mismatch" in risks:
        return "Rerun foreground brightness and color-temperature matching."
    if "background_too_blurry" in risks:
        return "Use a sharper background or enhance background sharpness before rerunning."
    if "hair_edge_lighting_mismatch" in risks:
        return "Strengthen local hair-edge lighting and despill correction."
    if {"chair_logic_error", "floating_subject", "support_logic_error"} & risks:
        return "Use a steps, low-wall, bench, or chair-safe background."
    if item.status == ItemStatus.pass_:
        return "Ready for delivery."
    return "Review the image and rerun with a safer scene if needed."


def _is_business_batch(batch_id: str) -> bool:
    return not batch_id.startswith(DEV_BATCH_PREFIXES)


def _batch_issue_summary(report: BatchReport, lang: str = "zh") -> tuple[str, str]:
    failed_items = [item for item in report.items if item.status == ItemStatus.fail]
    review_items = [item for item in report.items if item.status == ItemStatus.review]
    prioritized = failed_items or review_items
    if not prioritized:
        return "", ""
    item = prioritized[0]
    reason = item.reason if lang == "zh" else (item.reason_en or _english_quality_reason(item))
    if not reason:
        reason = _english_quality_reason(item) if lang == "en" else "需要复核主体边缘、商品一致性和背景融合。"
    reason = reason.strip()
    label_key = "failure_note" if failed_items else "review_note"
    label = UI_TEXT.get(lang, UI_TEXT["zh"])[label_key]
    return reason[:96] + ("..." if len(reason) > 96 else ""), label


def _recent_batch_history(limit: int = 14, lang: str = "en") -> list[dict[str, str | int]]:
    batches_dir = settings.app_data_dir / "batches"
    if not batches_dir.exists():
        return []

    report_files = sorted(
        batches_dir.glob("*/report.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    history: list[dict[str, str | int]] = []
    for report_file in report_files:
        batch_id = report_file.parent.name
        if not _is_business_batch(batch_id):
            continue
        try:
            report = load_report(batch_id)
        except Exception:
            continue
        report.recompute_counts()
        issue_summary, issue_label = _batch_issue_summary(report, lang)
        history.append(
            {
                "batch_id": batch_id,
                "display_time": _batch_display_time(batch_id, report_file),
                "status": _status_label(report.status, lang),
                "total": report.total,
                "pass_count": report.pass_count,
                "review_count": report.review_count,
                "fail_count": report.fail_count,
                "issue_summary": issue_summary,
                "issue_label": issue_label,
            }
        )
        if len(history) >= limit:
            break
    return history


def _read_photoroom_history() -> list[dict]:
    if not PHOTOROOM_HISTORY_PATH.exists():
        return []
    try:
        payload = json.loads(PHOTOROOM_HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _write_photoroom_history(items: list[dict]) -> None:
    PROVIDER_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    PHOTOROOM_HISTORY_PATH.write_text(
        json.dumps(items[:80], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _record_photoroom_history(entry: dict) -> dict:
    now = datetime.now()
    normalized = {
        "id": entry.get("id") or now.strftime("photoroom_%Y%m%d_%H%M%S_") + uuid4().hex[:8],
        "batch_id": entry.get("batch_id") or now.strftime("photoroom_batch_%Y%m%d_%H%M%S_") + uuid4().hex[:8],
        "created_at": entry.get("created_at") or now.isoformat(timespec="seconds"),
        "provider": "photoroom",
        "ok": bool(entry.get("ok")),
        "mode": str(entry.get("mode") or ""),
        "input_url": entry.get("input_url") or "",
        "input_path": entry.get("input_path") or "",
        "result_url": entry.get("result_url") or "",
        "result_path": entry.get("result_path") or "",
        "alpha_url": entry.get("alpha_url") or "",
        "background_url": entry.get("background_url") or "",
        "background_path": entry.get("background_path") or "",
        "background_prompt": entry.get("background_prompt") or "",
        "background_seed": entry.get("background_seed") if entry.get("background_seed") not in (None, "") else "",
        "background_theme": entry.get("background_theme") or "",
        "candidate_label": entry.get("candidate_label") or "",
        "lighting_mode": entry.get("lighting_mode") or "",
        "shadow_mode": entry.get("shadow_mode") or "",
        "error": entry.get("error") or "",
    }
    history = [item for item in _read_photoroom_history() if item.get("id") != normalized["id"]]
    history.insert(0, normalized)
    _write_photoroom_history(history)
    return normalized


BACKGROUND_FEEDBACK_LABELS = {
    "pass": {"zh": "通过", "en": "Pass", "result": "pass", "weight": 2},
    "fake_background": {"zh": "背景假", "en": "Fake Background", "result": "fail", "weight": -3},
    "bad_floor_contact": {"zh": "脚底/地面不对", "en": "Bad Floor Contact", "result": "fail", "weight": -3},
    "insufficient_background_change": {"zh": "背景变化太小", "en": "Too Little Change", "result": "fail", "weight": -2},
    "background_subject_scale_mismatch": {"zh": "主体比例不对", "en": "Scale Mismatch", "result": "fail", "weight": -3},
    "product_changed": {"zh": "商品变了", "en": "Product Changed", "result": "fail", "weight": -5},
}


def _read_background_feedback() -> list[dict]:
    if not BACKGROUND_FEEDBACK_PATH.exists():
        return []
    items: list[dict] = []
    for line in BACKGROUND_FEEDBACK_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            items.append(payload)
    return items


def _append_background_feedback(entry: dict) -> dict:
    BACKGROUND_LEARNING_DIR.mkdir(parents=True, exist_ok=True)
    normalized = {
        "id": entry.get("id") or datetime.now().strftime("bgfb_%Y%m%d_%H%M%S_") + uuid4().hex[:8],
        "created_at": entry.get("created_at") or datetime.now().isoformat(timespec="seconds"),
        "history_id": entry.get("history_id") or "",
        "batch_id": entry.get("batch_id") or "",
        "input_type": entry.get("input_type") or "unknown",
        "theme": entry.get("theme") or "",
        "prompt_id": entry.get("prompt_id") or "",
        "prompt": entry.get("prompt") or "",
        "seed": entry.get("seed") if entry.get("seed") not in (None, "") else "",
        "candidate_label": entry.get("candidate_label") or "",
        "lighting_mode": entry.get("lighting_mode") or "",
        "shadow_mode": entry.get("shadow_mode") or "",
        "result": entry.get("result") or "fail",
        "feedback_tag": entry.get("feedback_tag") or "",
        "failure_tags": entry.get("failure_tags") or [],
        "weight": entry.get("weight") or 0,
        "note": entry.get("note") or "",
    }
    with BACKGROUND_FEEDBACK_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(normalized, ensure_ascii=False) + "\n")
    return normalized


def _background_feedback_summary(lang: str = "zh") -> dict:
    rows = _read_background_feedback()
    theme_scores: dict[str, int] = {}
    tag_counts: dict[str, int] = {}
    recent = []
    for row in rows:
      theme = str(row.get("theme") or "")
      if theme:
          theme_scores[theme] = theme_scores.get(theme, 0) + int(row.get("weight") or 0)
      tag = str(row.get("feedback_tag") or "")
      if tag:
          tag_counts[tag] = tag_counts.get(tag, 0) + 1
    for row in reversed(rows[-12:]):
        tag = str(row.get("feedback_tag") or "")
        label = BACKGROUND_FEEDBACK_LABELS.get(tag, {}).get(lang, tag)
        recent.append(
            {
                "created_at": row.get("created_at", ""),
                "theme": row.get("theme", ""),
                "seed": row.get("seed", ""),
                "feedback_tag": tag,
                "feedback_label": label,
                "result": row.get("result", ""),
                "weight": row.get("weight", 0),
            }
        )
    return {
        "count": len(rows),
        "theme_scores": theme_scores,
        "tag_counts": tag_counts,
        "recent": recent,
        "labels": [
            {
                "tag": tag,
                "label": data.get(lang, tag),
                "result": data["result"],
                "weight": data["weight"],
            }
            for tag, data in BACKGROUND_FEEDBACK_LABELS.items()
        ],
    }


def _photoroom_mode_label(mode: str, lang: str) -> str:
    labels = {
        "zh": {
            "remove_background": "PhotoRoom 抠图",
            "ai_background": "AI 智能背景",
            "background_image": "手选背景",
            "relight": "调光",
        },
        "en": {
            "remove_background": "PhotoRoom Cutout",
            "ai_background": "AI Background",
            "background_image": "Chosen Background",
            "relight": "Relight",
        },
    }
    return labels.get(lang, labels["zh"]).get(mode, mode or "PhotoRoom")


def _photoroom_status_label(ok: bool, lang: str) -> str:
    if lang == "en":
        return "Returned Image" if ok else "Failed"
    return "已返回图片" if ok else "失败"


def _history_display_time(created_at: str, fallback_path: Path | None = None) -> str:
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(created_at[:19], fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    if fallback_path and fallback_path.exists():
        return datetime.fromtimestamp(fallback_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    return created_at[:19] if created_at else ""


def _result_url_from_output(path: Path) -> str:
    return "/data/provider_outputs/" + path.name


def _input_url_from_output(output_path: Path) -> str:
    possible_stem = output_path.stem
    for suffix in ("_remove_background", "_ai_background", "_background_image", "_relight"):
        if possible_stem.endswith(suffix):
            possible_stem = possible_stem[: -len(suffix)]
            break
    for candidate in sorted(PROVIDER_INPUTS_DIR.glob(possible_stem + ".*")):
        if candidate.is_file() and candidate.suffix.lower() in IMAGE_SUFFIXES:
            return "/data/provider_inputs/" + candidate.name
    return ""


def _legacy_photoroom_batch_key(item: dict) -> str:
    for key in ("batch_id", "input_url", "input_path"):
        value = str(item.get(key) or "")
        if value:
            stem = Path(value).stem
            return stem.removesuffix("_photoroom-cutout")
    result = str(item.get("result_url") or item.get("result_path") or item.get("id") or "")
    stem = Path(result).stem
    for suffix in ("_remove_background", "_ai_background", "_background_image", "_relight"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return stem.removesuffix("_photoroom-cutout") or str(item.get("id") or result)


def _legacy_photoroom_output_items() -> list[dict]:
    if not PROVIDER_OUTPUTS_DIR.exists():
        return []
    items = []
    for path in sorted(PROVIDER_OUTPUTS_DIR.glob("*.png"), key=lambda item: item.stat().st_mtime, reverse=True):
        if path.name.endswith("_alpha.png") or path.name.startswith("photoroom_smoke"):
            continue
        mode = ""
        for candidate in ("remove_background", "ai_background", "background_image", "relight"):
            if path.stem.endswith("_" + candidate):
                mode = candidate
                break
        if not mode:
            continue
        created = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
        alpha_path = path.with_name(path.stem + "_alpha.png")
        items.append(
            {
                "id": "legacy_" + path.stem,
                "batch_id": _legacy_photoroom_batch_key({"result_url": _result_url_from_output(path), "input_url": _input_url_from_output(path)}),
                "created_at": created,
                "provider": "photoroom",
                "ok": True,
                "mode": mode,
                "input_url": _input_url_from_output(path),
                "input_path": "",
                "result_url": _result_url_from_output(path),
                "result_path": str(path),
                "alpha_url": _result_url_from_output(alpha_path) if alpha_path.exists() else "",
                "background_url": "",
                "background_path": "",
                "background_prompt": "",
                "background_seed": "",
                "background_theme": "",
                "candidate_label": "",
                "lighting_mode": "",
                "shadow_mode": "",
                "error": "",
            }
        )
    return items


def _recent_photoroom_history(limit: int = 12, lang: str = "zh", mode: str | None = None) -> list[dict]:
    keyed: dict[str, dict] = {}
    for item in _legacy_photoroom_output_items():
        if item.get("result_url"):
            keyed[str(item["result_url"])] = item
    for item in reversed(_read_photoroom_history()):
        key = str(item.get("result_url") or item.get("id"))
        keyed[key] = item
    combined = sorted(
        keyed.values(),
        key=lambda item: str(item.get("created_at") or ""),
        reverse=True,
    )
    if mode:
        combined = [item for item in combined if item.get("mode") == mode]

    latest_feedback_by_history: dict[str, dict] = {}
    for row in _read_background_feedback():
        history_id = str(row.get("history_id") or "")
        if history_id:
            latest_feedback_by_history[history_id] = row

    history = []
    for item in combined[:limit]:
        result_path = Path(str(item.get("result_path") or ""))
        result_url = str(item.get("result_url") or "")
        ok = bool(item.get("ok")) and bool(result_url)
        item_id = str(item.get("id") or result_url)
        feedback = latest_feedback_by_history.get(item_id, {})
        feedback_tag = str(feedback.get("feedback_tag") or "")
        feedback_label = BACKGROUND_FEEDBACK_LABELS.get(feedback_tag, {}).get(lang, feedback_tag)
        history.append(
            {
                "id": item_id,
                "batch_id": str(item.get("batch_id") or _legacy_photoroom_batch_key(item)),
                "display_time": _history_display_time(str(item.get("created_at") or ""), result_path if result_path else None),
                "mode": str(item.get("mode") or ""),
                "mode_label": _photoroom_mode_label(str(item.get("mode") or ""), lang),
                "status": _photoroom_status_label(ok, lang),
                "ok": ok,
                "input_url": str(item.get("input_url") or ""),
                "result_url": result_url,
                "alpha_url": str(item.get("alpha_url") or ""),
                "background_url": str(item.get("background_url") or ""),
                "background_prompt": str(item.get("background_prompt") or ""),
                "background_seed": item.get("background_seed") if item.get("background_seed") not in (None, "") else "",
                "background_theme": str(item.get("background_theme") or ""),
                "candidate_label": str(item.get("candidate_label") or ""),
                "lighting_mode": str(item.get("lighting_mode") or ""),
                "shadow_mode": str(item.get("shadow_mode") or ""),
                "error": str(item.get("error") or ""),
                "feedback_tag": feedback_tag,
                "feedback_label": feedback_label,
                "feedback_result": str(feedback.get("result") or ""),
                "feedback_at": str(feedback.get("created_at") or ""),
            }
        )
    return history


def _recent_photoroom_groups(limit: int = 10, lang: str = "zh") -> list[dict]:
    items = _recent_photoroom_history(limit=60, lang=lang)
    grouped: dict[str, dict] = {}
    stage_order = {
        "remove_background": 1,
        "background_image": 2,
        "ai_background": 3,
        "relight": 4,
    }
    for item in items:
        batch_id = str(item.get("batch_id") or item.get("id"))
        group = grouped.setdefault(
            batch_id,
            {
                "id": batch_id,
                "display_time": item["display_time"],
                "items": [],
                "ok": True,
                "error": "",
                "thumbnail_url": "",
                "input_url": "",
                "result_url": "",
                "mode_summary": "",
                "status": "",
            },
        )
        group["items"].append(item)
        group["display_time"] = max(str(group["display_time"]), str(item["display_time"]))
        group["ok"] = bool(group["ok"]) and bool(item.get("ok"))
        if item.get("error") and not group["error"]:
            group["error"] = item["error"]
        if item.get("input_url") and not group["input_url"]:
            group["input_url"] = item["input_url"]
        if item.get("result_url"):
            group["result_url"] = item["result_url"]
            group["thumbnail_url"] = item["result_url"]

    groups = sorted(grouped.values(), key=lambda group: str(group["display_time"]), reverse=True)
    for group in groups:
        group["items"].sort(key=lambda item: (stage_order.get(str(item.get("mode")), 99), str(item.get("display_time"))))
        input_candidates = [item for item in group["items"] if item.get("input_url")]
        result_candidates = [item for item in group["items"] if item.get("result_url")]
        if input_candidates:
            group["input_url"] = input_candidates[0]["input_url"]
        if result_candidates:
            group["result_url"] = result_candidates[-1]["result_url"]
            group["thumbnail_url"] = group["result_url"]
        labels = []
        for item in group["items"]:
            label = str(item.get("mode_label") or "")
            if label and label not in labels:
                labels.append(label)
        group["mode_summary"] = " -> ".join(labels)
        ok_count = sum(1 for item in group["items"] if item.get("ok"))
        total = len(group["items"])
        if lang == "en":
            group["status"] = f"{ok_count}/{total} returned"
        else:
            group["status"] = f"{ok_count}/{total} 已返回图片"
        if not group["thumbnail_url"]:
            group["thumbnail_url"] = group["input_url"]
    return groups[:limit]


def _latest_batch_summary(lang: str = "zh") -> dict[str, str | int] | None:
    history = _recent_batch_history(limit=1, lang=lang)
    return history[0] if history else None


def _batch_progress(report: BatchReport) -> int:
    if report.total <= 0:
        return 0
    done = sum(
        1
        for item in report.items
        if item.status.value in {"pass", "review", "fail"}
    )
    if report.status == BatchStatus.completed:
        return 100
    if report.status == BatchStatus.failed:
        return max(1, round((done / report.total) * 100))
    return max(6, min(96, round((done / report.total) * 100)))


def _batch_context(report: BatchReport, batch_id: str, lang: str = "zh") -> dict[str, object]:
    report.recompute_counts()
    items_done = sum(
        1
        for item in report.items
        if item.status.value in {"pass", "review", "fail"}
    )
    active_item = next(
        (item for item in report.items if item.status.value in {"processing", "queued"}),
        report.items[-1] if report.items else None,
    )
    first_final = next((item for item in report.items if item.final), None)
    preview_items = [item for item in report.items if item.final][:8]
    selected_item = first_final or (report.items[0] if report.items else None)
    localized_items = [_localized_item(item, lang) for item in report.items]
    localized_preview_items = [_localized_item(item, lang) for item in preview_items]
    localized_selected = _localized_item(selected_item, lang) if selected_item else None
    return {
        "progress": _batch_progress(report),
        "items_done": items_done,
        "active_item": active_item,
        "first_final": first_final,
        "selected_item": localized_selected,
        "preview_items": localized_preview_items,
        "localized_items": localized_items,
        "is_processing": report.status in {BatchStatus.queued, BatchStatus.processing},
        "zip_exists": zip_path(batch_id).exists(),
        "batch_status_label": _status_label(report.status, lang),
    }


def _selected_batch_item(report: BatchReport, request: Request) -> ImageItemReport | None:
    requested_item = request.query_params.get("item")
    if requested_item:
        try:
            requested_index = int(requested_item)
        except ValueError:
            requested_index = None
        if requested_index is not None:
            selected = next((item for item in report.items if item.index == requested_index), None)
            if selected:
                return selected
    return next((item for item in report.items if item.final), None) or (report.items[0] if report.items else None)


def _project_type_label(value: object, lang: str = "zh") -> str:
    key = getattr(value, "value", str(value))
    text = UI_TEXT.get(lang, UI_TEXT["zh"])
    return {
        "new_listing": text["new_listing"],
        "style_reuse": text["style_reuse"],
        "campaign": text["campaign"],
        "buyer_preview": text["buyer_preview"],
    }.get(key, str(key))


def _project_status_label(value: object, lang: str = "zh") -> str:
    key = getattr(value, "value", str(value))
    if lang == "zh":
        labels = {
            "draft": "草稿",
            "active": "进行中",
            "processing": "生成中",
            "review": "待复核",
            "completed": "已完成",
            "archived": "已归档",
        }
    else:
        labels = {
            "draft": "Draft",
            "active": "Active",
            "processing": "Processing",
            "review": "Review",
            "completed": "Completed",
            "archived": "Archived",
        }
    return labels.get(key, str(key))


def _localized_projects(projects: list[ProjectRecord], lang: str) -> list[dict]:
    localized = []
    for project in projects:
        data = project.model_dump(mode="json")
        data["type_label"] = _project_type_label(project.project_type, lang)
        data["status_label"] = _project_status_label(project.status, lang)
        localized.append(data)
    return localized


def _localized_background(raw: dict, lang: str) -> dict:
    scene = str(raw.get("scene_type", ""))
    ground = str(raw.get("ground_type", ""))
    lighting = str(raw.get("lighting_direction", ""))
    level = str(raw.get("scene_level", "L1_product_safe"))
    data = dict(raw)
    if lang == "zh":
        scene_labels = {
            "street": "街景",
            "steps": "台阶",
            "mountain": "山石",
            "bench": "长椅",
        }
        ground_labels = {
            "concrete": "混凝土",
            "stone": "石材",
            "unknown": "未知地面",
        }
        lighting_labels = {
            "front_left": "左前方光",
            "front": "正面光",
            "side": "侧光",
        }
        level_labels = {
            "L1_product_safe": "一级商品安全",
            "L2_pose_matched": "二级姿态匹配",
            "L3_contextual": "三级场景表达",
        }
    else:
        scene_labels = {
            "street": "Street",
            "steps": "Steps",
            "mountain": "Stone Outdoor",
            "bench": "Bench",
        }
        ground_labels = {
            "concrete": "Concrete",
            "stone": "Stone",
            "unknown": "Unknown Ground",
        }
        lighting_labels = {
            "front_left": "Front-left Light",
            "front": "Front Light",
            "side": "Side Light",
        }
        level_labels = {
            "L1_product_safe": "L1 Product Safe",
            "L2_pose_matched": "L2 Pose Matched",
            "L3_contextual": "L3 Contextual",
        }
    data["scene_type_label"] = scene_labels.get(scene, scene)
    data["ground_type_label"] = ground_labels.get(ground, ground)
    data["lighting_direction_label"] = lighting_labels.get(lighting, lighting)
    data["scene_level_label"] = level_labels.get(level, level)
    data["priority"] = raw.get("priority", 50)
    data["file"] = str(raw.get("file") or "")
    data["id"] = str(raw.get("id") or Path(data["file"]).stem)
    return data


def _load_background_library(lang: str) -> list[dict]:
    meta_path = settings.background_dir / "backgrounds.json"
    indexed: dict[str, dict] = {}
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        raw_backgrounds = payload if isinstance(payload, list) else payload.get("backgrounds", [])
    except Exception:
        raw_backgrounds = []

    for raw in raw_backgrounds:
        if not isinstance(raw, dict):
            continue
        filename = str(raw.get("file") or "")
        if not filename:
            continue
        path = settings.background_dir / filename
        if not path.exists() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        indexed[filename] = _localized_background(raw, lang)

    for path in sorted(settings.background_dir.glob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if path.name in indexed:
            continue
        if indexed and not path.name.startswith("user_"):
            continue
        indexed[path.name] = _localized_background(
            {
                "id": path.stem,
                "file": path.name,
                "scene_type": "custom",
                "ground_type": "custom",
                "lighting_direction": "custom",
                "scene_level": "user_uploaded",
                "priority": 80,
            },
            lang,
        )

    return sorted(indexed.values(), key=lambda item: (int(item.get("priority", 80)), str(item.get("id", ""))))


def _load_project_or_404(project_id: str) -> ProjectRecord:
    try:
        return load_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="project not found") from exc


def _resolve_allowed_path(path: str, *, must_exist: bool = True) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = WORKSPACE_ROOT / candidate
    resolved = candidate.resolve()
    allowed_roots = [
        WORKSPACE_ROOT,
        settings.app_data_dir.resolve(),
        settings.background_dir.resolve(),
    ]
    if not any(_is_relative_to(resolved, root) for root in allowed_roots):
        raise HTTPException(status_code=400, detail="path is outside the allowed workspace")
    if must_exist and not resolved.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return resolved


def _data_url(path: Path) -> str:
    resolved = path.resolve()
    data_root = settings.app_data_dir.resolve()
    try:
        return "/data/" + str(resolved.relative_to(data_root)).replace("\\", "/")
    except ValueError:
        return str(path)


async def _save_provider_upload(upload: UploadFile, target_dir: Path, prefix: str) -> Path:
    suffix = Path(upload.filename or "").suffix.lower() or ".png"
    if suffix not in IMAGE_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"unsupported file type: {suffix}")
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = (
        datetime.now().strftime(f"{prefix}_%Y%m%d_%H%M%S_")
        + uuid4().hex[:8]
        + "_"
        + _safe_name(upload.filename or f"image{suffix}")
    )
    destination = target_dir / filename
    destination.write_bytes(await upload.read())
    return destination


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _provider_exception_response(exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "ok": False,
            "error": str(exc),
            "type": exc.__class__.__name__,
        },
    )


@app.get("/api/providers/status")
def api_provider_status() -> dict:
    return provider_status()


@app.get("/api/tools/photoroom/history")
def api_photoroom_history(request: Request) -> dict:
    lang = _ui_lang(request)
    mode = request.query_params.get("mode")
    try:
        limit = int(request.query_params.get("limit", "12"))
    except ValueError:
        limit = 12
    return {
        "items": _recent_photoroom_history(
            limit=max(1, min(limit, 40)),
            lang=lang,
            mode=mode if mode else None,
        )
    }


@app.get("/api/learning/background-feedback")
def api_background_feedback_summary(request: Request) -> dict:
    return _background_feedback_summary(_ui_lang(request))


@app.post("/api/learning/background-feedback")
def api_background_feedback(payload: BackgroundFeedbackRequest, request: Request) -> dict:
    labels = BACKGROUND_FEEDBACK_LABELS
    if payload.feedback_tag not in labels:
        raise HTTPException(status_code=400, detail="unsupported feedback_tag")
    history_item = next(
        (item for item in _read_photoroom_history() if str(item.get("id") or "") == payload.history_id),
        None,
    )
    if not history_item:
        history_item = next(
            (item for item in _legacy_photoroom_output_items() if str(item.get("id") or "") == payload.history_id),
            None,
        )
    if not history_item:
        raise HTTPException(status_code=404, detail="history item not found")
    label = labels[payload.feedback_tag]
    result = payload.result.strip() or str(label["result"])
    feedback = _append_background_feedback(
        {
            "history_id": payload.history_id,
            "batch_id": history_item.get("batch_id") or "",
            "input_type": "unknown",
            "theme": history_item.get("background_theme") or "",
            "prompt_id": f"{history_item.get('background_theme') or 'unknown'}:{history_item.get('candidate_label') or ''}",
            "prompt": history_item.get("background_prompt") or "",
            "seed": history_item.get("background_seed") if history_item.get("background_seed") not in (None, "") else "",
            "candidate_label": history_item.get("candidate_label") or "",
            "lighting_mode": history_item.get("lighting_mode") or "",
            "shadow_mode": history_item.get("shadow_mode") or "",
            "result": result,
            "feedback_tag": payload.feedback_tag,
            "failure_tags": [] if result == "pass" else [payload.feedback_tag],
            "weight": label["weight"],
            "note": payload.note.strip(),
        }
    )
    feedback["feedback_label"] = label.get(_ui_lang(request), payload.feedback_tag)
    return {
        "ok": True,
        "feedback": feedback,
        "summary": _background_feedback_summary(_ui_lang(request)),
    }


@app.get("/api/batches/{batch_id}")
def api_get_batch(batch_id: str) -> dict:
    if not report_path(batch_id).exists():
        raise HTTPException(status_code=404, detail="batch not found")
    report = load_report(batch_id)
    report.recompute_counts()
    context = _batch_context(report, batch_id)
    return {
        "report": report.model_dump(mode="json"),
        "progress": context["progress"],
        "items_done": context["items_done"],
        "zip_exists": context["zip_exists"],
    }


@app.get("/api/projects")
def api_list_projects() -> dict:
    return {"projects": [project.model_dump() for project in list_projects()]}


@app.post("/api/projects")
def api_create_project(payload: ProjectCreateRequest) -> dict:
    project_id = datetime.now().strftime("proj_%Y%m%d_%H%M%S_") + uuid4().hex[:8]
    now = _now_iso()
    project = ProjectRecord(
        id=project_id,
        name=payload.name.strip() or "未命名项目",
        project_type=payload.project_type,
        description=payload.description,
        status=ProjectStatus.active,
        created_at=now,
        updated_at=now,
    )
    save_project(project)
    return {"project": project.model_dump()}


@app.get("/api/projects/{project_id}")
def api_get_project(project_id: str) -> dict:
    project = _load_project_or_404(project_id)
    return {"project": project.model_dump()}


@app.patch("/api/projects/{project_id}")
def api_update_project(project_id: str, payload: ProjectUpdateRequest) -> dict:
    project = _load_project_or_404(project_id)
    update = payload.model_dump(exclude_unset=True)
    for key, value in update.items():
        setattr(project, key, value)
    project.updated_at = _now_iso()
    save_project(project)
    return {"project": project.model_dump()}


@app.post("/api/projects/{project_id}/assets")
async def api_upload_project_assets(
    project_id: str,
    files: list[UploadFile] = File(...),
) -> dict:
    project = _load_project_or_404(project_id)
    target_dir = project_assets_dir(project_id)
    saved: list[dict[str, str | int]] = []
    for upload in files:
        suffix = Path(upload.filename or "").suffix.lower() or ".png"
        if suffix not in IMAGE_SUFFIXES:
            raise HTTPException(status_code=400, detail=f"unsupported file type: {suffix}")
        filename = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid4().hex[:8] + "_" + _safe_name(upload.filename or f"asset{suffix}")
        destination = target_dir / filename
        content = await upload.read()
        destination.write_bytes(content)
        saved.append({"filename": filename, "path": str(destination), "size": len(content)})
    project.asset_count += len(saved)
    project.updated_at = _now_iso()
    save_project(project)
    return {"project": project.model_dump(), "assets": saved}


@app.get("/api/projects/{project_id}/assets")
def api_list_project_assets(project_id: str) -> dict:
    _load_project_or_404(project_id)
    assets = [
        {
            "filename": path.name,
            "path": str(path),
            "size": path.stat().st_size,
            "updated_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        }
        for path in sorted(project_assets_dir(project_id).glob("*"))
        if path.is_file()
    ]
    return {"assets": assets}


@app.post("/api/projects/{project_id}/batches/{batch_id}")
def api_attach_batch_to_project(project_id: str, batch_id: str) -> dict:
    project = _load_project_or_404(project_id)
    if not report_path(batch_id).exists():
        raise HTTPException(status_code=404, detail="batch not found")
    if batch_id not in project.batch_ids:
        project.batch_ids.append(batch_id)
    project.updated_at = _now_iso()
    save_project(project)
    return {"project": project.model_dump()}


@app.get("/api/projects/{project_id}/batches")
def api_project_batches(project_id: str) -> dict:
    project = _load_project_or_404(project_id)
    batches = []
    for batch_id in project.batch_ids:
        try:
            report = load_report(batch_id)
            report.recompute_counts()
            batches.append(report.model_dump())
        except Exception:
            continue
    return {"batches": batches}


@app.post("/api/tools/photoroom/sandbox")
async def api_photoroom_sandbox(
    image: UploadFile = File(...),
    mode: PhotoRoomSandboxMode = Form(PhotoRoomSandboxMode.ai_background),
    batch_id: str = Form(""),
    background_prompt: str = Form(""),
    background_seed: int | None = Form(default=None),
    background_theme: str = Form(""),
    candidate_label: str = Form(""),
    background_image: UploadFile | None = File(default=None),
    lighting_mode: str = Form("ai.auto"),
    shadow_mode: str = Form("ai.soft"),
    padding: float | None = Form(default=None),
    output_size: str | None = Form(default=None),
):
    history_batch_id = batch_id.strip() or datetime.now().strftime("photoroom_batch_%Y%m%d_%H%M%S_") + uuid4().hex[:8]
    source = await _save_provider_upload(image, PROVIDER_INPUTS_DIR, "photoroom_input")
    background_path = (
        await _save_provider_upload(background_image, PROVIDER_INPUTS_DIR, "photoroom_bg")
        if background_image
        else None
    )
    if mode == PhotoRoomSandboxMode.background_image and background_path is None:
        raise HTTPException(status_code=400, detail="background_image is required for background_image mode")
    output_stem = f"{source.stem}_{mode.value}"
    output_path = PROVIDER_OUTPUTS_DIR / f"{output_stem}.png"
    alpha_path = PROVIDER_OUTPUTS_DIR / f"{output_stem}_alpha.png"
    photoroom = PhotoRoomClient()

    try:
        if mode == PhotoRoomSandboxMode.remove_background:
            call = await photoroom.remove_background(source, output_path, alpha_path)
            alpha_url = _data_url(alpha_path)
        else:
            prompt = background_prompt.strip() or None
            if mode == PhotoRoomSandboxMode.background_image:
                prompt = None
            if mode == PhotoRoomSandboxMode.ai_background and prompt is None:
                prompt = "clean ecommerce background matching the subject angle, style, lighting, and shadows"
            call = await photoroom.edit_image(
                source,
                output_path,
                background_image_path=background_path if mode == PhotoRoomSandboxMode.background_image else None,
                background_prompt=prompt if mode == PhotoRoomSandboxMode.ai_background else None,
                background_seed=background_seed if mode == PhotoRoomSandboxMode.ai_background else None,
                lighting_mode=lighting_mode.strip() or None,
                shadow_mode=shadow_mode.strip() or None,
                remove_background=mode != PhotoRoomSandboxMode.relight,
                padding=padding,
                output_size=output_size.strip() if output_size else None,
                max_width=settings.processing_long_edge,
                max_height=settings.processing_long_edge,
            )
            alpha_url = None
    except ProviderError as exc:
        _record_photoroom_history(
            {
                "ok": False,
                "batch_id": history_batch_id,
                "mode": mode.value,
                "input_url": _data_url(source),
                "input_path": str(source),
                "background_url": _data_url(background_path) if background_path else "",
                "background_path": str(background_path) if background_path else "",
                "background_prompt": background_prompt.strip(),
                "background_seed": background_seed if background_seed is not None else "",
                "background_theme": background_theme.strip(),
                "candidate_label": candidate_label.strip(),
                "lighting_mode": lighting_mode.strip(),
                "shadow_mode": shadow_mode.strip(),
                "error": str(exc),
            }
        )
        return _provider_exception_response(exc)

    history_entry = _record_photoroom_history(
        {
            "ok": True,
            "batch_id": history_batch_id,
            "mode": mode.value,
            "input_url": _data_url(source),
            "input_path": str(source),
            "result_url": _data_url(output_path),
            "result_path": str(output_path),
            "alpha_url": alpha_url or "",
            "background_url": _data_url(background_path) if background_path else "",
            "background_path": str(background_path) if background_path else "",
            "background_prompt": background_prompt.strip(),
            "background_seed": background_seed if background_seed is not None else "",
            "background_theme": background_theme.strip(),
            "candidate_label": candidate_label.strip(),
            "lighting_mode": lighting_mode.strip(),
            "shadow_mode": shadow_mode.strip(),
        }
    )

    return {
        "ok": True,
        "mode": mode.value,
        "history": history_entry,
        "input": {
            "path": str(source),
            "url": _data_url(source),
        },
        "result": {
            "path": str(output_path),
            "url": _data_url(output_path),
            "alpha_url": alpha_url,
        },
        "call": call,
        "unsupported_addons": [
            {
                "name": "manual_retouch",
                "reason": "当前 PhotoRoom 工具接口已覆盖抠图、背景、光影、阴影；像画笔擦除/局部人工修图这类交互需要后续接画布层或 PhotoRoom 对应编辑端点。",
            }
        ],
    }


@app.post("/api/tools/photoroom/remove-background")
async def api_photoroom_remove_background(payload: PhotoRoomMattingRequest):
    source = _resolve_allowed_path(payload.image_path)
    output_rgba = _resolve_allowed_path(
        payload.output_rgba_path
        or str(settings.app_data_dir / "provider_outputs" / f"{source.stem}_photoroom_rgba.png"),
        must_exist=False,
    )
    output_alpha = (
        _resolve_allowed_path(payload.output_alpha_path, must_exist=False)
        if payload.output_alpha_path
        else output_rgba.with_name(f"{output_rgba.stem}_alpha.png")
    )
    try:
        call = await PhotoRoomClient().remove_background(source, output_rgba, output_alpha)
    except ProviderError as exc:
        return _provider_exception_response(exc)
    return {"ok": True, "call": call}


@app.post("/api/tools/photoroom/edit")
async def api_photoroom_edit(payload: PhotoRoomEditRequest):
    source = _resolve_allowed_path(payload.image_path)
    output = _resolve_allowed_path(
        payload.output_path
        or str(settings.app_data_dir / "provider_outputs" / f"{source.stem}_photoroom_edit.png"),
        must_exist=False,
    )
    try:
        call = await PhotoRoomClient().edit_image(
            source,
            output,
            background_image_path=_resolve_allowed_path(payload.background_image_path) if payload.background_image_path else None,
            background_prompt=payload.background_prompt,
            background_seed=payload.background_seed,
            guidance_image_path=_resolve_allowed_path(payload.guidance_image_path) if payload.guidance_image_path else None,
            guidance_scale=payload.guidance_scale,
            lighting_mode=payload.lighting_mode,
            shadow_mode=payload.shadow_mode,
            remove_background=payload.remove_background,
            padding=payload.padding,
            output_size=payload.output_size,
            max_width=settings.processing_long_edge,
            max_height=settings.processing_long_edge,
        )
    except ProviderError as exc:
        return _provider_exception_response(exc)
    return {"ok": True, "call": call}


@app.post("/api/tools/adobe/firefly/generate-background")
async def api_adobe_firefly_generate(payload: AdobeFireflyGenerateRequest):
    output = _resolve_allowed_path(payload.output_path, must_exist=False)
    try:
        call = await AdobeFireflyClient().generate_background(
            payload.prompt,
            output,
            content_class=payload.content_class,
        )
    except ProviderError as exc:
        return _provider_exception_response(exc)
    return {"ok": True, "call": call}


@app.post("/api/tools/adobe/photoshop/remove-background")
async def api_adobe_photoshop_remove_background(
    payload: AdobePhotoshopRemoveBackgroundRequest,
):
    try:
        call = await AdobePhotoshopClient().remove_background_from_url(
            payload.source_url,
            mode=payload.mode,
            media_type=payload.media_type,
        )
    except ProviderError as exc:
        return _provider_exception_response(exc)
    return {"ok": True, "call": call}


def _resolve_batch_file(batch_id: str, path: str) -> Path:
    batch_root = get_batch_paths(batch_id).root.resolve()
    target = (batch_root / path).resolve()
    try:
        target.relative_to(batch_root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="文件不存在") from exc
    if not target.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return target


def _open_in_file_manager(target: Path) -> None:
    resolved = target.resolve()
    if os.name == "nt":
        if resolved.is_file():
            subprocess.Popen(["explorer.exe", f"/select,{resolved}"])
        else:
            subprocess.Popen(["explorer.exe", str(resolved)])
        return
    if sys.platform == "darwin":
        if resolved.is_file():
            subprocess.Popen(["open", "-R", str(resolved)])
        else:
            subprocess.Popen(["open", str(resolved)])
        return
    subprocess.Popen(["xdg-open", str(resolved.parent if resolved.is_file() else resolved)])


@app.get("/batches/{batch_id}", response_class=HTMLResponse)
def view_batch(request: Request, batch_id: str) -> HTMLResponse:
    lang = _ui_lang(request)
    report = load_report(batch_id)
    report.recompute_counts()
    if not report_path(batch_id).exists():
        raise HTTPException(status_code=404, detail="批次不存在")
    batch_context = _batch_context(report, batch_id, lang)
    selected_item = _selected_batch_item(report, request)
    localized_selected = _localized_item(selected_item, lang) if selected_item else None
    return templates.TemplateResponse(
        "batch.html",
        _template_context(request, {
            "request": request,
            "report": report,
            "batch_id": batch_id,
            "batch_display_time": _batch_display_time(batch_id, report_path(batch_id)),
            "history_items": _recent_batch_history(lang=lang),
            "current_batch_id": batch_id,
            "zip_exists": batch_context["zip_exists"],
            "progress": batch_context["progress"],
            "items_done": batch_context["items_done"],
            "active_item": batch_context["active_item"],
            "first_final": batch_context["first_final"],
            "preview_items": batch_context["preview_items"],
            "selected_item": localized_selected,
            "localized_items": batch_context["localized_items"],
            "is_processing": batch_context["is_processing"],
            "active_nav": "pipeline" if batch_context["is_processing"] else "review",
        }),
    )


@app.post("/batches/{batch_id}/open-folder")
def open_batch_folder(batch_id: str) -> RedirectResponse:
    batch_root = get_batch_paths(batch_id).root.resolve()
    if not batch_root.exists():
        raise HTTPException(status_code=404, detail="批次不存在")
    _open_in_file_manager(batch_root)
    return RedirectResponse(url=f"/batches/{batch_id}", status_code=303)


@app.post("/batches/{batch_id}/open-file")
def open_batch_file(batch_id: str, path: str) -> RedirectResponse:
    target = _resolve_batch_file(batch_id, path)
    _open_in_file_manager(target)
    return RedirectResponse(url=f"/batches/{batch_id}", status_code=303)


@app.get("/batches/{batch_id}/report.json")
def download_report_json(batch_id: str) -> FileResponse:
    path = report_path(batch_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="报告不存在")
    return FileResponse(path, filename="report.json")


@app.get("/batches/{batch_id}/report.html")
def download_report_html(request: Request, batch_id: str) -> FileResponse:
    lang = _ui_lang(request)
    path = html_report_path(batch_id, lang)
    if report_path(batch_id).exists():
        from app.agent.reporting import render_html_report

        report = load_report(batch_id)
        render_html_report(report, lang)
    if not path.exists():
        raise HTTPException(status_code=404, detail="HTML 报告不存在")
    return FileResponse(path, filename=f"report_{lang}.html")


@app.get("/batches/{batch_id}/zip")
def download_zip(batch_id: str) -> FileResponse:
    path = zip_path(batch_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="zip 尚未生成")
    return FileResponse(path, filename=path.name)


@app.get("/batches/{batch_id}/file")
def download_file(batch_id: str, path: str) -> FileResponse:
    target = _resolve_batch_file(batch_id, path)
    return FileResponse(target, filename=target.name)
