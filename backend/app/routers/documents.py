from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.document_service import DocumentService
from app.services.parser import DocumentParser, MAX_FILE_SIZE, SUPPORTED_TYPES

router = APIRouter(prefix="/api/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    original_name: str
    file_type: str
    file_size: int
    folder_id: Optional[int]
    created_at: datetime


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int


class MoveDocumentRequest(BaseModel):
    folder_id: Optional[int] = None


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    folder_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(400, "Missing filename")

    file_type = DocumentParser.get_file_type(file.filename)
    if not DocumentParser.is_supported(file_type):
        raise HTTPException(400, f"Unsupported file type. Allowed: {SUPPORTED_TYPES}")

    # Stream read with early size check to prevent DoS
    chunks = []
    total_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > MAX_FILE_SIZE:
            raise HTTPException(
                400, f"File too large. Max size: {MAX_FILE_SIZE // 1024 // 1024}MB"
            )
        chunks.append(chunk)

    content = b"".join(chunks)

    service = DocumentService(db)
    document = await service.save_document(file.filename, content, file_type, folder_id)
    return document


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    folder_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    items, total = await service.list_documents(folder_id, skip, limit)
    return DocumentListResponse(items=items, total=total)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: int, db: AsyncSession = Depends(get_db)):
    service = DocumentService(db)
    doc = await service.get_document(document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.post("/{document_id}/move", response_model=DocumentResponse)
async def move_document(
    document_id: int,
    data: MoveDocumentRequest,
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    try:
        doc = await service.move_document(document_id, data.folder_id)
        if not doc:
            raise HTTPException(404, "Document not found")
        return doc
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/{document_id}")
async def delete_document(document_id: int, db: AsyncSession = Depends(get_db)):
    service = DocumentService(db)
    success = await service.delete_document(document_id)
    if not success:
        raise HTTPException(404, "Document not found")
    return {"message": "Document deleted"}


class DocumentTagRequest(BaseModel):
    tag_id: int


@router.post("/{document_id}/tags")
async def add_tag_to_document(
    document_id: int,
    data: DocumentTagRequest,
    db: AsyncSession = Depends(get_db),
):
    from app.services.tag_service import TagService

    service = TagService(db)
    try:
        added = await service.add_tag_to_document(document_id, data.tag_id)
        if added:
            return {"message": "Tag added to document"}
        return {"message": "Document already has this tag"}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/{document_id}/tags/{tag_id}")
async def remove_tag_from_document(
    document_id: int,
    tag_id: int,
    db: AsyncSession = Depends(get_db),
):
    from app.services.tag_service import TagService

    service = TagService(db)
    try:
        removed = await service.remove_tag_from_document(document_id, tag_id)
        if removed:
            return {"message": "Tag removed from document"}
        raise HTTPException(404, "Tag not associated with document")
    except ValueError as e:
        raise HTTPException(400, str(e))
