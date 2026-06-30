import asyncio
import contextlib
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    import onnxruntime  # noqa: F401
except Exception:  # pragma: no cover - optional unless remove-background is used
    pass

from app.api.v1.routes import api_router
from app.core.config.settings import settings
from app.core.conversion_history import cleanup_expired_files
from app.core.conversion_jobs import start_persistent_conversion_workers
from app.core.conversion_queue import start_conversion_workers
from app.core.security.headers import SecurityHeadersMiddleware


logger = logging.getLogger("polaryix.cleanup")


async def cleanup_loop() -> None:
    default_interval_seconds = max(settings.cleanup_interval_hours, 1) * 60 * 60
    link_interval_seconds = max(settings.link_download_retention_minutes, 1) * 60
    interval_seconds = max(min(default_interval_seconds, link_interval_seconds), 60)
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            cleanup_expired_files()
        except Exception as exc:  # pragma: no cover
            logger.warning("Automatic cleanup failed: %s", exc)


def create_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI."""

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    app.add_middleware(SecurityHeadersMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_origin_regex=settings.allowed_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.on_event("startup")
    async def start_cleanup_task() -> None:
        start_conversion_workers()
        start_persistent_conversion_workers()
        app.state.cleanup_task = asyncio.create_task(cleanup_loop())

    @app.on_event("shutdown")
    async def stop_cleanup_task() -> None:
        task = getattr(app.state, "cleanup_task", None)
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    return app


app = create_app()
