from fastapi import FastAPI

from app.api.v1.routes import api_router
from app.core.config.settings import settings
from app.core.security.headers import SecurityHeadersMiddleware


def create_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI."""

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.include_router(api_router)

    return app


app = create_app()