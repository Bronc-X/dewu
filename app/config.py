from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_data_dir: Path = Path("data")
    background_dir: Path = Path("assets/backgrounds")
    openai_api_key: str = ""
    vision_api_base_url: str = ""
    vision_api_key: str = ""
    vision_model: str = "gpt-4.1-mini"
    vision_api_retries: int = 2
    vision_api_timeout_seconds: float = 120
    image_api_base_url: str = ""
    image_api_key: str = ""
    image_model: str = "gpt-image-1.5"
    image_quality: str = "medium"
    matting_provider: str = "local"
    compositing_provider: str = "local"
    background_provider: str = "local"
    photoroom_api_key: str = ""
    photoroom_segment_url: str = "https://sdk.photoroom.com/v1/segment"
    photoroom_edit_url: str = "https://image-api.photoroom.com/v2/edit"
    photoroom_ai_background_model: str = ""
    adobe_client_id: str = ""
    adobe_client_secret: str = ""
    adobe_scope: str = "openid,AdobeID,session,additional_info,read_organizations,firefly_api,ff_apis"
    adobe_photoshop_scope: str = "openid,AdobeID,read_organizations"
    adobe_token_url: str = "https://ims-na1.adobelogin.com/ims/token/v3"
    adobe_firefly_base_url: str = "https://firefly-api.adobe.io"
    adobe_photoshop_base_url: str = "https://image.adobe.io"
    adobe_job_poll_attempts: int = 40
    adobe_job_poll_interval_seconds: float = 3
    min_images_per_batch: int = 1
    max_images_per_batch: int = 8
    max_retries_per_image: int = 1
    processing_long_edge: int = 1800
    product_change_review_threshold: float = 32
    product_change_fail_threshold: float = 42

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
