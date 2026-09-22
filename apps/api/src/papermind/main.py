from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from papermind.api.routes import auth, health
from papermind.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title=settings.api_title)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(health.router, prefix="/health", tags=["health"])

    return app


app = create_app()
