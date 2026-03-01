from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.logging_config import setup_logging
from src.config.settings import Settings, get_settings
from src.db.connection import close_pool, create_pool, run_migrations

from .middleware import RequestIDMiddleware
from .routes import courses, health, programs, scrape, universities


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown."""
    settings: Settings = app.state.settings

    # Startup
    setup_logging(settings.LOG_LEVEL)
    await create_pool(settings.DATABASE_URL)
    await run_migrations(settings.DATABASE_URL)

    yield

    # Shutdown
    await close_pool()


def create_app(settings: Settings | None = None) -> FastAPI:
    """FastAPI application factory."""
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="Uni Scraper Pipeline",
        description="AI agentic scraping pipeline for university course catalogs",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.settings = settings

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)

    # Routes
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(scrape.router, prefix="/api/v1")
    app.include_router(universities.router, prefix="/api/v1")
    app.include_router(programs.router, prefix="/api/v1")
    app.include_router(courses.router, prefix="/api/v1")

    return app
