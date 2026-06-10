import argparse
import asyncio
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agent.pipeline import process_batch
from app.config import settings
from app.models import BatchReport, BatchStatus, ImageItemReport
from app.storage import create_batch_dirs, load_report, save_report


SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def _collect_images(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"回归样本目录不存在：{input_dir}")
    files = [
        path
        for path in sorted(input_dir.iterdir())
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]
    if not settings.min_images_per_batch <= len(files) <= settings.max_images_per_batch:
        raise ValueError(
            f"回归样本必须为 {settings.min_images_per_batch} 到 {settings.max_images_per_batch} 张，"
            f"当前 {len(files)} 张：{input_dir}"
        )
    return files


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run a configured-size regression batch.")
    parser.add_argument(
        "--input-dir",
        default="data/regression_cases/default",
        help="Directory containing 1 to the configured maximum number of regression images.",
    )
    parser.add_argument(
        "--batch-id",
        default="regression_" + datetime.now().strftime("%Y%m%d_%H%M%S"),
        help="Batch id to write under data/batches.",
    )
    args = parser.parse_args()

    images = _collect_images(Path(args.input_dir))
    paths = create_batch_dirs(args.batch_id)
    items: list[ImageItemReport] = []
    for index, source in enumerate(images, start=1):
        target = paths.input / f"input_{index:02d}{source.suffix.lower()}"
        shutil.copy2(source, target)
        items.append(
            ImageItemReport(
                index=index,
                input=str(target.relative_to(paths.root)).replace("\\", "/"),
            )
        )

    save_report(
        BatchReport(
            batch_id=args.batch_id,
            status=BatchStatus.queued,
            total=len(items),
            items=items,
        )
    )
    await process_batch(args.batch_id)
    print(load_report(args.batch_id).model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
