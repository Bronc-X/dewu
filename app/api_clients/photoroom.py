from pathlib import Path
import mimetypes

import httpx
from PIL import Image

from app.api_clients.errors import ProviderError, ProviderNotConfiguredError
from app.config import settings


def _mime_type(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


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
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, headers=headers, data=data, files=files)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = response.text[:500]
            raise ProviderError(f"PhotoRoom request failed: {exc.response.status_code} {detail}") from exc
        return response.content

