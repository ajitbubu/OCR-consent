import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(
    os.environ.get("OCR_DATA_DIR", Path(__file__).resolve().parents[2] / "data")
).resolve()
DB_PATH = ROOT / "db-consent.sqlite3"


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    ROOT.mkdir(parents=True, exist_ok=True)
    database = sqlite3.connect(DB_PATH, timeout=30)
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA foreign_keys=ON")
    try:
        yield database
        database.commit()
    except Exception:
        database.rollback()
        raise
    finally:
        database.close()


def _ensure_column(database: sqlite3.Connection, table: str, name: str, sql_type: str) -> None:
    columns = {row["name"] for row in database.execute(f"PRAGMA table_info({table})")}
    if name not in columns:
        database.execute(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")


def init() -> None:
    with connect() as database:
        database.execute("PRAGMA journal_mode=WAL")
        database.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                hash TEXT UNIQUE NOT NULL,
                extension TEXT NOT NULL,
                size INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                review_status TEXT NOT NULL DEFAULT 'unreviewed',
                document_type TEXT DEFAULT 'Unknown',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                error TEXT,
                page_count INTEGER DEFAULT 0,
                warnings TEXT DEFAULT '[]',
                revision INTEGER DEFAULT 0,
                original_path TEXT
            );
            CREATE TABLE IF NOT EXISTS sources (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                source_type TEXT NOT NULL,
                source_reference TEXT NOT NULL,
                filename TEXT,
                imported_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                processor TEXT NOT NULL,
                error TEXT
            );
            CREATE TABLE IF NOT EXISTS pages (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                number INTEGER NOT NULL,
                text TEXT,
                native_text TEXT,
                method TEXT,
                confidence REAL,
                widgets TEXT,
                image_path TEXT,
                UNIQUE(document_id, number)
            );
            CREATE TABLE IF NOT EXISTS fields (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                value TEXT,
                raw_value TEXT,
                category TEXT,
                page INTEGER,
                evidence TEXT,
                confidence REAL,
                missing_reason TEXT,
                party TEXT DEFAULT 'Unassigned',
                provenance TEXT DEFAULT 'extracted',
                UNIQUE(document_id, name)
            );
            CREATE TABLE IF NOT EXISTS clauses (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                category TEXT,
                text TEXT,
                page INTEGER
            );
            CREATE TABLE IF NOT EXISTS review_history (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                timestamp TEXT NOT NULL,
                reviewer TEXT,
                reason TEXT,
                before_json TEXT,
                after_json TEXT,
                revision INTEGER
            );
            """
        )
        # These keep databases created by the initial scaffold forward compatible.
        _ensure_column(database, "documents", "original_path", "TEXT")
        _ensure_column(database, "sources", "source_type", "TEXT")
        _ensure_column(database, "sources", "source_reference", "TEXT")
        _ensure_column(database, "sources", "filename", "TEXT")
        _ensure_column(database, "pages", "image_path", "TEXT")


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    result = dict(row)
    for key in ("warnings", "widgets"):
        if key in result:
            try:
                result[key] = json.loads(result[key] or "[]")
            except json.JSONDecodeError:
                result[key] = []
    return result


def find_document_by_hash(file_hash: str) -> dict[str, Any] | None:
    with connect() as database:
        return row_to_dict(
            database.execute("SELECT * FROM documents WHERE hash = ?", (file_hash,)).fetchone()
        )


def list_documents() -> list[dict[str, Any]]:
    with connect() as database:
        rows = database.execute(
            """
            SELECT d.*,
                   COUNT(DISTINCT f.id) AS field_count,
                   COUNT(DISTINCT p.id) AS stored_page_count
            FROM documents d
            LEFT JOIN fields f ON f.document_id = d.id
            LEFT JOIN pages p ON p.document_id = d.id
            GROUP BY d.id
            ORDER BY d.created_at DESC
            """
        ).fetchall()
    return [row_to_dict(row) for row in rows if row is not None]


def get_document(document_id: str) -> dict[str, Any] | None:
    with connect() as database:
        document = row_to_dict(
            database.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        )
        if document is None:
            return None
        document["fields"] = [
            row_to_dict(row)
            for row in database.execute(
                """
                SELECT * FROM fields WHERE document_id = ?
                ORDER BY CASE name
                    WHEN 'name' THEN 1
                    WHEN 'email' THEN 2
                    WHEN 'phone' THEN 3
                    WHEN 'consent' THEN 4
                    WHEN 'consent_choice' THEN 5
                    WHEN 'purpose' THEN 6
                    WHEN 'signature' THEN 7
                    WHEN 'notice_version' THEN 8
                    WHEN 'form_version' THEN 9
                    ELSE 99 END
                """,
                (document_id,),
            ).fetchall()
        ]
        document["clauses"] = [
            row_to_dict(row)
            for row in database.execute(
                "SELECT * FROM clauses WHERE document_id = ? ORDER BY page, id", (document_id,)
            ).fetchall()
        ]
        document["pages"] = [
            row_to_dict(row)
            for row in database.execute(
                """
                SELECT id, document_id, number, method, confidence, widgets, image_path
                FROM pages WHERE document_id = ? ORDER BY number
                """,
                (document_id,),
            ).fetchall()
        ]
        return document
