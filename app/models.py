from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ItemStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    pass_ = "pass"
    review = "review"
    fail = "fail"


class BatchStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ProjectStatus(str, Enum):
    draft = "draft"
    active = "active"
    processing = "processing"
    review = "review"
    completed = "completed"
    archived = "archived"


class ProjectType(str, Enum):
    new_listing = "new_listing"
    style_reuse = "style_reuse"
    campaign = "campaign"
    buyer_preview = "buyer_preview"


class BackgroundMeta(BaseModel):
    id: str
    file: str
    scene_type: str
    scene_level: str = "L1_product_safe"
    priority: int = 50
    pose_fit: list[str] = Field(default_factory=list)
    sit_support: bool = False
    ground_type: str = "unknown"
    lighting_direction: str = "front"
    color_temperature: str = "cool_neutral"
    depth_of_field: str = "sharp"
    style: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)


class ImageItemReport(BaseModel):
    index: int
    input: str
    final: str | None = None
    status: ItemStatus = ItemStatus.queued
    background_id: str | None = None
    reason: str = ""
    reason_en: str = ""
    suggestion: str = ""
    suggestion_en: str = ""
    elapsed_seconds: float = 0
    attempts: int = 0
    risk_tags: list[str] = Field(default_factory=list)
    debug: dict[str, str] = Field(default_factory=dict)
    metrics: dict[str, float | int | str] = Field(default_factory=dict)
    guardrails: list[dict[str, Any]] = Field(default_factory=list)
    external_calls: list[dict[str, Any]] = Field(default_factory=list)


class BatchReport(BaseModel):
    batch_id: str
    status: BatchStatus
    total: int
    pass_count: int = 0
    review_count: int = 0
    fail_count: int = 0
    items: list[ImageItemReport] = Field(default_factory=list)
    zip_path: str | None = None

    def recompute_counts(self) -> None:
        self.pass_count = sum(1 for item in self.items if item.status == ItemStatus.pass_)
        self.review_count = sum(1 for item in self.items if item.status == ItemStatus.review)
        self.fail_count = sum(1 for item in self.items if item.status == ItemStatus.fail)


class ProjectCreateRequest(BaseModel):
    name: str
    project_type: ProjectType = ProjectType.new_listing
    description: str = ""


class ProjectUpdateRequest(BaseModel):
    name: str | None = None
    project_type: ProjectType | None = None
    description: str | None = None
    status: ProjectStatus | None = None


class ProjectRecord(BaseModel):
    id: str
    name: str
    project_type: ProjectType
    description: str = ""
    status: ProjectStatus = ProjectStatus.draft
    created_at: str
    updated_at: str
    batch_ids: list[str] = Field(default_factory=list)
    asset_count: int = 0
    result_count: int = 0


class PhotoRoomEditRequest(BaseModel):
    image_path: str
    output_path: str | None = None
    background_image_path: str | None = None
    background_prompt: str | None = None
    guidance_image_path: str | None = None
    guidance_scale: float | None = None
    lighting_mode: str | None = None
    shadow_mode: str | None = None
    remove_background: bool | None = None
    padding: float | None = None
    output_size: str | None = None


class PhotoRoomMattingRequest(BaseModel):
    image_path: str
    output_rgba_path: str | None = None
    output_alpha_path: str | None = None


class AdobeFireflyGenerateRequest(BaseModel):
    prompt: str
    output_path: str
    content_class: str = "photo"


class AdobePhotoshopRemoveBackgroundRequest(BaseModel):
    source_url: str
    mode: str = "cutout"
    media_type: str = "image/png"


class BatchPaths(BaseModel):
    root: Path
    input: Path
    final_pass: Path
    final_review: Path
    final_fail: Path
    debug_matte: Path
    debug_composite: Path
    debug_final: Path
    background_used: Path
