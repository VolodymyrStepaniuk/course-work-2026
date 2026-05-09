"""
Barcode / QR-code scanning service.

Accepts a **full package photograph** (the entire parcel including label,
packaging material, and surrounding environment).  pyzbar locates and
decodes every barcode / QR code present anywhere in the image, returning
the decoded data together with the pixel-level bounding box of each code.

This bounding box is the primary output consumed by the metrics service
for IoU-based evaluation of detection quality.

Preprocessing pipeline applied before decoding:
  1. Grayscale conversion
  2. CLAHE (adaptive histogram equalisation) — handles uneven lighting
  3. Gaussian blur — reduces sensor noise that can confuse the decoder
"""

import logging

import cv2
import numpy as np
from pyzbar.pyzbar import decode

from app.exceptions import InvalidImageError, BarcodeDecodeError
from app.models import BarcodeResult, BoundingBox

logger = logging.getLogger(__name__)


def _bytes_to_gray(image_bytes: bytes) -> np.ndarray:
    """Decode raw bytes into a grayscale OpenCV image."""
    buffer = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(buffer, cv2.IMREAD_COLOR)

    if img is None:
        raise InvalidImageError(
            "Could not decode the uploaded file as an image. "
            "Make sure you are sending a valid JPEG, PNG, or BMP."
        )

    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def _preprocess(gray: np.ndarray) -> np.ndarray:
    """
    Enhance a grayscale image to improve barcode / QR recognition.

    Steps
    -----
    1. CLAHE — adaptive histogram equalisation; lifts contrast in dark
       or unevenly-lit regions without over-brightening bright ones.
    2. Gaussian blur — removes high-frequency sensor noise that can
       confuse the barcode decoder.
    """
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    denoised = cv2.GaussianBlur(enhanced, (3, 3), 0)
    return denoised


def scan_barcode(image_bytes: bytes) -> list[BarcodeResult]:
    """
    Detect and decode all barcodes / QR-codes present in *image_bytes*.

    Returns a (possibly empty) list of :class:`~app.models.BarcodeResult`.
    Raises :class:`~app.exceptions.InvalidImageError` for unreadable images
    and :class:`~app.exceptions.BarcodeDecodeError` for unexpected failures.
    """
    try:
        gray = _bytes_to_gray(image_bytes)
        preprocessed = _preprocess(gray)
        decoded_objects = decode(preprocessed)
    except InvalidImageError:
        raise
    except Exception as exc:
        logger.exception("Unexpected error during barcode scanning")
        raise BarcodeDecodeError(f"Barcode scanning failed: {exc}") from exc

    results: list[BarcodeResult] = []
    for obj in decoded_objects:
        try:
            data = obj.data.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning("Skipping barcode with non-UTF-8 payload: %r", obj.data)
            continue

        rect = obj.rect
        results.append(
            BarcodeResult(
                data=data,
                type=obj.type,
                bounding_box=BoundingBox(
                    x=rect.left,
                    y=rect.top,
                    w=rect.width,
                    h=rect.height,
                ),
            )
        )

    logger.debug("Found %d barcode(s)", len(results))
    return results
