"""Application configuration loaded from environment / .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_DIR / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str = "YOUR_GEMINI_API_KEY_HERE"
    gemini_model: str = "gemini-2.5-flash"
    gemini_refine_model: str = "gemini-2.5-flash"

    dr7_api_key: str = ""
    dr7_base_url: str = "https://dr7.ai/api/v1"

    ai_provider: Literal["auto", "dr7", "gemini"] = "auto"

    host: str = "127.0.0.1"
    port: int = 8000

    reports_dir: Path = _BACKEND_DIR / "reports"
    max_upload_files: int = 2000
    max_upload_size_mb: int = 512
    ai_slice_count: int = 8

    app_title: str = "DICOM AI Report API"
    app_version: str = "2.0.0"

    @property
    def reports_path(self) -> Path:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        return self.reports_dir

    @property
    def dr7_enabled(self) -> bool:
        return bool(self.dr7_api_key and self.dr7_api_key.startswith("sk-"))

    @property
    def gemini_enabled(self) -> bool:
        return bool(
            self.gemini_api_key
            and self.gemini_api_key != "YOUR_GEMINI_API_KEY_HERE"
        )

    def resolve_provider(self) -> Literal["dr7", "gemini"]:
        if self.ai_provider == "dr7":
            if not self.dr7_enabled:
                raise ValueError("AI_PROVIDER=dr7 but DR7_API_KEY is not configured")
            return "dr7"
        if self.ai_provider == "gemini":
            if not self.gemini_enabled:
                raise ValueError("AI_PROVIDER=gemini but GEMINI_API_KEY is not configured")
            return "gemini"
        if self.dr7_enabled:
            return "dr7"
        if self.gemini_enabled:
            return "gemini"
        raise ValueError(
            "No AI provider configured. Set DR7_API_KEY and/or GEMINI_API_KEY in backend/.env"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
