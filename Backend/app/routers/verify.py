"""
Verification router.

Contains all endpoints related to package / barcode verification.

Verification is two-tiered:
  1. Label self-consistency  — does the barcode data appear in the OCR text?
  2. Registry check          — does the barcode SKU exist in the database?

Both results are returned independently so the caller can decide on policy.
"""

import logging
import re
import time
import difflib
import json

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import PackageRecord
from app.models import InferenceTiming, PackageResponse, VerificationDetails, VerifyResponse
from app.services.recognizer import extract_text
from app.services.scanner import scan_barcode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verify", tags=["Verification"])


def _normalize(text: str) -> str:
    """
    Normalize a string for fuzzy comparison.

    Strips whitespace, dashes, and underscores, then lowercases.
    Also maps visually similar characters to handle OCR errors.
    Examples
    --------
    "SKU-001"  → "skuooi"
    "SKU OOl"  → "skuooi"
    "sku_001"  → "skuooi"
    """
    text = re.sub(r"[\s\-_]", "", text).lower()
    
    # Map common OCR confusions: 0->o, 1->i, l->i, 2->z, 5->s, 8->b
    text = text.replace("l", "i")
    text = text.translate(str.maketrans("01258", "oizsb"))
    
    return text


@router.post(
    "/package",
    response_model=VerifyResponse,
    summary="Verify a warehouse package label",
    description=(
        "Upload an image of a package label. "
        "Returns two independent verification signals:\n\n"
        "- **verified** — the barcode data appears in the OCR text (self-consistent label)\n"
        "- **registered** — the barcode SKU exists in the package registry (DB lookup)\n\n"
        "A fully trusted package has both flags set to `true`."
    ),
)
async def verify_package(
    file: UploadFile = File(...),
    languages: list[str] | None = Query(
        default=None,
        description=(
            "Pass the parameter multiple times for multiple languages: "
            "`?languages=en&languages=uk`"
        ),
    ),
    db: AsyncSession = Depends(get_db),
) -> VerifyResponse:
    logger.info("Received file: %s (%s)", file.filename, file.content_type)

    image_bytes = await file.read()

    t_start = time.perf_counter()

    lang_tuple = tuple(languages) if languages else None
    
    t_scan_start = time.perf_counter()
    barcodes = scan_barcode(image_bytes)
    t_scan = (time.perf_counter() - t_scan_start) * 1000

    t_ocr_start = time.perf_counter()
    texts = extract_text(image_bytes, lang_tuple)
    t_ocr = (time.perf_counter() - t_ocr_start) * 1000

    full_ocr_text = "".join(_normalize(item.text) for item in texts)

    matched_data: str | None = None
    found_package: PackageRecord | None = None

    t_db_start = time.perf_counter()
    for barcode in barcodes:
        sku_to_verify = barcode.data
        try:
            data_dict = json.loads(barcode.data)
            if isinstance(data_dict, dict) and "sku" in data_dict:
                sku_to_verify = data_dict["sku"]
        except json.JSONDecodeError:
            pass

        norm_barcode = _normalize(sku_to_verify)
        
        if matched_data is None:
            # 1. Exact substring check in full combined text (handles token fragmentation)
            if norm_barcode in full_ocr_text:
                matched_data = sku_to_verify
            else:
                # 2. Fuzzy match against individual tokens (handles OCR misreads)
                for item in texts:
                    norm_item = _normalize(item.text)
                    if len(norm_item) >= len(norm_barcode) * 0.5:
                        ratio = difflib.SequenceMatcher(None, norm_barcode, norm_item).ratio()
                        # If the OCR token is part of a larger string (e.g., 'SKU:WH-302A0167'), 
                        # or has minor typos, check if ratio is high enough or if barcode is a fuzzy substring
                        if ratio >= 0.75 or norm_barcode in norm_item:
                            matched_data = sku_to_verify
                            break

        if found_package is None:
            result = await db.execute(
                select(PackageRecord).where(PackageRecord.sku == sku_to_verify)
            )
            found_package = result.scalar_one_or_none()

        if matched_data is not None and found_package is not None:
            break
    t_db = (time.perf_counter() - t_db_start) * 1000

    is_verified = matched_data is not None
    is_registered = found_package is not None
    
    t_total = (time.perf_counter() - t_start) * 1000

    logger.info(
        "Verification result for %s: verified=%s, registered=%s, matched=%r",
        file.filename,
        is_verified,
        is_registered,
        matched_data,
    )

    return VerifyResponse(
        filename=file.filename or "",
        verified=is_verified,
        registered=is_registered,
        matched_data=matched_data,
        package=PackageResponse.model_validate(found_package) if found_package else None,
        details=VerificationDetails(
            barcodes_found=barcodes,
            texts_found=texts,
        ),
        timing=InferenceTiming(
            total_ms=round(t_total, 2),
            scan_ms=round(t_scan, 2),
            ocr_ms=round(t_ocr, 2),
            db_ms=round(t_db, 2)
        ),
    )
