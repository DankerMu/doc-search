from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.tag_service import TagService

router = APIRouter(prefix="/api/tags", tags=["tags"])


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#3B82F6", pattern=r"^#[0-9A-Fa-f]{6}$")


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str
    document_count: int = 0
    created_at: datetime


class DocumentTagRequest(BaseModel):
    tag_id: int


class BatchTagRequest(BaseModel):
    document_ids: List[int]
    tag_ids: List[int]


class BatchTagResponse(BaseModel):
    added: int = 0
    skipped: int = 0
    removed: int = 0


@router.post("", response_model=TagResponse, status_code=201)
async def create_tag(data: TagCreate, db: AsyncSession = Depends(get_db)):
    service = TagService(db)

    # Check for duplicate name
    existing = await service.get_tag_by_name(data.name)
    if existing:
        raise HTTPException(400, "Tag with this name already exists")

    tag = await service.create_tag(data.name, data.color)
    return TagResponse(
        id=tag.id,
        name=tag.name,
        color=tag.color,
        document_count=0,
        created_at=tag.created_at,
    )


@router.get("", response_model=List[TagResponse])
async def list_tags(db: AsyncSession = Depends(get_db)):
    service = TagService(db)
    tags = await service.list_tags()
    return [TagResponse(**t) for t in tags]


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(tag_id: int, db: AsyncSession = Depends(get_db)):
    service = TagService(db)
    tag = await service.get_tag(tag_id)
    if not tag:
        raise HTTPException(404, "Tag not found")

    # Get document count
    tags_with_count = await service.list_tags()
    tag_data = next((t for t in tags_with_count if t["id"] == tag_id), None)
    doc_count = tag_data["document_count"] if tag_data else 0

    return TagResponse(
        id=tag.id,
        name=tag.name,
        color=tag.color,
        document_count=doc_count,
        created_at=tag.created_at,
    )


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: int, data: TagUpdate, db: AsyncSession = Depends(get_db)
):
    service = TagService(db)

    # Check for duplicate name if updating name
    if data.name:
        existing = await service.get_tag_by_name(data.name)
        if existing and existing.id != tag_id:
            raise HTTPException(400, "Tag with this name already exists")

    tag = await service.update_tag(tag_id, data.name, data.color)
    if not tag:
        raise HTTPException(404, "Tag not found")

    # Get document count
    tags_with_count = await service.list_tags()
    tag_data = next((t for t in tags_with_count if t["id"] == tag_id), None)
    doc_count = tag_data["document_count"] if tag_data else 0

    return TagResponse(
        id=tag.id,
        name=tag.name,
        color=tag.color,
        document_count=doc_count,
        created_at=tag.created_at,
    )


@router.delete("/{tag_id}")
async def delete_tag(tag_id: int, db: AsyncSession = Depends(get_db)):
    service = TagService(db)
    success = await service.delete_tag(tag_id)
    if not success:
        raise HTTPException(404, "Tag not found")
    return {"message": "Tag deleted"}


@router.post("/batch-add", response_model=BatchTagResponse)
async def batch_add_tags(data: BatchTagRequest, db: AsyncSession = Depends(get_db)):
    service = TagService(db)
    try:
        result = await service.batch_add_tags(data.document_ids, data.tag_ids)
        return BatchTagResponse(**result)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/batch-remove", response_model=BatchTagResponse)
async def batch_remove_tags(data: BatchTagRequest, db: AsyncSession = Depends(get_db)):
    service = TagService(db)
    result = await service.batch_remove_tags(data.document_ids, data.tag_ids)
    return BatchTagResponse(**result)
