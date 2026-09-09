"""Pluggable page OCR providers for the consent extraction pipeline."""

import io
import os
from dataclasses import dataclass
from functools import lru_cache

import pytesseract
from PIL import Image


@dataclass(frozen=True)
class OCRResult:
    text: str
    confidence: float | None
    method: str


def configured_provider() -> str:
    provider = os.environ.get("OCR_PROVIDER", "tesseract").strip().lower()
    if provider not in {"tesseract", "google-vision"}:
        raise ValueError("OCR_PROVIDER must be 'tesseract' or 'google-vision'.")
    return provider


def processor_name() -> str:
    return f"native-pdf+{configured_provider()}"


def tesseract_ocr(image: Image.Image) -> OCRResult:
    data = pytesseract.image_to_data(
        image,
        config="--psm 3",
        output_type=pytesseract.Output.DICT,
        timeout=40,
    )
    lines: dict[tuple[int, int, int], list[str]] = {}
    scores: list[float] = []
    for index, word in enumerate(data["text"]):
        if not word.strip():
            continue
        key = (data["block_num"][index], data["par_num"][index], data["line_num"][index])
        lines.setdefault(key, []).append(word)
        confidence = float(data["conf"][index])
        if confidence >= 0:
            scores.append(confidence)
    average = round(sum(scores) / len(scores), 1) if scores else None
    return OCRResult(
        text="\n".join(" ".join(words) for words in lines.values()),
        confidence=average,
        method="Tesseract 5",
    )


@lru_cache(maxsize=4)
def _google_client(endpoint: str):
    try:
        from google.cloud import vision
    except ImportError as exc:
        raise RuntimeError(
            "Google Cloud Vision is not installed. Install backend/requirements.txt."
        ) from exc
    options = {"api_endpoint": endpoint} if endpoint else None
    return vision.ImageAnnotatorClient(client_options=options)


def google_document_ocr(image: Image.Image) -> OCRResult:
    try:
        from google.cloud import vision
    except ImportError as exc:
        raise RuntimeError(
            "Google Cloud Vision is not installed. Install backend/requirements.txt."
        ) from exc

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    request_image = vision.Image(content=buffer.getvalue())

    hints = [
        value.strip()
        for value in os.environ.get("OCR_LANGUAGE_HINTS", "en-t-i0-handwrit").split(",")
        if value.strip()
    ]
    image_context = vision.ImageContext(language_hints=hints) if hints else None
    endpoint = os.environ.get("GOOGLE_CLOUD_VISION_ENDPOINT", "").strip()
    response = _google_client(endpoint).document_text_detection(
        image=request_image,
        image_context=image_context,
        timeout=60,
    )
    if response.error.message:
        raise RuntimeError(f"Google Cloud Vision OCR failed: {response.error.message}")

    annotation = response.full_text_annotation
    scores = [
        float(word.confidence) * 100
        for page in annotation.pages
        for block in page.blocks
        for paragraph in block.paragraphs
        for word in paragraph.words
        if word.confidence > 0
    ]
    average = round(sum(scores) / len(scores), 1) if scores else None
    return OCRResult(
        text=annotation.text or "",
        confidence=average,
        method="Google Cloud Vision DOCUMENT_TEXT_DETECTION",
    )


def recognize(image: Image.Image) -> OCRResult:
    provider = configured_provider()
    if provider == "google-vision":
        try:
            return google_document_ocr(image)
        except Exception:
            if os.environ.get("OCR_GOOGLE_FALLBACK", "false").strip().lower() not in {
                "1",
                "true",
                "yes",
            }:
                raise
            local = tesseract_ocr(image)
            return OCRResult(
                text=local.text,
                confidence=local.confidence,
                method="Tesseract 5 (Google Vision fallback)",
            )
    return tesseract_ocr(image)
