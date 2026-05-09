"""
FastAPI application factory.

Run with:
    uvicorn app.main:app --reload
Or directly:
    python -m app.main
"""

import logging
import logging.config
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import uvicorn
from fastapi import FastAPI

from app.config import settings
from app.db.base import Base, engine
from app.exceptions import (
    BarcodeDecodeError,
    InvalidImageError,
    PackageNotFoundError,
    barcode_decode_handler,
    invalid_image_handler,
    package_not_found_handler,
)
from app.routers import packages, verify

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            }
        },
        "root": {"handlers": ["console"], "level": "INFO"},
        "loggers": {
            "app": {"level": "DEBUG", "propagate": True},
        },
    }
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Create DB tables on startup; dispose the engine on shutdown."""
    logger.info("Starting up — creating database tables if needed…")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database ready.")

    yield

    logger.info("Shutting down — disposing DB engine…")
    await engine.dispose()

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="Barcode Verification API",
        description=(
            "Automatic reading and verification of barcodes and QR codes "
            "on warehouse packages.\n\n"
            "**Workflow:**\n"
            "1. `POST /packages` — register a package and get a SKU\n"
            "2. `GET /packages/{sku}/label` — download a print-ready PNG label\n"
            "3. Attach the label to the physical package\n"
            "4. `POST /verify/package` — scan the label image to verify it"
        ),
        version="2.0.0",
        lifespan=lifespan,
    )

    from fastapi.middleware.cors import CORSMiddleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.add_exception_handler(InvalidImageError, invalid_image_handler)
    application.add_exception_handler(BarcodeDecodeError, barcode_decode_handler)
    application.add_exception_handler(PackageNotFoundError, package_not_found_handler)
    application.include_router(packages.router, prefix="/api/v1")
    application.include_router(verify.router, prefix="/api/v1")

    @application.get("/api/v1/health", tags=["Health"])
    def health_check() -> dict[str, str]:
        """Returns a simple liveness signal."""
        return {"status": "ok"}

    return application


app = create_app()

if __name__ == "__main__":
    logger.info("Starting server on %s:%d", settings.api_host, settings.api_port)
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )