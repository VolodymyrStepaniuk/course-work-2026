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


def _get_variants(gray: np.ndarray) -> list[np.ndarray]:
    """
    Generate multiple preprocessed versions of the image to handle 
    different types of damage and lighting conditions.
    """
    variants = [gray]
    
    # 1. Adaptive Thresholding (Excellent for shadows and uneven light)
    variants.append(cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    ))

    # 2. Otsu's Binarization (Great for clean digital labels)
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(otsu)

    # 3. Downscaling (Crucial for high-res images where bars are too wide/thin for pyzbar)
    h, w = gray.shape
    if w > 1000:
        variants.append(cv2.resize(gray, (w // 2, h // 2), interpolation=cv2.INTER_AREA))

    # 4. Strategic Gaussian Blur (Makes 'too perfect' digital images scannable like a camera)
    variants.append(cv2.GaussianBlur(gray, (3, 3), 0))

    # 5. High Contrast CLAHE (Handles glare and low contrast)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    variants.append(clahe.apply(gray))

    # 6. Erosion (Thickens black lines, helps with faded barcodes)
    kernel = np.ones((2, 2), np.uint8)
    variants.append(cv2.erode(gray, kernel, iterations=1))

    # 7. Sharpening (Helps with motion blur)
    sharpen_kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    variants.append(cv2.filter2D(gray, -1, sharpen_kernel))

    return variants


def scan_barcode(image_bytes: bytes) -> list[BarcodeResult]:
    """
    Detect and decode all barcodes / QR-codes present in *image_bytes*.
    Uses a multi-pass preprocessing approach to improve recognition 
    of damaged or poorly lit labels.
    """
    try:
        gray = _bytes_to_gray(image_bytes)
        variants = _get_variants(gray)
        
        # Use a dictionary to store unique results indexed by their content
        unique_results: dict[str, BarcodeResult] = {}

        for img_variant in variants:
            decoded_objects = decode(img_variant)
            
            for obj in decoded_objects:
                try:
                    data = obj.data.decode("utf-8")
                except UnicodeDecodeError:
                    continue

                if data not in unique_results:
                    rect = obj.rect
                    unique_results[data] = BarcodeResult(
                        data=data,
                        type=obj.type,
                        bounding_box=BoundingBox(
                            x=rect.left,
                            y=rect.top,
                            w=rect.width,
                            h=rect.height,
                        ),
                    )
        
        results = list(unique_results.values())

    except InvalidImageError:
        raise
    except Exception as exc:
        logger.exception("Unexpected error during barcode scanning")
        raise BarcodeDecodeError(f"Barcode scanning failed: {exc}") from exc

    logger.debug("Found %d unique barcode(s) across all variants", len(results))
    return results
