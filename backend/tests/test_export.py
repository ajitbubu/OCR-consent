from app.export import build_document_export


def test_json_export_has_stable_fields_and_omits_local_paths():
    document = {
        "id": "record-123",
        "filename": "consent.pdf",
        "hash": "abc123",
        "extension": ".pdf",
        "size": 42,
        "status": "completed",
        "review_status": "needs_review",
        "document_type": "Consent form",
        "page_count": 1,
        "revision": 2,
        "created_at": "2026-09-08T10:00:00Z",
        "updated_at": "2026-09-08T10:01:00Z",
        "original_path": "/private/consent.pdf",
        "error": None,
        "warnings": ["Review required"],
        "fields": [
            {
                "name": "email",
                "value": "person@example.com",
                "raw_value": "Person@Example.com",
                "category": "Contact",
                "page": 1,
                "evidence": "Email: Person@Example.com",
                "confidence": 97.5,
                "missing_reason": None,
                "party": "Applicant",
                "provenance": "google_vision_label",
            }
        ],
        "clauses": [{"category": "Consent candidate", "text": "I agree", "page": 1}],
        "pages": [{"number": 1, "method": "Google Vision", "confidence": 96.0, "widgets": []}],
    }

    exported = build_document_export(document)

    assert exported["schema_version"] == "1.0"
    assert exported["record_id"] == "record-123"
    assert exported["fields"]["email"]["value"] == "person@example.com"
    assert exported["pages"][0]["ocr_method"] == "Google Vision"
    assert "original_path" not in str(exported)
