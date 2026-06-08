import json
import time
from pathlib import Path

from app.config import settings
from app.models import BatchPaths, BatchReport, BatchStatus, ProjectRecord


def ensure_base_dirs() -> None:
    settings.app_data_dir.mkdir(parents=True, exist_ok=True)
    (settings.app_data_dir / "batches").mkdir(parents=True, exist_ok=True)
    (settings.app_data_dir / "projects").mkdir(parents=True, exist_ok=True)
    (settings.app_data_dir / "provider_outputs").mkdir(parents=True, exist_ok=True)
    settings.background_dir.mkdir(parents=True, exist_ok=True)


def get_batch_paths(batch_id: str) -> BatchPaths:
    root = settings.app_data_dir / "batches" / batch_id
    return BatchPaths(
        root=root,
        input=root / "input",
        final_pass=root / "final_pass",
        final_review=root / "final_review",
        final_fail=root / "final_fail",
        debug_matte=root / "debug_matte",
        debug_composite=root / "debug_composite",
        debug_final=root / "debug_final",
        background_used=root / "background_used",
    )


def create_batch_dirs(batch_id: str) -> BatchPaths:
    paths = get_batch_paths(batch_id)
    for directory in paths.model_dump().values():
        Path(directory).mkdir(parents=True, exist_ok=True)
    return paths


def report_path(batch_id: str) -> Path:
    return get_batch_paths(batch_id).root / "report.json"


def html_report_path(batch_id: str) -> Path:
    return get_batch_paths(batch_id).root / "report.html"


def zip_path(batch_id: str) -> Path:
    return get_batch_paths(batch_id).root / f"batch_{batch_id}.zip"


def projects_dir() -> Path:
    path = settings.app_data_dir / "projects"
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_dir(project_id: str) -> Path:
    path = projects_dir() / project_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_path(project_id: str) -> Path:
    return project_dir(project_id) / "project.json"


def project_assets_dir(project_id: str) -> Path:
    path = project_dir(project_id) / "assets"
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_results_dir(project_id: str) -> Path:
    path = project_dir(project_id) / "results"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_report(report: BatchReport) -> None:
    report.recompute_counts()
    path = report_path(report.batch_id)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    tmp_path.replace(path)


def save_project(project: ProjectRecord) -> None:
    path = project_path(project.id)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(project.model_dump_json(indent=2), encoding="utf-8")
    tmp_path.replace(path)


def load_project(project_id: str) -> ProjectRecord:
    path = project_path(project_id)
    if not path.exists():
        raise FileNotFoundError(project_id)
    return ProjectRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))


def list_projects() -> list[ProjectRecord]:
    records: list[ProjectRecord] = []
    for path in sorted(projects_dir().glob("*/project.json")):
        try:
            records.append(ProjectRecord.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        except Exception:
            continue
    records.sort(key=lambda item: item.updated_at, reverse=True)
    return records


def load_report(batch_id: str) -> BatchReport:
    path = report_path(batch_id)
    if not path.exists():
        return BatchReport(batch_id=batch_id, status=BatchStatus.queued, total=0)
    last_error: Exception | None = None
    for _ in range(3):
        try:
            return BatchReport.model_validate(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            last_error = exc
            time.sleep(0.05)
    raise last_error or RuntimeError("无法读取批次报告。")
