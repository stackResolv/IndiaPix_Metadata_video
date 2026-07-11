"""
IndiaPix Metadata Automation System — FastAPI Application Entry Point
Powered by Claude AI (Anthropic) | IndiaPix Visual Media Pvt. Ltd.
"""

import asyncio
import json
import logging
import logging.handlers
import shutil
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from config import settings


# ═════════════════════════════════════════════════════════════════════════════
# Custom Logging Infrastructure
# ═════════════════════════════════════════════════════════════════════════════

class CorrelationIdFilter(logging.Filter):
    """A logging filter that injects a correlation_id into every log record."""

    _correlation_id: str = ""

    @classmethod
    def set_correlation_id(cls, cid: str) -> None:
        cls._correlation_id = cid

    @classmethod
    def get_correlation_id(cls) -> str:
        return cls._correlation_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = self._correlation_id
        return True


class JsonFormatter(logging.Formatter):
    """Output logs as JSON lines for machine-parsable logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", ""),
        }
        # Include exception info if present
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        if record.exc_text:
            log_entry["exception_text"] = record.exc_text
        # Include any extra fields passed via extra={}
        for key, value in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "message", "module", "msecs", "msg",
                "name", "pathname", "process", "processName",
                "relativeCreated", "stack_info", "thread", "threadName",
                "correlation_id",
            ):
                log_entry[key] = value
        return json.dumps(log_entry, default=str)


def setup_logging() -> None:
    """Configure logging with file rotation, JSON support, and correlation IDs."""
    log_dir = settings.logs_path
    log_file = log_dir / "app.log"
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any pre-existing handlers
    root_logger.handlers.clear()

    # ── Console handler (stdout) ───────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    if settings.log_format == "json":
        console_handler.setFormatter(JsonFormatter(datefmt="%Y-%m-%d %H:%M:%S"))
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s "
                "[correlation_id=%(correlation_id)s]",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    console_handler.addFilter(CorrelationIdFilter())
    root_logger.addHandler(console_handler)

    # ── File handler (rotating) ────────────────────────────────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        filename=str(log_file),
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(JsonFormatter(datefmt="%Y-%m-%d %H:%M:%S"))
    file_handler.addFilter(CorrelationIdFilter())
    root_logger.addHandler(file_handler)

    logging.getLogger(__name__).info(
        f"Logging initialised: level={settings.log_level}, "
        f"format={settings.log_format}, file={log_file}"
    )


logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# Correlation ID Middleware
# ═════════════════════════════════════════════════════════════════════════════

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns a unique correlation ID to every request.
    The ID is injected into log records and returned in the response header.
    If the client sends an 'X-Correlation-ID' header, that value is used.
    """

    async def dispatch(self, request: Request, call_next):
        # Use client-provided ID or generate one
        cid = request.headers.get(
            "X-Correlation-ID",
            str(uuid.uuid4())[:8],
        )
        CorrelationIdFilter.set_correlation_id(cid)

        start_time = time.monotonic()
        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed = time.monotonic() - start_time
            logger.error(
                f"Unhandled exception on {request.method} {request.url.path}: {exc}",
                exc_info=True,
                extra={"request_method": request.method, "request_path": request.url.path, "elapsed_ms": round(elapsed * 1000)},
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "correlation_id": cid},
            )

        elapsed = time.monotonic() - start_time
        response.headers["X-Correlation-ID"] = cid

        # Log every request at INFO level
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code}",
            extra={
                "request_method": request.method,
                "request_path": request.url.path,
                "status_code": response.status_code,
                "elapsed_ms": round(elapsed * 1000),
            },
        )
        return response


