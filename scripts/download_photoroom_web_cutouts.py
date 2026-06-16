import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = (
    ROOT
    / "data"
    / "client_batches"
    / "2026-06-14_photoroom_50_v4"
    / "07_delivery"
    / "manual_test_10_from_link_raw"
)
OUTPUT_DIR = ROOT / "data" / "experiments" / "2026-06-15_web_cutout_image2" / "01_web_cutouts"


async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    images = [
        path
        for path in sorted(INPUT_DIR.iterdir())
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    ][:10]
    if not images:
        raise FileNotFoundError(INPUT_DIR)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(Path.home() / ".codex" / "browser" / "playwright-profile"),
            headless=False,
            accept_downloads=True,
        )
        page = context.pages[0] if context.pages else await context.new_page()
        results = []
        for index, source in enumerate(images, start=1):
            target = OUTPUT_DIR / f"{index:02d}_{source.stem}_web_cutout.png"
            if target.exists():
                results.append({"index": index, "source": str(source), "target": str(target), "cached": True})
                continue

            print(f"[{index}/{len(images)}] upload {source.name}", flush=True)
            await page.goto("https://app.photoroom.com/create", wait_until="domcontentloaded", timeout=120000)
            await page.locator("button").filter(has_text="透明").first.wait_for(timeout=120000)
            await page.wait_for_timeout(2500)

            async with page.expect_file_chooser(timeout=60000) as chooser_info:
                await page.locator("button").filter(has_text="透明").first.click(force=True, timeout=60000)
            chooser = await chooser_info.value
            await chooser.set_files(str(source))

            await page.wait_for_url("**/u/edit/**", timeout=180000)
            await page.get_by_role("button", name="下载").wait_for(timeout=180000)
            await page.wait_for_timeout(3500)
            await page.get_by_role("button", name="下载").click(timeout=60000)
            await page.locator('[role=dialog] button[type="submit"]').wait_for(timeout=120000)
            async with page.expect_download(timeout=180000) as download_info:
                await page.locator('[role=dialog] button[type="submit"]').click(timeout=60000)
            download = await download_info.value
            await download.save_as(str(target))
            results.append(
                {
                    "index": index,
                    "source": str(source),
                    "target": str(target),
                    "suggested": download.suggested_filename,
                }
            )
            print(f"[{index}/{len(images)}] saved {target.name}", flush=True)
            await page.wait_for_timeout(1500)

        (OUTPUT_DIR.parent / "web_cutouts_manifest.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
