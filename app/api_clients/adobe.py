import asyncio
from pathlib import Path
from typing import Any

import httpx

from app.api_clients.errors import ProviderError, ProviderNotConfiguredError
from app.config import settings


class AdobeAuthClient:
    def configured(self) -> bool:
        return bool(settings.adobe_client_id and settings.adobe_client_secret)

    async def access_token(self, scope: str | None = None) -> str:
        if not self.configured():
            raise ProviderNotConfiguredError(
                "ADOBE_CLIENT_ID and ADOBE_CLIENT_SECRET are required for Adobe calls."
            )
        payload = {
            "grant_type": "client_credentials",
            "client_id": settings.adobe_client_id,
            "client_secret": settings.adobe_client_secret,
            "scope": scope or settings.adobe_scope,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(settings.adobe_token_url, data=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(f"Adobe token request failed: {response.text[:500]}") from exc
        token = response.json().get("access_token")
        if not token:
            raise ProviderError("Adobe token response did not include access_token.")
        return str(token)


class AdobeFireflyClient:
    provider = "adobe_firefly"

    def __init__(self) -> None:
        self.auth = AdobeAuthClient()

    def configured(self) -> bool:
        return self.auth.configured()

    def status(self) -> dict:
        return {
            "provider": self.provider,
            "configured": self.configured(),
            "required_env": ["ADOBE_CLIENT_ID", "ADOBE_CLIENT_SECRET"],
            "capabilities": ["generate_background", "expand_image", "fill_image"],
            "endpoints": {
                "generate_background_async": f"{settings.adobe_firefly_base_url}/v3/images/generate-async"
            },
        }

    async def generate_background(
        self,
        prompt: str,
        output_path: Path,
        *,
        content_class: str = "photo",
    ) -> dict:
        token = await self.auth.access_token()
        payload = {"prompt": prompt, "contentClass": content_class}
        headers = self._headers(token)
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{settings.adobe_firefly_base_url}/v3/images/generate-async",
                headers=headers,
                json=payload,
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(f"Adobe Firefly request failed: {response.text[:500]}") from exc

        job = response.json()
        if self._first_url(job):
            result = job
        else:
            result = await self._poll_job(job.get("statusUrl"), token)
        image_url = self._first_url(result)
        if not image_url:
            raise ProviderError("Adobe Firefly job succeeded but no output image URL was found.")
        await self._download(image_url, output_path)
        return {
            "provider": self.provider,
            "purpose": "generate_background",
            "prompt": prompt,
            "output": str(output_path),
            "job_id": result.get("jobId") or job.get("jobId"),
            "used_external_api": True,
            "endpoint": f"{settings.adobe_firefly_base_url}/v3/images/generate-async",
        }

    async def _poll_job(self, status_url: str | None, token: str) -> dict:
        if not status_url:
            raise ProviderError("Adobe Firefly response did not include statusUrl.")
        headers = self._headers(token)
        async with httpx.AsyncClient(timeout=60) as client:
            for _ in range(settings.adobe_job_poll_attempts):
                response = await client.get(status_url, headers=headers)
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise ProviderError(f"Adobe Firefly status failed: {response.text[:500]}") from exc
                payload = response.json()
                status = payload.get("status")
                if status == "succeeded":
                    return payload
                if status == "failed":
                    raise ProviderError(f"Adobe Firefly job failed: {payload}")
                await asyncio.sleep(settings.adobe_job_poll_interval_seconds)
        raise ProviderError("Adobe Firefly job timed out.")

    async def _download(self, url: str, output_path: Path) -> None:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.get(url)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(f"Adobe Firefly download failed: {response.text[:500]}") from exc
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "x-api-key": settings.adobe_client_id,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _first_url(self, payload: Any) -> str | None:
        if isinstance(payload, dict):
            for key in ("url", "href"):
                value = payload.get(key)
                if isinstance(value, str) and value.startswith("http"):
                    return value
            for value in payload.values():
                found = self._first_url(value)
                if found:
                    return found
        if isinstance(payload, list):
            for value in payload:
                found = self._first_url(value)
                if found:
                    return found
        return None


class AdobePhotoshopClient:
    provider = "adobe_photoshop"

    def __init__(self) -> None:
        self.auth = AdobeAuthClient()

    def configured(self) -> bool:
        return self.auth.configured()

    def status(self) -> dict:
        return {
            "provider": self.provider,
            "configured": self.configured(),
            "required_env": ["ADOBE_CLIENT_ID", "ADOBE_CLIENT_SECRET"],
            "capabilities": ["remove_background_from_signed_url", "mask_from_signed_url"],
            "endpoints": {
                "remove_background": f"{settings.adobe_photoshop_base_url}/v2/remove-background",
                "status": f"{settings.adobe_photoshop_base_url}/v2/status/{{jobId}}",
            },
            "notes": "Adobe Photoshop API requires externally reachable signed source/output URLs.",
        }

    async def remove_background_from_url(
        self,
        source_url: str,
        *,
        mode: str = "cutout",
        media_type: str = "image/png",
    ) -> dict:
        token = await self.auth.access_token(settings.adobe_photoshop_scope)
        payload = {
            "image": {"source": {"url": source_url}},
            "mode": mode,
            "output": {"mediaType": media_type},
        }
        headers = self._headers(token)
        endpoint = f"{settings.adobe_photoshop_base_url}/v2/remove-background"
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(f"Adobe Photoshop request failed: {response.text[:500]}") from exc
        return {
            "provider": self.provider,
            "purpose": "remove_background_from_url",
            "source_url": source_url,
            "mode": mode,
            "used_external_api": True,
            "endpoint": endpoint,
            "job": response.json(),
        }

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "x-api-key": settings.adobe_client_id,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
