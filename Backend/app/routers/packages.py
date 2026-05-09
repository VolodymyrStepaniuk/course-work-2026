"""
Packages router — CRUD for registered warehouse packages + label generation.

Endpoints:
    POST   /packages              — register a new package
    GET    /packages              — list all packages (paginated)
    GET    /packages/{sku}        — get a single package by SKU
    DELETE /packages/{sku}        — remove a package from the registry
    GET    /packages/{sku}/label  — download a print-ready PNG label
"""

import logging
import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import PackageRecord
from app.exceptions import PackageNotFoundError
from app.models import PackageCreate, PackageResponse, PackageUpdate
from app.enums import PackageStatus
from app.services.label import generate_label

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/packages", tags=["Packages"])



def _generate_sku() -> str:
    """Generate a human-readable, unique warehouse SKU."""
    return f"WH-{uuid.uuid4().hex[:8].upper()}"


async def _get_or_404(sku: str, db: AsyncSession) -> PackageRecord:
    result = await db.execute(select(PackageRecord).where(PackageRecord.sku == sku))
    record = result.scalar_one_or_none()
    if record is None:
        raise PackageNotFoundError(f"Package with SKU '{sku}' not found in the registry.")
    return record



@router.post(
    "",
    response_model=PackageResponse,
    status_code=201,
    summary="Register a new package",
)
async def create_package(
    payload: PackageCreate,
    db: AsyncSession = Depends(get_db),
) -> PackageResponse:
    """
    Add a package to the registry. A unique SKU is auto-generated.
    The returned SKU should be encoded into the barcode / QR code
    and printed on the label via **GET /packages/{sku}/label**.
    """
    record = PackageRecord(
        sku=_generate_sku(),
        sender=payload.sender,
        recipient=payload.recipient,
        contents=payload.contents,
        weight_kg=payload.weight_kg,
        destination=payload.destination,
        routing_zone=payload.routing_zone,
        status=PackageStatus.REGISTERED,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)

    logger.info("Registered new package: %s", record.sku)
    return PackageResponse.model_validate(record)


@router.get(
    "",
    response_model=list[PackageResponse],
    summary="List all registered packages",
)
async def list_packages(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
) -> list[PackageResponse]:
    result = await db.execute(
        select(PackageRecord).order_by(PackageRecord.created_at.desc()).offset(skip).limit(limit)
    )
    records = result.scalars().all()
    return [PackageResponse.model_validate(r) for r in records]


@router.get(
    "/{sku}",
    response_model=PackageResponse,
    summary="Get a single package by SKU",
)
async def get_package(
    sku: str,
    db: AsyncSession = Depends(get_db),
) -> PackageResponse:
    record = await _get_or_404(sku, db)
    return PackageResponse.model_validate(record)


@router.patch(
    "/{sku}",
    response_model=PackageResponse,
    summary="Update an existing package",
)
async def update_package(
    sku: str,
    payload: PackageUpdate,
    db: AsyncSession = Depends(get_db),
) -> PackageResponse:
    record = await _get_or_404(sku, db)

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(record, key, value)

    await db.flush()
    await db.refresh(record)
    logger.info("Updated package: %s", sku)

    return PackageResponse.model_validate(record)


@router.delete(
    "/{sku}",
    status_code=204,
    summary="Remove a package from the registry",
)
async def delete_package(
    sku: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    record = await _get_or_404(sku, db)
    await db.delete(record)
    logger.info("Deleted package: %s", sku)


@router.get(
    "/{sku}/label",
    response_class=Response,
    summary="Generate a print-ready PNG label",
    responses={200: {"content": {"image/png": {}}}},
)
async def get_label(
    sku: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Returns a PNG image of the warehouse label for the given package.

    The label contains:
    - All package metadata as human-readable text (for OCR)
    - A QR code encoding the SKU (for barcode scanning)

    Print this label, attach it to the package, then use
    **POST /verify/package** to verify it.
    """
    record = await _get_or_404(sku, db)

    png_bytes = generate_label(
        sku=record.sku,
        sender=record.sender,
        recipient=record.recipient,
        contents=record.contents,
        weight_kg=record.weight_kg,
        destination=record.destination,
        routing_zone=record.routing_zone,
        created_at=record.created_at,
    )

    logger.info("Generated label for package: %s", sku)
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{sku}_label.png"'},
    )