# ═════════════════════════════════════════════════════════════════════════════
# Application Setup
# ═════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle events."""
    logger.info("=" * 60)
    logger.info("IndiaPix Metadata Automation System starting up...")
    logger.info(f"Upload directory: {settings.upload_path.resolve()}")
    logger.info(f"Log directory: {settings.logs_path.resolve()}")
    logger.info(f"Log format: {settings.log_format}")
    logger.info(f"Claude model: {settings.claude_model}")
    logger.info(f"Allowed video formats: {', '.join(sorted(settings.allowed_video_extensions))}")
    logger.info(f"Max upload size: {settings.max_upload_size_mb}MB")
    logger.info(f"Stale upload TTL: {settings.upload_ttl_hours}h")
    logger.info(f"Allowed image formats: {', '.join(sorted(settings.allowed_image_extensions))}")

    # Verify FFmpeg is available
    _check_ffmpeg()

    # Verify API key configuration
    _check_api_keys()

    # Ensure upload directory exists
    settings.upload_path.mkdir(parents=True, exist_ok=True)

    # Run initial stale upload cleanup on startup
    from services.storage_service import cleanup_stale_uploads
    try:
        cleaned = cleanup_stale_uploads()
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} stale upload(s) from previous session")
    except Exception as e:
        logger.warning(f"Startup stale upload cleanup failed: {e}")

    # Background task: periodic stale upload cleanup every 15 minutes
    async def _stale_cleanup_loop():
        while True:
            await asyncio.sleep(900)  # 15 minutes
            try:
                from services.storage_service import cleanup_stale_uploads
                cleaned = await asyncio.to_thread(cleanup_stale_uploads)
                if cleaned > 0:
                    logger.info(f"Background cleanup removed {cleaned} stale upload(s)")
            except Exception as e:
                logger.warning(f"Background stale upload cleanup failed: {e}")

    cleanup_task = asyncio.create_task(_stale_cleanup_loop())

    yield

    # Cancel the background task on shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    logger.info("IndiaPix Metadata Automation System shutting down.")


def _check_ffmpeg():
    """Check if FFmpeg/ffprobe are available on PATH."""
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")

    if ffmpeg_path and ffprobe_path:
        logger.info(f"FFmpeg found: {ffmpeg_path}")
        logger.info(f"FFprobe found: {ffprobe_path}")
    else:
        missing = []
        if not ffmpeg_path:
            missing.append("ffmpeg")
        if not ffprobe_path:
            missing.append("ffprobe")
        logger.warning(
            f"{', '.join(missing)} not found on PATH. "
            f"Frame extraction will fail. "
            f"Install FFmpeg: https://ffmpeg.org/download.html"
        )


def _check_api_keys():
    """Validate API key configuration at startup."""
    key_status = settings.validate_api_keys()

    if key_status["claude"]:
        logger.info("Anthropic (Claude) API key is configured.")
    else:
        logger.warning(
            "Anthropic (Claude) API key is NOT configured. "
            "Set ANTHROPIC_API_KEY in .env to use Claude."
        )

    if key_status["openai"]:
        logger.info("OpenAI (GPT-4o) API key is configured.")
    else:
        logger.warning(
            "OpenAI (GPT-4o) API key is NOT configured. "
            "Set OPENAI_API_KEY in .env to use OpenAI."
        )

    if not key_status["claude"] and not key_status["openai"]:
        logger.warning(
            "NO AI PROVIDERS CONFIGURED. "
            "Metadata generation will fail until at least one API key is set."
        )


# Create FastAPI app
app = FastAPI(
    title="IndiaPix Metadata Automation System",
    description="Generate professional stock metadata for video and image files "
                "using Claude AI. Supports Getty Images, Adobe Stock, "
                "Shutterstock, and Pond5.",
    version="1.0.0",
    lifespan=lifespan,
)

# --- Initialise logging before any middleware ---
setup_logging()

# Add correlation ID middleware (runs before all other middleware)
app.add_middleware(CorrelationIdMiddleware)

# CORS middleware — allow frontend (Next.js dev server) to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:5173",  # Vite dev server (alternative)
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID"],
)

# Register API routers
from api.upload import router as upload_router
from api.metadata import router as metadata_router
from api.export import router as export_router
from api.batch import router as batch_router

app.include_router(upload_router)
app.include_router(metadata_router)
app.include_router(export_router)
app.include_router(batch_router)


# Health check endpoint
@app.get("/api/health")
async def health_check(request: Request):
    """Simple health check endpoint."""
    key_status = settings.validate_api_keys()
    cid = CorrelationIdFilter.get_correlation_id()
    return {
        "status": "healthy",
        "version": "1.0.0",
        "correlation_id": cid,
        "ffmpeg_available": shutil.which("ffmpeg") is not None,
        "ffprobe_available": shutil.which("ffprobe") is not None,
        "default_provider": settings.default_provider,
        "claude_configured": key_status["claude"],
        "openai_configured": key_status["openai"],
        "batch_enabled": True,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info",
    )