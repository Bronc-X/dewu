import base64
import asyncio
import json
import mimetypes
from pathlib import Path

import httpx
from PIL import Image

from app.config import settings


class VisionApiClient:
    def enabled(self) -> bool:
        return bool(self._api_key())

    async def analyze_subject(self, image_path: Path) -> dict:
        if not self.enabled():
            return self._local_subject_fallback(image_path)
        prompt = (
            "Analyze this Dewu ecommerce product-on-model image for a controlled "
            "image-production pipeline. The system must preserve the product, model "
            "identity, pose, logos, shoe shape, clothing pattern, and any real support "
            "object that makes the pose physically valid. Return strict JSON only. "
            "Schema: pose ('standing'|'sitting'|'leaning'), support_required "
            "(boolean), support_kept (boolean), scene_level "
            "('L1_product_safe'|'L2_pose_matched'|'L3_contextual'), product_consistency "
            "('strict'), risk_tags (array of strings). Use risk_tags only from: "
            "transparent_prop, white_screen_edge, green_spill_risk, complex_hair, "
            "seated_support, hand_prop. If the model is seated or touching a "
            "chair/bench/table, support_required must be true and scene_level should "
            "prefer L1_product_safe or L2_pose_matched."
        )
        try:
            result = await self._responses_json(prompt, [image_path])
            pose = result.get("pose", "standing")
            if pose not in {"standing", "sitting", "leaning"}:
                pose = "standing"
            support_required = bool(result.get("support_required", pose == "sitting"))
            support_kept = bool(result.get("support_kept", support_required))
            scene_level = str(result.get("scene_level", "L1_product_safe"))
            if scene_level not in {"L1_product_safe", "L2_pose_matched", "L3_contextual"}:
                scene_level = "L1_product_safe"
            risk_tags = result.get("risk_tags", [])
            if not isinstance(risk_tags, list):
                risk_tags = []
            return {
                "pose": pose,
                "support_required": support_required,
                "support_kept": support_kept,
                "scene_level": scene_level,
                "product_consistency": "strict",
                "risk_tags": [str(tag) for tag in risk_tags],
                "external_call": {
                    "provider": "openai_compatible",
                    "purpose": "analyze_subject",
                    "input": str(image_path),
                    "used_external_api": True,
                    "model": settings.vision_model,
                },
            }
        except Exception as exc:
            fallback = self._local_subject_fallback(image_path)
            fallback["external_call"]["error"] = str(exc)
            return fallback

    async def explain_quality(self, payload: dict, original_path: Path, final_path: Path) -> dict:
        if not self.enabled():
            return payload
        allowed_risk_tags = {
            "product_changed",
            "face_changed",
            "pose_changed",
            "edge_halo",
            "edge_green_spill",
            "edge_feather_too_hard",
            "edge_feather_too_soft",
            "lighting_mismatch",
            "background_too_blurry",
            "hair_edge_lighting_mismatch",
            "support_logic_error",
            "scene_level_mismatch",
        }
        prompt = (
            "You are a strict ecommerce image quality reviewer. Compare the original "
            "product-on-model image and the final composited result. The background "
            "replacement is intentional, so do not treat scene change or background "
            "replacement as a risk by itself. Review or fail only when the product, "
            "model identity, face, pose, support logic, edge quality, lighting match, "
            "scene level, or background clarity is visibly wrong. Product consistency "
            "is the highest priority: product shape, logos, patterns, shoe shape, face, "
            "and pose must not change. Scene hierarchy is: L1_product_safe for clean "
            "commercial backgrounds, L2_pose_matched for support/pose-matched scenes, "
            "and L3_contextual for richer outdoor context. Fail identity/product/support "
            "breakage; review weaker lighting, edge, or scene-level mismatch. Return "
            "strict JSON only with keys: status ('pass'|'review'|'fail'), reason_zh, "
            "reason_en, suggestion_zh, suggestion_en, risk_tags. Use risk_tags only from: "
            "product_changed, face_changed, "
            "pose_changed, edge_halo, edge_green_spill, edge_feather_too_hard, "
            "edge_feather_too_soft, lighting_mismatch, background_too_blurry, "
            "hair_edge_lighting_mismatch, support_logic_error, scene_level_mismatch. "
            "Slight brightness and color temperature changes are acceptable. Be precise "
            "in both Chinese and English. "
            "Existing local assessment: "
            f"{json.dumps(payload, ensure_ascii=False)}"
        )
        try:
            result = await self._responses_json(prompt, [original_path, final_path])
            merged = dict(payload)
            if result.get("status") in {"pass", "review", "fail"}:
                merged["status"] = result["status"]
            if result.get("reason_zh"):
                merged["reason"] = str(result["reason_zh"])
            if result.get("reason_en"):
                merged["reason_en"] = str(result["reason_en"])
            if result.get("suggestion_zh"):
                merged["suggestion"] = str(result["suggestion_zh"])
            if result.get("suggestion_en"):
                merged["suggestion_en"] = str(result["suggestion_en"])
            if isinstance(result.get("risk_tags"), list):
                merged["risk_tags"] = [
                    tag
                    for raw_tag in result["risk_tags"]
                    if (tag := str(raw_tag)) in allowed_risk_tags
                ]
            merged["external_call"] = {
                "provider": "openai_compatible",
                "purpose": "explain_quality",
                "inputs": [str(original_path), str(final_path)],
                "used_external_api": True,
                "model": settings.vision_model,
            }
            return merged
        except Exception as exc:
            merged = dict(payload)
            merged["external_call"] = {
                "provider": "local_fallback",
                "purpose": "explain_quality",
                "used_external_api": False,
                "error": str(exc),
            }
            return merged

    def _local_subject_fallback(self, image_path: Path) -> dict:
        image = Image.open(image_path).convert("RGB")
        width, height = image.size
        ratio = width / max(height, 1)
        pose = "sitting" if ratio > 0.58 else "standing"
        support_required = pose == "sitting"
        risk_tags: list[str] = []
        border = max(8, min(width, height) // 24)
        pixels = []
        pixels.extend(image.crop((0, 0, width, border)).getdata())
        pixels.extend(image.crop((0, height - border, width, height)).getdata())
        pixels.extend(image.crop((0, 0, border, height)).getdata())
        pixels.extend(image.crop((width - border, 0, width, height)).getdata())
        if pixels:
            avg = tuple(sum(channel) / len(pixels) for channel in zip(*pixels))
            if min(avg) > 190 and max(avg) - min(avg) < 32:
                risk_tags.append("white_screen_edge")
            if avg[1] > avg[0] * 1.12 and avg[1] > avg[2] * 1.12:
                risk_tags.append("green_spill_risk")
        return {
            "pose": pose,
            "support_required": support_required,
            "support_kept": support_required,
            "scene_level": "L1_product_safe",
            "product_consistency": "strict",
            "risk_tags": risk_tags,
            "external_call": {
                "provider": "local_fallback",
                "purpose": "analyze_subject",
                "input": str(image_path),
                "used_external_api": False,
            },
        }

    def _api_key(self) -> str:
        return settings.vision_api_key or settings.openai_api_key

    def _base_url(self) -> str:
        return (settings.vision_api_base_url or "https://api.openai.com/v1").rstrip("/")

    def _data_url(self, image_path: Path) -> str:
        mime = mimetypes.guess_type(image_path.name)[0] or "image/png"
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    async def _responses_json(self, prompt: str, image_paths: list[Path]) -> dict:
        content = [{"type": "input_text", "text": prompt}]
        content.extend(
            {"type": "input_image", "image_url": self._data_url(path)}
            for path in image_paths
        )
        payload = {
            "model": settings.vision_model,
            "input": [{"role": "user", "content": content}],
            "text": {"format": {"type": "json_object"}},
        }
        headers = {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
        }
        attempts = max(1, settings.vision_api_retries + 1)
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=settings.vision_api_timeout_seconds) as client:
                    response = await client.post(
                        f"{self._base_url()}/responses", headers=headers, json=payload
                    )
                    response.raise_for_status()
                data = response.json()
                text = self._extract_output_text(data)
                return self._loads_json_object(text)
            except (httpx.HTTPError, json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                if attempt >= attempts:
                    break
                await asyncio.sleep(min(0.5 * attempt, 2.0))
        raise RuntimeError(f"Vision API JSON call failed after {attempts} attempt(s): {last_error}")

    def _extract_output_text(self, response: dict) -> str:
        if isinstance(response.get("output_text"), str):
            return response["output_text"]
        for item in response.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    return content["text"]
        raise ValueError("Vision API response did not include output text.")

    def _loads_json_object(self, text: str) -> dict:
        text = text.strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end <= start:
                raise
            parsed = json.loads(text[start:end + 1])
        if not isinstance(parsed, dict):
            raise ValueError("Vision API response JSON was not an object.")
        return parsed
