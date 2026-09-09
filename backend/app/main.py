from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import db
from .export import build_document_export
from .ocr import configured_provider
from .service import import_folder, import_sqlite, page_image_path, process_document, stage_bytes


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    db.init()
    yield


app = FastAPI(
    title="OCR Consent API",
    version="0.1.0",
    description="Document OCR, field labeling and consent-record storage.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FolderImportRequest(BaseModel):
    path: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class SqliteImportRequest(BaseModel):
    path: str = Field(min_length=1)
    table: str = Field(min_length=1)
    id_column: str = Field(default="id", min_length=1)
    filename_column: str = Field(default="filename", min_length=1)
    content_column: str = Field(default="content", min_length=1)
    limit: int = Field(default=5, ge=1, le=5)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "database": str(db.DB_PATH), "ocr_provider": configured_provider()}


@app.get("/api/documents")
def documents() -> list[dict]:
    return db.list_documents()


@app.get("/api/documents/{document_id}")
def document(document_id: str) -> dict:
    item = db.get_document(document_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return item


@app.get("/api/documents/{document_id}/export")
def document_export(document_id: str, download: bool = False) -> JSONResponse:
    item = db.get_document(document_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    headers = None
    if download:
        safe_stem = "".join(
            character if character.isalnum() or character in {"-", "_", "."} else "_"
            for character in Path(item["filename"]).stem
        )
        headers = {"Content-Disposition": f'attachment; filename="{safe_stem}.json"'}
    return JSONResponse(content=build_document_export(item), headers=headers)


@app.post("/api/documents", status_code=status.HTTP_202_ACCEPTED)
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile], File(description="Up to five documents")],
) -> dict:
    if not files or len(files) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose between one and five documents.",
        )

    accepted: list[dict] = []
    for upload in files:
        try:
            content = await upload.read()
            staged, duplicate = stage_bytes(upload.filename or "document", content)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if not duplicate:
            background_tasks.add_task(process_document, staged["id"])
        accepted.append(
            {
                "id": staged["id"],
                "filename": staged["filename"],
                "status": staged["status"],
                "duplicate": duplicate,
            }
        )
    return {"documents": accepted}


@app.post("/api/import-folder", status_code=status.HTTP_202_ACCEPTED)
def folder_import(request: FolderImportRequest, background_tasks: BackgroundTasks) -> dict:
    try:
        staged_items = import_folder(Path(request.path), request.limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    results: list[dict] = []
    for staged, duplicate in staged_items:
        if not duplicate:
            background_tasks.add_task(process_document, staged["id"])
        results.append(
            {
                "id": staged["id"],
                "filename": staged["filename"],
                "status": staged["status"],
                "duplicate": duplicate,
            }
        )
    return {"documents": results, "folder": str(Path(request.path).expanduser())}


@app.post("/api/import-sqlite", status_code=status.HTTP_202_ACCEPTED)
def sqlite_import(request: SqliteImportRequest, background_tasks: BackgroundTasks) -> dict:
    try:
        staged_items = import_sqlite(
            Path(request.path),
            table=request.table,
            id_column=request.id_column,
            filename_column=request.filename_column,
            content_column=request.content_column,
            limit=request.limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    results: list[dict] = []
    for staged, duplicate in staged_items:
        if not duplicate:
            background_tasks.add_task(process_document, staged["id"])
        results.append(
            {
                "id": staged["id"],
                "filename": staged["filename"],
                "status": staged["status"],
                "duplicate": duplicate,
            }
        )
    return {"documents": results, "database": str(Path(request.path).expanduser())}


@app.post("/api/documents/{document_id}/process", status_code=status.HTTP_202_ACCEPTED)
def reprocess(document_id: str, background_tasks: BackgroundTasks) -> dict[str, str]:
    item = db.get_document(document_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    background_tasks.add_task(process_document, document_id)
    return {"id": document_id, "status": "queued"}


@app.get("/api/documents/{document_id}/pages/{page_number}/image")
def page_image(document_id: str, page_number: int) -> FileResponse:
    path = page_image_path(document_id, page_number)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page image not found")
    return FileResponse(path, media_type="image/png", filename=f"page-{page_number}.png")
