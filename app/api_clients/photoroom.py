from pathlib import Path
import asyncio
from collections import deque
import mimetypes
import random
import re
import threading
import time

import httpx
from PIL import Image

from app.api_clients.errors import ProviderError, ProviderNotConfiguredError, ProviderRateLimitError
from app.config import settings


def _mime_type(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


class _PhotoRoomRequestLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._timestamps: deque[float] = deque()
        self._active_requests = 0
        self._blocked_until = 0.0
        self._blocked_message = ""

    async def wait_for_slot(self) -> None:
        limit = max(1, settings.photoroom_max_requests_per_minute)
        window_seconds = 60.0
        while True:
            with self._lock:
                now = time.monotonic()
                if self._blocked_until > now:
                    retry_after = self._blocked_until - now
                    message = self._blocked_message or "PhotoRoom rate limit is active."
                    raise ProviderRateLimitError(message, retry_after)
                while self._timestamps and now - self._timestamps[0] >= window_seconds:
                    self._timestamps.popleft()
                if len(self._timestamps) < limit:
                    self._timestamps.append(now)
                    return
                wait_seconds = window_seconds - (now - self._timestamps[0])
            await asyncio.sleep(max(wait_seconds, 0.05))

    async def acquire_concurrency(self) -> None:
        while True:
            with self._lock:
                limit = max(1, settings.photoroom_max_concurrency)
                if self._active_requests < limit:
                    self._active_requests += 1
                    return
            await asyncio.sleep(0.05)

    def release_concurrency(self) -> None:
        with self._lock:
            self._active_requests = max(0, self._active_requests - 1)

    def block_for(self, retry_after_seconds: float, message: str) -> None:
        if retry_after_seconds <= 0:
            return
        with self._lock:
            self._blocked_until = max(self._blocked_until, time.monotonic() + retry_after_seconds)
            self._blocked_message = message


_REQUEST_LIMITER = _PhotoRoomRequestLimiter()


class PhotoRoomClient:
    provider = "photoroom"

    def configured(self) -> bool:
        return bool(settings.photoroom_api_key)

    def status(self) -> dict:
        return {
            "provider": self.provider,
            "configured": self.configured(),
            "required_env": ["PHOTOROOM_API_KEY"],
            "capabilities": [
                "remove_background",
                "segmentation_alpha",
                "static_background",
                "ai_background",
                "ai_relight",
                "ai_shadow",
            ],
            "endpoints": {
                "remove_background": settings.photoroom_segment_url,
                "image_editing": settings.photoroom_edit_url,
            },
            "rate_limits": {
                "max_requests_per_minute": settings.photoroom_max_requests_per_minute,
                "max_concurrency": settings.photoroom_max_concurrency,
                "too_many_requests_retries": settings.photoroom_429_max_retries,
            },
        }

    async def remove_background(
        self,
        image_path: Path,
        output_rgba_path: Path,
        output_alpha_path: Path | None = None,
    ) -> dict:
        self._require_configured()
        response = await self._post_binary(
            settings.photoroom_segment_url,
            data={"format": "png"},
            files={
                "image_file": (
                    image_path.name,
                    image_path.read_bytes(),
                    _mime_type(image_path),
                )
            },
            timeout=180,
        )
        output_rgba_path.parent.mkdir(parents=True, exist_ok=True)
        output_rgba_path.write_bytes(response)

        if output_alpha_path:
            output_alpha_path.parent.mkdir(parents=True, exist_ok=True)
            Image.open(output_rgba_path).convert("RGBA").getchannel("A").save(output_alpha_path)

        return {
            "provider": self.provider,
            "purpose": "remove_background",
            "input": str(image_path),
            "output": str(output_rgba_path),
            "alpha": str(output_alpha_path) if output_alpha_path else None,
            "used_external_api": True,
            "endpoint": settings.photoroom_segment_url,
        }

    async def edit_image(
        self,
        image_path: Path,
        output_path: Path,
        *,
        background_image_path: Path | None = None,
        background_prompt: str | None = None,
        guidance_image_path: Path | None = None,
        guidance_scale: float | None = None,
        lighting_mode: str | None = None,
        shadow_mode: str | None = None,
        remove_background: bool | None = None,
        reference_box: str = "originalImage",
        padding: float | None = None,
        output_size: str | None = None,
        max_width: int | None = None,
        max_height: int | None = None,
    ) -> dict:
        self._require_configured()
        data: dict[str, str] = {"referenceBox": reference_box}
        files: dict[str, tuple[str, bytes, str]] = {
            "imageFile": (image_path.name, image_path.read_bytes(), _mime_type(image_path))
        }

        if background_image_path:
            files["background.imageFile"] = (
                background_image_path.name,
                background_image_path.read_bytes(),
                _mime_type(background_image_path),
            )
        if guidance_image_path:
            files["background.guidance.imageFile"] = (
                guidance_image_path.name,
                guidance_image_path.read_bytes(),
                _mime_type(guidance_image_path),
            )
        if background_prompt:
            data["background.prompt"] = background_prompt
        if guidance_scale is not None:
            data["background.guidance.scale"] = str(guidance_scale)
        if lighting_mode:
            data["lighting.mode"] = lighting_mode
        if shadow_mode:
            data["shadow.mode"] = shadow_mode
        if remove_background is not None:
            data["removeBackground"] = "true" if remove_background else "false"
        if padding is not None:
            data["padding"] = str(padding)
        if output_size:
            data["outputSize"] = output_size
        if max_width:
            data["maxWidth"] = str(max_width)
        if max_height:
            data["maxHeight"] = str(max_height)

        headers = {}
        if background_prompt and settings.photoroom_ai_background_model:
            headers["pr-ai-background-model-version"] = settings.photoroom_ai_background_model

        response = await self._post_binary(
            settings.photoroom_edit_url,
            data=data,
            files=files,
            extra_headers=headers,
            timeout=240,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response)
        return {
            "provider": self.provider,
            "purpose": "edit_image",
            "input": str(image_path),
            "output": str(output_path),
            "background_image": str(background_image_path) if background_image_path else None,
            "background_prompt": background_prompt,
            "lighting_mode": lighting_mode,
            "shadow_mode": shadow_mode,
            "used_external_api": True,
            "endpoint": settings.photoroom_edit_url,
        }

    async def relight(
        self,
        image_path: Path,
        output_path: Path,
        *,
        lighting_mode: str = "ai.auto",
    ) -> dict:
        return await self.edit_image(
            image_path,
            output_path,
            lighting_mode=lighting_mode,
            remove_background=False,
            max_width=2000,
            max_height=2000,
        )

    async def add_shadow(
        self,
        image_path: Path,
        output_path: Path,
        *,
        shadow_mode: str = "ai.soft",
        background_color: str = "FFFFFF",
    ) -> dict:
        self._require_configured()
        data = {
            "background.color": background_color,
            "shadow.mode": shadow_mode,
        }
        response = await self._post_binary(
            settings.photoroom_edit_url,
            data=data,
            files={
                "imageFile": (
                    image_path.name,
                    image_path.read_bytes(),
                    _mime_type(image_path),
                )
            },
            timeout=180,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response)
        return {
            "provider": self.provider,
            "purpose": "add_shadow",
            "input": str(image_path),
            "output": str(output_path),
            "shadow_mode": shadow_mode,
            "used_external_api": True,
            "endpoint": settings.photoroom_edit_url,
        }

    def _require_configured(self) -> None:
        if not self.configured():
            raise ProviderNotConfiguredError("PHOTOROOM_API_KEY is required for PhotoRoom calls.")

    async def _post_binary(
        self,
        url: str,
        *,
        data: dict[str, str],
        files: dict[str, tuple[str, bytes, str]],
        extra_headers: dict[str, str] | None = None,
        timeout: int,
    ) -> bytes:
        headers = {"x-api-key": settings.photoroom_api_key}
        headers.update(extra_headers or {})
        max_attempts = max(1, settings.photoroom_429_max_retries + 1)
        last_429_detail = ""
        for attempt in range(1, max_attempts + 1):
            await _REQUEST_LIMITER.wait_for_slot()
            await _REQUEST_LIMITER.acquire_concurrency()
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url, headers=headers, data=data, files=files)
            except httpx.RequestError as exc:
                raise ProviderError(f"PhotoRoom request failed before response: {exc.__class__.__name__}") from exc
            finally:
                _REQUEST_LIMITER.release_concurrency()

            if response.status_code == 429:
                last_429_detail = response.text[:500]
                retry_after = self._retry_after_seconds(response)
                if retry_after and retry_after > 300:
                    message = f"PhotoRoom rate limit active; retry after {int(retry_after)} seconds. {last_429_detail}"
                    _REQUEST_LIMITER.block_for(retry_after, message)
                    raise ProviderRateLimitError(message, retry_after)
                if attempt >= max_attempts:
                    raise ProviderError(f"PhotoRoom request failed: 429 {last_429_detail}")
                if retry_after is None:
                    base = max(0.2, settings.photoroom_429_backoff_seconds)
                    retry_after = min(base * (2 ** (attempt - 1)), 30.0)
                    retry_after += random.uniform(0, min(1.0, retry_after * 0.2))
                await asyncio.sleep(retry_after)
                continue

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = response.text[:500]
                raise ProviderError(f"PhotoRoom request failed: {exc.response.status_code} {detail}") from exc
            return response.content

        retry_after = self._retry_after_seconds(response) if "response" in locals() else None
        message = f"PhotoRoom request failed: 429 {last_429_detail}"
        if retry_after and retry_after > 300:
            _REQUEST_LIMITER.block_for(retry_after, message)
            raise ProviderRateLimitError(message, retry_after)
        raise ProviderError(message)

    def _retry_after_seconds(self, response: httpx.Response) -> float | None:
        raw_value = response.headers.get("Retry-After")
        body_match = re.search(r"available in ([0-9]+(?:\.[0-9]+)?) seconds", response.text)
        if body_match:
            try:
                return float(body_match.group(1))
            except ValueError:
                return None
        if not raw_value:
            return None
        try:
            return max(float(raw_value), 0.2)
        except ValueError:
            return None
