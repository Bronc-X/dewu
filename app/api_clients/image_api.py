import base64
from pathlib import Path

import httpx

from app.api_clients.adobe import AdobeFireflyClient
from app.api_clients.errors import ProviderNotConfiguredError
from app.config import settings


class ImageApiClient:
    def enabled(self) -> bool:
        if settings.background_provider == "adobe_firefly":
            return AdobeFireflyClient().configured()
        if settings.background_provider in {"openai_compatible", "local"}:
            return bool(self._api_key())
        return False

    async def generate_background(self, prompt: str, output_path: Path) -> dict:
        if settings.background_provider == "adobe_firefly":
            return await AdobeFireflyClient().generate_background(prompt, output_path)
        if settings.background_provider not in {"openai_compatible", "local"}:
            raise RuntimeError(f"Unsupported BACKGROUND_PROVIDER: {settings.background_provider}")
        if not self.enabled():
            raise ProviderNotConfiguredError("IMAGE_API_KEY or OPENAI_API_KEY is required.")
        payload = {
            "model": settings.image_model,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1536",
            "quality": settings.image_quality,
            "output_format": "png",
        }
        headers = {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                f"{self._base_url()}/images/generations", headers=headers, json=payload
            )
            response.raise_for_status()
        data = response.json()
        b64_json = data["data"][0]["b64_json"]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(base64.b64decode(b64_json))
        return {
            "provider": "openai_compatible",
            "purpose": "generate_background",
            "output": str(output_path),
            "used_external_api": True,
            "model": settings.image_model,
            "quality": settings.image_quality,
        }

    async def repair_local_region(self, image_path: Path, mask_path: Path) -> dict:
        raise NotImplementedError(
            "repair_local_region must call a real provider or an implemented local image operation."
        )

    def _api_key(self) -> str:
        return settings.image_api_key or settings.openai_api_key

    def _base_url(self) -> str:
        return (settings.image_api_base_url or "https://api.openai.com/v1").rstrip("/")
