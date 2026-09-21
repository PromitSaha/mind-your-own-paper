from fastapi import FastAPI

from papermind.api.routes import auth, health
from papermind.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title=settings.api_title)
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(health.router, prefix="/health", tags=["health"])

    return app


app = create_app()
