"""
Tests for the /verify/package endpoint.

Uses FastAPI's TestClient so no running server is needed.
Heavy ML models (EasyOCR) are mocked to keep tests fast.
"""

from io import BytesIO
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import BarcodeResult, BoundingBox, TextResult

client = TestClient(app)

def _make_image_bytes() -> bytes:
    """Return a minimal 1×1 white PNG as fake image bytes."""
    import struct, zlib

    def _chunk(name: bytes, data: bytes) -> bytes:
        c = name + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff"))
        + _chunk(b"IEND", b"")
    )
    return png


FAKE_IMAGE = _make_image_bytes()

FAKE_BARCODE = BarcodeResult(
    data="SKU-001",
    type="CODE128",
    bounding_box=BoundingBox(x=10, y=10, w=100, h=40),
)

FAKE_TEXT_MATCH = TextResult(text="SKU-001", confidence=0.99)
FAKE_TEXT_NO_MATCH = TextResult(text="WAREHOUSE-B", confidence=0.88)
# OCR sometimes reads "SKU 001" (space) or "SKU_001" (underscore) instead of "SKU-001"
FAKE_TEXT_FUZZY_SPACE = TextResult(text="SKU 001", confidence=0.95)
FAKE_TEXT_FUZZY_CASE = TextResult(text="sku001", confidence=0.91)

class TestHealthCheck:
    def test_returns_ok(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestVerifyPackage:
    @patch("app.routers.verify.scan_barcode", return_value=[FAKE_BARCODE])
    @patch("app.routers.verify.extract_text", return_value=[FAKE_TEXT_MATCH])
    def test_verified_when_barcode_matches_text(self, _mock_ocr, _mock_scan):
        response = client.post(
            "/api/v1/verify/package",
            files={"file": ("label.png", BytesIO(FAKE_IMAGE), "image/png")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["verified"] is True
        assert body["matched_data"] == "SKU-001"

    @patch("app.routers.verify.scan_barcode", return_value=[FAKE_BARCODE])
    @patch("app.routers.verify.extract_text", return_value=[FAKE_TEXT_NO_MATCH])
    def test_not_verified_when_no_match(self, _mock_ocr, _mock_scan):
        response = client.post(
            "/api/v1/verify/package",
            files={"file": ("label.png", BytesIO(FAKE_IMAGE), "image/png")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["verified"] is False
        assert body["matched_data"] is None

    @patch("app.routers.verify.scan_barcode", return_value=[])
    @patch("app.routers.verify.extract_text", return_value=[])
    def test_empty_results(self, _mock_ocr, _mock_scan):
        response = client.post(
            "/api/v1/verify/package",
            files={"file": ("label.png", BytesIO(FAKE_IMAGE), "image/png")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["verified"] is False
        assert body["details"]["barcodes_found"] == []
        assert body["details"]["texts_found"] == []

    def test_missing_file_returns_422(self):
        response = client.post("/api/v1/verify/package")
        assert response.status_code == 422


class TestNormalization:
    """Verify that fuzzy string matching works across OCR formatting variants."""

    @patch("app.routers.verify.scan_barcode", return_value=[FAKE_BARCODE])
    @patch("app.routers.verify.extract_text", return_value=[FAKE_TEXT_FUZZY_SPACE])
    def test_verified_when_ocr_has_spaces(self, _mock_ocr, _mock_scan):
        """Barcode 'SKU-001' should match OCR text 'SKU 001' after normalization."""
        response = client.post(
            "/api/v1/verify/package",
            files={"file": ("label.png", BytesIO(FAKE_IMAGE), "image/png")},
        )
        body = response.json()
        assert body["verified"] is True
        assert body["matched_data"] == "SKU-001"

    @patch("app.routers.verify.scan_barcode", return_value=[FAKE_BARCODE])
    @patch("app.routers.verify.extract_text", return_value=[FAKE_TEXT_FUZZY_CASE])
    def test_verified_when_ocr_is_lowercase(self, _mock_ocr, _mock_scan):
        """Barcode 'SKU-001' should match OCR text 'sku001' after normalization."""
        response = client.post(
            "/api/v1/verify/package",
            files={"file": ("label.png", BytesIO(FAKE_IMAGE), "image/png")},
        )
        body = response.json()
        assert body["verified"] is True
        assert body["matched_data"] == "SKU-001"
