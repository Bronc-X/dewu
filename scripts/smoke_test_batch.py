import asyncio
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agent.pipeline import process_batch
from app.models import BatchReport, BatchStatus, ImageItemReport
from app.storage import create_batch_dirs, load_report, save_report


SAMPLE_IMAGES = [
    Path("C:/Users/Administrator/Documents/xwechat_files/broncin_80df/temp/RWTemp/2026-06/9268b5ff95f4360f4d9068b95286884c.png"),
    Path("C:/Users/Administrator/Documents/xwechat_files/broncin_80df/temp/RWTemp/2026-06/f949dd67-695d-4d5f-9628-a2f83692c01e/0.png"),
]


async def main() -> None:
    available = [path for path in SAMPLE_IMAGES if path.exists()]
    if not available:
        raise FileNotFoundError("No sample images found.")

    batch_id = "smoke_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = create_batch_dirs(batch_id)
    items = []
    for index in range(1, 9):
        source = available[(index - 1) % len(available)]
        suffix = source.suffix.lower() or ".png"
        target = paths.input / f"input_{index:02d}{suffix}"
        shutil.copy2(source, target)
        items.append(ImageItemReport(index=index, input=str(target.relative_to(paths.root)).replace("\\", "/")))

    save_report(BatchReport(batch_id=batch_id, status=BatchStatus.queued, total=8, items=items))
    await process_batch(batch_id)
    report = load_report(batch_id)
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
