import sqlite3

from app import db
from app.service import import_folder, import_sqlite, stage_bytes


def test_staging_same_bytes_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "ROOT", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "db-consent.sqlite3")
    db.init()

    first, first_duplicate = stage_bytes("scan.png", b"not-empty")
    second, second_duplicate = stage_bytes("copy.png", b"not-empty")

    assert first_duplicate is False
    assert second_duplicate is True
    assert second["id"] == first["id"]
    assert len(db.list_documents()) == 1


def test_imports_document_blobs_from_read_only_sqlite_source(tmp_path, monkeypatch):
    destination = tmp_path / "destination"
    monkeypatch.setattr(db, "ROOT", destination)
    monkeypatch.setattr(db, "DB_PATH", destination / "db-consent.sqlite3")
    db.init()

    source_path = tmp_path / "source.sqlite3"
    source = sqlite3.connect(source_path)
    source.execute("CREATE TABLE paper_documents (record_id TEXT, filename TEXT, file_blob BLOB)")
    source.execute(
        "INSERT INTO paper_documents VALUES (?, ?, ?)",
        ("record-1", "consent.pdf", b"example-pdf-bytes"),
    )
    source.commit()
    source.close()

    imported = import_sqlite(
        source_path,
        table="paper_documents",
        id_column="record_id",
        filename_column="filename",
        content_column="file_blob",
    )

    assert len(imported) == 1
    document, duplicate = imported[0]
    assert duplicate is False
    assert document["filename"] == "consent.pdf"


def test_folder_import_adopts_existing_file_without_copying(tmp_path, monkeypatch):
    destination = tmp_path / "destination"
    originals = destination / "originals"
    originals.mkdir(parents=True)
    source = originals / "filled-consent.pdf"
    source.write_bytes(b"example-pdf-bytes")
    monkeypatch.setattr(db, "ROOT", destination)
    monkeypatch.setattr(db, "DB_PATH", destination / "db-consent.sqlite3")
    db.init()

    imported = import_folder(originals, limit=20)

    assert len(imported) == 1
    document, duplicate = imported[0]
    assert duplicate is False
    assert document["original_path"] == str(source.resolve())
    assert sorted(path.name for path in originals.iterdir()) == ["filled-consent.pdf"]
