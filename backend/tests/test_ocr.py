from app import ocr


def test_google_provider_routes_to_document_ocr(monkeypatch):
    expected = ocr.OCRResult("handwritten text", 91.2, "Google Cloud Vision")
    monkeypatch.setenv("OCR_PROVIDER", "google-vision")
    monkeypatch.setattr(ocr, "google_document_ocr", lambda _image: expected)

    assert ocr.recognize(object()) == expected
    assert ocr.processor_name() == "native-pdf+google-vision"


def test_google_provider_can_fall_back_to_local_ocr(monkeypatch):
    monkeypatch.setenv("OCR_PROVIDER", "google-vision")
    monkeypatch.setenv("OCR_GOOGLE_FALLBACK", "true")
    monkeypatch.setattr(ocr, "google_document_ocr", lambda _image: (_ for _ in ()).throw(RuntimeError("unavailable")))
    monkeypatch.setattr(
        ocr,
        "tesseract_ocr",
        lambda _image: ocr.OCRResult("local text", 82.0, "Tesseract 5"),
    )

    result = ocr.recognize(object())

    assert result.text == "local text"
    assert result.method == "Tesseract 5 (Google Vision fallback)"


def test_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("OCR_PROVIDER", "unknown")

    try:
        ocr.configured_provider()
    except ValueError as exc:
        assert "OCR_PROVIDER" in str(exc)
    else:
        raise AssertionError("Unknown provider should fail configuration validation")
