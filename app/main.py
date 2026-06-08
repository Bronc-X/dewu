from datetime import datetime
from pathlib import Path
import asyncio
import os
import shutil
import subprocess
import sys
import threading
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
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
    BatchReport,
    BatchStatus,
    ImageItemReport,
    PhotoRoomEditRequest,
    PhotoRoomMattingRequest,
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

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
ACTIVE_WORKERS: set[str] = set()
ACTIVE_WORKERS_LOCK = threading.Lock()
WORKSPACE_ROOT = Path.cwd().resolve()


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "history_items": _recent_batch_history(),
            "current_batch_id": "",
        },
    )


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status_code=204)


@app.post("/batches")
async def create_batch(
    files: list[UploadFile] = File(...),
) -> RedirectResponse:
    if len(files) != settings.max_images_per_batch:
        raise HTTPException(
            status_code=400,
            detail=f"请一次上传 {settings.max_images_per_batch} 张图片。",
        )

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
    return RedirectResponse(url=f"/batches/{batch_id}", status_code=303)


@app.post("/batches/pick-local")
def create_batch_from_local_picker() -> RedirectResponse:
    selected = _pick_local_images()
    if len(selected) != settings.max_images_per_batch:
        raise HTTPException(
            status_code=400,
            detail=f"Please select exactly {settings.max_images_per_batch} images.",
        )

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
    return RedirectResponse(url=f"/batches/{batch_id}", status_code=303)


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
            title="Select exactly 8 product images",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.webp"),
                ("All files", "*.*"),
            ],
        )
    finally:
        root.destroy()
    return [Path(filename) for filename in filenames]


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


def _status_label(status: BatchStatus) -> str:
    return {
        BatchStatus.queued: "排队中",
        BatchStatus.processing: "处理中",
        BatchStatus.completed: "已完成",
        BatchStatus.failed: "失败",
    }.get(status, status.value)


def _recent_batch_history(limit: int = 14) -> list[dict[str, str | int]]:
    batches_dir = settings.app_data_dir / "batches"
    if not batches_dir.exists():
        return []

    report_files = sorted(
        batches_dir.glob("*/report.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    history: list[dict[str, str | int]] = []
    for report_file in report_files[:limit]:
        batch_id = report_file.parent.name
        try:
            report = load_report(batch_id)
        except Exception:
            continue
        report.recompute_counts()
        history.append(
            {
                "batch_id": batch_id,
                "display_time": _batch_display_time(batch_id, report_file),
                "status": _status_label(report.status),
                "total": report.total,
                "pass_count": report.pass_count,
                "review_count": report.review_count,
                "fail_count": report.fail_count,
            }
        )
    return history


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _safe_name(name: str) -> str:
    return "".join(
        character if character.isalnum() or character in {"-", "_", "."} else "_"
        for character in name
    ).strip("._") or "asset"


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
    report = load_report(batch_id)
    report.recompute_counts()
    if not report_path(batch_id).exists():
        raise HTTPException(status_code=404, detail="批次不存在")
    return templates.TemplateResponse(
        "batch.html",
        {
            "request": request,
            "report": report,
            "batch_id": batch_id,
            "batch_display_time": _batch_display_time(batch_id, report_path(batch_id)),
            "history_items": _recent_batch_history(),
            "current_batch_id": batch_id,
            "zip_exists": zip_path(batch_id).exists(),
        },
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
def download_report_html(batch_id: str) -> FileResponse:
    path = html_report_path(batch_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="HTML 报告不存在")
    return FileResponse(path, filename="report.html")


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
