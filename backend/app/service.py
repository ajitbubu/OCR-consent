import hashlib
import json
import re
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import db
from .extract import extract
from .ocr import processor_name


SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".docx"}
MAX_FILE_BYTES = 50 * 1024 * 1024
SQL_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(filename: str) -> str:
    return Path(filename).name or "document"


def stage_bytes(
    filename: str,
    content: bytes,
    *,
    source_type: str = "upload",
    source_reference: str | None = None,
) -> tuple[dict[str, Any], bool]:
    filename = _safe_filename(filename)
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix or 'none'}")
    if not content:
        raise ValueError("The file is empty.")
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("The file exceeds the 50 MB pilot limit.")

    file_hash = hashlib.sha256(content).hexdigest()
    duplicate = db.find_document_by_hash(file_hash)
    if duplicate is not None:
        return duplicate, True

    document_id = str(uuid.uuid4())
    original_dir = db.ROOT / "originals"
    original_dir.mkdir(parents=True, exist_ok=True)
    original_path = original_dir / f"{document_id}{suffix}"
    original_path.write_bytes(content)
    now = utc_now()

    try:
        with db.connect() as database:
            database.execute(
                """
                INSERT INTO documents (
                    id, filename, hash, extension, size, status, review_status,
                    document_type, created_at, updated_at, warnings, original_path
                ) VALUES (?, ?, ?, ?, ?, 'queued', 'unreviewed', 'Unknown', ?, ?, '[]', ?)
                """,
                (
                    document_id,
                    filename,
                    file_hash,
                    suffix,
                    len(content),
                    now,
                    now,
                    str(original_path.resolve()),
                ),
            )
            database.execute(
                """
                INSERT INTO sources (
                    id, document_id, source_type, source_reference, filename, imported_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    document_id,
                    source_type,
                    source_reference or filename,
                    filename,
                    now,
                ),
            )
    except Exception:
        original_path.unlink(missing_ok=True)
        raise

    document = db.get_document(document_id)
    if document is None:
        raise RuntimeError("The document was staged but could not be read back.")
    return document, False


def stage_file(path: Path) -> tuple[dict[str, Any], bool]:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ValueError(f"File does not exist: {resolved}")
    if resolved.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f"File exceeds the 50 MB pilot limit: {resolved.name}")
    return stage_bytes(
        resolved.name,
        resolved.read_bytes(),
        source_type="folder",
        source_reference=str(resolved),
    )


def stage_existing_file(path: Path) -> tuple[dict[str, Any], bool]:
    """Register a durable folder file without creating a second original copy."""
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ValueError(f"File does not exist: {resolved}")

    suffix = resolved.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix or 'none'}")
    size = resolved.stat().st_size
    if not size:
        raise ValueError("The file is empty.")
    if size > MAX_FILE_BYTES:
        raise ValueError(f"File exceeds the 50 MB pilot limit: {resolved.name}")

    file_hash = hashlib.sha256(resolved.read_bytes()).hexdigest()
    duplicate = db.find_document_by_hash(file_hash)
    if duplicate is not None:
        return duplicate, True

    document_id = str(uuid.uuid4())
    now = utc_now()
    with db.connect() as database:
        database.execute(
            """
            INSERT INTO documents (
                id, filename, hash, extension, size, status, review_status,
                document_type, created_at, updated_at, warnings, original_path
            ) VALUES (?, ?, ?, ?, ?, 'queued', 'unreviewed', 'Unknown', ?, ?, '[]', ?)
            """,
            (
                document_id,
                resolved.name,
                file_hash,
                suffix,
                size,
                now,
                now,
                str(resolved),
            ),
        )
        database.execute(
            """
            INSERT INTO sources (
                id, document_id, source_type, source_reference, filename, imported_at
            ) VALUES (?, ?, 'folder', ?, ?, ?)
            """,
            (str(uuid.uuid4()), document_id, str(resolved), resolved.name, now),
        )

    document = db.get_document(document_id)
    if document is None:
        raise RuntimeError("The document was staged but could not be read back.")
    return document, False


def import_folder(folder: Path, limit: int = 5) -> list[tuple[dict[str, Any], bool]]:
    resolved = folder.expanduser().resolve()
    if not resolved.is_dir():
        raise ValueError(f"Folder does not exist: {resolved}")
    candidates = sorted(
        path for path in resolved.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    return [stage_existing_file(path) for path in candidates[:limit]]


def import_sqlite(
    database_path: Path,
    *,
    table: str,
    id_column: str,
    filename_column: str,
    content_column: str,
    limit: int = 5,
) -> list[tuple[dict[str, Any], bool]]:
    """Import BLOB documents from a read-only SQLite source database.

    Other database engines can implement the same staging contract after their schema is known.
    """
    identifiers = (table, id_column, filename_column, content_column)
    if not all(SQL_IDENTIFIER.fullmatch(identifier) for identifier in identifiers):
        raise ValueError("Table and column names must be simple SQL identifiers.")
    resolved = database_path.expanduser().resolve()
    if not resolved.is_file():
        raise ValueError(f"Source database does not exist: {resolved}")

    query = (
        f'SELECT "{id_column}", "{filename_column}", "{content_column}" '
        f'FROM "{table}" LIMIT ?'
    )
    try:
        source = sqlite3.connect(f"file:{resolved}?mode=ro", uri=True)
        rows = source.execute(query, (limit,)).fetchall()
    except sqlite3.Error as exc:
        raise ValueError(f"Could not read the source database: {exc}") from exc
    finally:
        if "source" in locals():
            source.close()

    imported: list[tuple[dict[str, Any], bool]] = []
    for source_id, filename, content in rows:
        if isinstance(content, memoryview):
            content = content.tobytes()
        if not isinstance(content, bytes):
            raise ValueError(f"Row {source_id} does not contain binary document data.")
        imported.append(
            stage_bytes(
                str(filename),
                content,
                source_type="sqlite",
                source_reference=f"{resolved}#{table}:{source_id}",
            )
        )
    return imported


def process_document(document_id: str) -> None:
    document = db.get_document(document_id)
    if document is None:
        return

    run_id = str(uuid.uuid4())
    started = utc_now()
    with db.connect() as database:
        database.execute(
            "UPDATE documents SET status = 'processing', error = NULL, updated_at = ? WHERE id = ?",
            (started, document_id),
        )
        database.execute(
            """
            INSERT INTO runs (id, document_id, status, started_at, processor)
            VALUES (?, ?, 'processing', ?, ?)
            """,
            (run_id, document_id, started, processor_name()),
        )

    output_dir = db.ROOT / "processed" / document_id
    if output_dir.exists():
        shutil.rmtree(output_dir)

    try:
        result = extract(Path(document["original_path"]), output_dir)
        finished = utc_now()
        with db.connect() as database:
            database.execute("DELETE FROM pages WHERE document_id = ?", (document_id,))
            database.execute("DELETE FROM fields WHERE document_id = ?", (document_id,))
            database.execute("DELETE FROM clauses WHERE document_id = ?", (document_id,))
            for page in result["pages"]:
                database.execute(
                    """
                    INSERT INTO pages (
                        id, document_id, number, text, native_text, method,
                        confidence, widgets, image_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        document_id,
                        page["number"],
                        page.get("text", ""),
                        page.get("native_text", ""),
                        page.get("method"),
                        page.get("confidence"),
                        json.dumps(page.get("widgets", [])),
                        page.get("image_path"),
                    ),
                )
            for field in result["fields"]:
                database.execute(
                    """
                    INSERT INTO fields (
                        id, document_id, name, value, raw_value, category, page,
                        evidence, confidence, missing_reason, party, provenance
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        document_id,
                        field["name"],
                        field.get("value"),
                        field.get("raw_value"),
                        field.get("category"),
                        field.get("page"),
                        field.get("evidence", ""),
                        field.get("confidence"),
                        field.get("missing_reason"),
                        field.get("party", "Unassigned"),
                        field.get("provenance", "extracted"),
                    ),
                )
            for clause in result["clauses"]:
                database.execute(
                    """
                    INSERT INTO clauses (id, document_id, category, text, page)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        document_id,
                        clause.get("category"),
                        clause.get("text"),
                        clause.get("page"),
                    ),
                )
            database.execute(
                """
                UPDATE documents
                SET status = 'completed', review_status = 'needs_review',
                    document_type = ?, page_count = ?, warnings = ?, error = NULL,
                    updated_at = ?, revision = revision + 1
                WHERE id = ?
                """,
                (
                    result["document_type"],
                    len(result["pages"]),
                    json.dumps(result["warnings"]),
                    finished,
                    document_id,
                ),
            )
            database.execute(
                "UPDATE runs SET status = 'completed', finished_at = ? WHERE id = ?",
                (finished, run_id),
            )
    except Exception as exc:
        failed = utc_now()
        with db.connect() as database:
            database.execute(
                "UPDATE documents SET status = 'failed', error = ?, updated_at = ? WHERE id = ?",
                (f"{type(exc).__name__}: {exc}", failed, document_id),
            )
            database.execute(
                "UPDATE runs SET status = 'failed', finished_at = ?, error = ? WHERE id = ?",
                (failed, f"{type(exc).__name__}: {exc}", run_id),
            )


def page_image_path(document_id: str, page_number: int) -> Path | None:
    document = db.get_document(document_id)
    if document is None:
        return None
    for page in document["pages"]:
        if page["number"] == page_number and page.get("image_path"):
            path = Path(page["image_path"]).resolve()
            processed_root = (db.ROOT / "processed").resolve()
            if path.is_file() and processed_root in path.parents:
                return path
    return None
