import shutil
import zipfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models import BatchReport
from app.storage import get_batch_paths, html_report_path, save_report, zip_path


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


def render_html_report(report: BatchReport) -> None:
    env = Environment(
        loader=FileSystemLoader("app/web/templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report.html")
    html = template.render(report=report)
    html_report_path(report.batch_id).write_text(html, encoding="utf-8")


def create_zip(report: BatchReport) -> Path:
    path = zip_path(report.batch_id)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    root = get_batch_paths(report.batch_id).root
    if path.exists():
        path.unlink()
    if tmp_path.exists():
        tmp_path.unlink()
    render_html_report(report)
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
        for file in [root / "report.json", root / "report.html"]:
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
