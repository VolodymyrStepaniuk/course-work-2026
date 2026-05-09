"""
Pydantic schemas for API request and response payloads.

Keeping models in a dedicated file ensures a single source of truth
for data shapes and makes OpenAPI docs auto-generated correctly.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import PackageStatus


class InferenceTiming(BaseModel):
    """Wall-clock time (ms) for each stage of verification."""
    total_ms: float
    scan_ms: float
    ocr_ms: float
    db_ms: float

class BoundingBox(BaseModel):
    x: int
    y: int
    w: int
    h: int


class BarcodeResult(BaseModel):
    data: str
    type: str
    bounding_box: BoundingBox


class TextResult(BaseModel):
    text: str
    confidence: float = Field(ge=0.0, le=1.0)


class PackageCreate(BaseModel):
    """Payload for registering a new package."""

    sender: str = Field(min_length=1, max_length=200, examples=["Logistic Plus LLC"])
    recipient: str = Field(min_length=1, max_length=200, examples=["John Doe"])
    contents: str = Field(min_length=1, max_length=500, examples=["UTP Cat.6 Cable, 10m"])
    weight_kg: float = Field(gt=0, examples=[2.3])
    destination: str = Field(min_length=1, max_length=200, examples=["Central Warehouse"])
    routing_zone: str = Field(min_length=1, max_length=50, examples=["A-12"])


class PackageUpdate(BaseModel):
    """Payload for updating an existing package."""

    sender: str | None = Field(None, min_length=1, max_length=200)
    recipient: str | None = Field(None, min_length=1, max_length=200)
    contents: str | None = Field(None, min_length=1, max_length=500)
    weight_kg: float | None = Field(None, gt=0)
    destination: str | None = Field(None, min_length=1, max_length=200)
    routing_zone: str | None = Field(None, min_length=1, max_length=50)
    status: PackageStatus | None = None


class PackageResponse(BaseModel):
    """Package data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    sku: str
    sender: str
    recipient: str
    contents: str
    weight_kg: float
    destination: str
    routing_zone: str
    status: PackageStatus
    created_at: datetime


class VerificationDetails(BaseModel):
    barcodes_found: list[BarcodeResult]
    texts_found: list[TextResult]


class VerifyResponse(BaseModel):
    filename: str
    verified: bool
    """True when the barcode data is found in the OCR text (label is self-consistent)."""
    registered: bool
    """True when the barcode SKU exists in the package registry (DB)."""
    matched_data: str | None
    package: PackageResponse | None
    """Full package record if the SKU was found in the registry."""
    details: VerificationDetails
    timing: InferenceTiming
    """Wall-clock inference time breakdown in milliseconds."""
