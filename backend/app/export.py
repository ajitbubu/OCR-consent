"""Stable JSON export contract for consent extraction records."""

from typing import Any


def build_document_export(document: dict[str, Any]) -> dict[str, Any]:
    fields = {
        field["name"]: {
            "value": field.get("value"),
            "raw_value": field.get("raw_value"),
            "category": field.get("category"),
            "page": field.get("page"),
            "evidence": field.get("evidence", ""),
            "confidence": field.get("confidence"),
            "missing_reason": field.get("missing_reason"),
            "party": field.get("party", "Unassigned"),
            "provenance": field.get("provenance", "extracted"),
        }
        for field in document.get("fields", [])
    }
    return {
        "schema_version": "1.0",
        "record_id": document["id"],
        "source": {
            "filename": document["filename"],
            "file_hash_sha256": document["hash"],
            "extension": document["extension"],
            "size_bytes": document["size"],
        },
        "processing": {
            "status": document["status"],
            "review_status": document["review_status"],
            "document_type": document.get("document_type", "Unknown"),
            "page_count": document.get("page_count", 0),
            "revision": document.get("revision", 0),
            "created_at": document["created_at"],
            "updated_at": document["updated_at"],
            "error": document.get("error"),
        },
        "fields": fields,
        "clauses": [
            {
                "category": clause.get("category"),
                "text": clause.get("text", ""),
                "page": clause.get("page"),
            }
            for clause in document.get("clauses", [])
        ],
        "pages": [
            {
                "number": page["number"],
                "ocr_method": page.get("method"),
                "confidence": page.get("confidence"),
                "populated_pdf_fields": len(page.get("widgets", [])),
            }
            for page in document.get("pages", [])
        ],
        "warnings": document.get("warnings", []),
    }
