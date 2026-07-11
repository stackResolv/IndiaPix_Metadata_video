"""
IndiaPix Metadata Automation System — Configuration
Powered by Claude AI (Anthropic) & OpenAI GPT
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # AI Provider selection: "claude" or "openai"
    ai_provider: str = os.getenv("AI_PROVIDER", "claude")

    # Anthropic API
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # OpenAI API
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    # Server
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    # Paths
    upload_dir: str = os.getenv("UPLOAD_DIR", "./temp_uploads")
    base_dir: Path = Path(__file__).parent.resolve()

    # ── Logging Configuration ─────────────────────────────────────────────
    log_dir: str = os.getenv("LOG_DIR", "./logs")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = os.getenv("LOG_FORMAT", "json")  # "text" or "json"
    log_max_bytes: int = int(os.getenv("LOG_MAX_BYTES", "10485760"))  # 10 MB
    log_backup_count: int = int(os.getenv("LOG_BACKUP_COUNT", "10"))

    # Claude API — model is configurable via env; update CLAUDE_MODEL in .env if needed
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    claude_max_tokens: int = 1500
    claude_max_images: int = 20

    # OpenAI API
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 1500
    openai_max_images: int = 20

    # Frame extraction
    frame_max_width: int = 1024
    frame_quality: int = 2  # FFmpeg q:v scale (1=best, 31=worst)

    # Results directory for batch CSVs
    results_dir: str = os.getenv("RESULTS_DIR", "./processed_results")

    # File validation
    max_upload_size_mb: int = 2000
    max_export_body_bytes: int = int(os.getenv("MAX_EXPORT_BODY_BYTES", "5242880"))  # 5 MB
    allowed_video_extensions: set = {".mp4", ".mov", ".avi", ".mxf", ".m4v", ".wmv"}
    allowed_image_extensions: set = {".jpg", ".jpeg", ".png", ".tiff", ".tif"}

    @property
    def upload_path(self) -> Path:
        """Get the upload directory path, creating it if needed."""
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def results_path(self) -> Path:
        """Get the processed results directory path, creating it if needed."""
        path = Path(self.results_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def logs_path(self) -> Path:
        """Get the log directory path, creating it if needed."""
        path = Path(self.log_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def all_allowed_extensions(self) -> set:
        """All supported file extensions (video + image)."""
        return self.allowed_video_extensions | self.allowed_image_extensions

    @property
    def default_provider(self) -> str:
        """Return the default AI provider."""
        return self.ai_provider.lower()

    def validate_api_keys(self) -> dict[str, bool]:
        """Validate API key configuration. Returns dict of provider -> configured status."""
        claude_ok = bool(
            self.anthropic_api_key
            and self.anthropic_api_key != "sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        )
        openai_ok = bool(self.openai_api_key)
        return {"claude": claude_ok, "openai": openai_ok}

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()