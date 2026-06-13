import asyncio
import csv
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api_clients.photoroom import PhotoRoomClient
from app.config import settings


RUN_DIR = Path("data/client_batches/2026-06-13_photoroom_50")
UPLOAD_DIR = RUN_DIR / "01_upload_source"
OUTPUT_DIR = RUN_DIR / "03_results_renamed"
PASS_DIR = RUN_DIR / "04_qc_pass"
REWORK_DIR = RUN_DIR / "06_rework"
DELIVERY_DIR = RUN_DIR / "07_delivery"
MANIFEST_PATH = RUN_DIR / "qa_manifest.csv"
RUN_NOTES_PATH = RUN_DIR / "run_notes.md"

BACKGROUND_PROMPT = (
    "Clean commercial ecommerce outdoor background for fashion product photography, "
    "cool neutral gray tone, soft overcast daylight, realistic concrete or stone ground, "
    "natural contact shadows, clean streetwear catalog style, no people, no text, no logos, "
    "no signs, no watermark. Match the subject angle, clothing style, lighting, and full-body "
    "pose. Keep the model, clothing, shoes, logos, shape, colors, and product details unchanged."
)


def image_files() -> list[Path]:
    return sorted(
        path
        for path in UPLOAD_DIR.iterdir()
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )


def existing_manifest() -> dict[str, dict[str, str]]:
    if not MANIFEST_PATH.exists():
        return {}
    with MANIFEST_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        return {row["id"]: row for row in rows}


def write_manifest(rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "id",
        "original_filename",
        "source_path",
        "upload_filename",
        "status",
        "result_filename",
        "notes",
    ]
    with MANIFEST_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


async def process_one(
    client: PhotoRoomClient,
    source: Path,
    row: dict[str, str],
    semaphore: asyncio.Semaphore,
) -> dict[str, str]:
    item_id = row["id"]
    output_path = OUTPUT_DIR / f"{item_id}_ai_bg.png"
    pass_path = PASS_DIR / output_path.name
    if output_path.exists() and output_path.stat().st_size > 0:
        row["status"] = "pass"
        row["result_filename"] = output_path.name
        row["notes"] = "already completed"
        if not pass_path.exists():
            shutil.copy2(output_path, pass_path)
        return row

    async with semaphore:
        started = time.perf_counter()
        try:
            call = await client.edit_image(
                source,
                output_path,
                background_prompt=BACKGROUND_PROMPT,
                lighting_mode="ai.auto",
                shadow_mode="ai.soft",
                remove_background=True,
                max_width=settings.processing_long_edge,
                max_height=settings.processing_long_edge,
            )
            if not output_path.exists() or output_path.stat().st_size <= 0:
                raise RuntimeError("PhotoRoom call returned but output file is empty")
            shutil.copy2(output_path, pass_path)
            row["status"] = "pass"
            row["result_filename"] = output_path.name
            row["notes"] = (
                f"completed in {time.perf_counter() - started:.1f}s; "
                f"endpoint={call.get('endpoint', '')}"
            )
        except Exception as exc:
            row["status"] = "rework"
            row["result_filename"] = ""
            row["notes"] = str(exc)
        return row


async def main() -> None:
    for directory in [OUTPUT_DIR, PASS_DIR, REWORK_DIR, DELIVERY_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    files = image_files()
    if len(files) != 50:
        raise RuntimeError(f"Expected exactly 50 selected images, found {len(files)}")

    manifest = existing_manifest()
    rows: list[dict[str, str]] = []
    for index, source in enumerate(files, start=1):
        item_id = f"DW_{index:03d}"
        row = manifest.get(item_id, {})
        rows.append(
            {
                "id": item_id,
                "original_filename": row.get("original_filename", source.name),
                "source_path": row.get("source_path", ""),
                "upload_filename": source.name,
                "status": row.get("status", "queued"),
                "result_filename": row.get("result_filename", ""),
                "notes": row.get("notes", ""),
            }
        )

    write_manifest(rows)

    client = PhotoRoomClient()
    if not client.configured():
        raise RuntimeError("PHOTOROOM_API_KEY is not configured")

    semaphore = asyncio.Semaphore(max(1, settings.photoroom_max_concurrency))
    tasks = [
        asyncio.create_task(process_one(client, UPLOAD_DIR / row["upload_filename"], row, semaphore))
        for row in rows
    ]

    completed: list[dict[str, str]] = []
    for task in asyncio.as_completed(tasks):
        completed.append(await task)
        merged = {row["id"]: row for row in rows}
        merged.update({row["id"]: row for row in completed})
        write_manifest([merged[f"DW_{index:03d}"] for index in range(1, 51)])
        print(json.dumps({"completed": len(completed), "passed": sum(1 for row in completed if row["status"] == "pass")}))

    final_rows = sorted(completed, key=lambda row: row["id"])
    write_manifest(final_rows)

    failed = [row for row in final_rows if row["status"] != "pass"]
    if failed:
        for row in failed:
            (REWORK_DIR / f"{row['id']}.txt").write_text(row["notes"], encoding="utf-8")
        raise RuntimeError(f"{len(failed)} image(s) failed; see qa_manifest.csv")

    final_images_dir = DELIVERY_DIR / "final_images"
    qc_dir = DELIVERY_DIR / "qc"
    final_images_dir.mkdir(parents=True, exist_ok=True)
    qc_dir.mkdir(parents=True, exist_ok=True)
    for output in sorted(PASS_DIR.glob("DW_*_ai_bg.png")):
        shutil.copy2(output, final_images_dir / output.name)
    shutil.copy2(MANIFEST_PATH, qc_dir / "qa_manifest.csv")

    RUN_NOTES_PATH.write_text(
        "\n".join(
            [
                "# PhotoRoom 50 Image Run",
                "",
                f"- selected images: {len(files)}",
                f"- successful outputs: {len(list(final_images_dir.glob('*.png')))}",
                f"- max requests per minute: {settings.photoroom_max_requests_per_minute}",
                f"- max concurrency: {settings.photoroom_max_concurrency}",
                "- processing: PhotoRoom Image Editing with removeBackground=true and AI background prompt",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    shutil.copy2(RUN_NOTES_PATH, qc_dir / "run_notes.md")
    archive_base = DELIVERY_DIR / "dewu_50_ai_background_final"
    archive_path = shutil.make_archive(str(archive_base), "zip", DELIVERY_DIR, "final_images")
    print(json.dumps({"ok": True, "archive": archive_path, "outputs": len(list(final_images_dir.glob('*.png')))}))


if __name__ == "__main__":
    asyncio.run(main())
