"""
Custom exceptions and FastAPI exception handlers.

Centralising error responses here means route handlers stay clean —
they raise domain exceptions, not HTTP-specific ones.
"""

from fastapi import Request
from fastapi.responses import JSONResponse


class InvalidImageError(ValueError):
    """Raised when the uploaded file cannot be decoded as an image."""


class BarcodeDecodeError(RuntimeError):
    """Raised when barcode decoding fails unexpectedly."""


class PackageNotFoundError(LookupError):
    """Raised when a requested SKU does not exist in the registry."""


async def invalid_image_handler(request: Request, exc: InvalidImageError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


async def barcode_decode_handler(request: Request, exc: BarcodeDecodeError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


async def package_not_found_handler(request: Request, exc: PackageNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})
