"""
OCR service backed by EasyOCR.

The Reader is instantiated lazily and cached per language combination.
A fresh Reader is only created when a new set of languages is first
requested; subsequent calls reuse the cached instance.

EasyOCR language codes (selection):
  English  → "en"
  Ukrainian → "uk"
  German    → "de"
  French    → "fr"
  Polish    → "pl"
Full list: https://www.jaided.ai/easyocr/
"""

import logging
from functools import lru_cache

import easyocr

from app.config import settings
from app.models import TextResult

logger = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def _get_reader(languages: tuple[str, ...]) -> easyocr.Reader:
    """
    Return a cached EasyOCR Reader for the given language tuple.

    ``lru_cache`` requires hashable args, so languages are passed as a
    tuple. Each unique combination is initialised only once — subsequent
    requests with the same languages reuse the cached Reader.
    """
    logger.info(
        "Initialising EasyOCR reader (languages=%s, gpu=%s)",
        list(languages),
        settings.ocr_use_gpu,
    )
    return easyocr.Reader(list(languages), gpu=settings.ocr_use_gpu)


def extract_text(
    image_bytes: bytes,
    languages: tuple[str, ...] | None = None,
) -> list[TextResult]:
    """
    Run OCR on *image_bytes* and return all detected text regions.

    Parameters
    ----------
    image_bytes:
        Raw bytes of the image file.
    languages:
        Tuple of EasyOCR language codes to use, e.g. ``("en", "uk")``.
        When *None*, falls back to ``settings.ocr_languages``.

    Results with confidence below ``settings.min_confidence`` are filtered out.
    Returns a (possibly empty) list of :class:`~app.models.TextResult`.
    """
    lang_key = languages if languages else tuple(settings.ocr_languages)
    reader = _get_reader(lang_key)
    raw_results = reader.readtext(image_bytes)

    results: list[TextResult] = []
    for _bbox, text, confidence in raw_results:
        if confidence < settings.min_confidence:
            logger.debug("Dropping low-confidence text %r (%.2f)", text, confidence)
            continue
        results.append(TextResult(text=text, confidence=round(confidence, 4)))

    logger.debug("Extracted %d text region(s)", len(results))
    return results
