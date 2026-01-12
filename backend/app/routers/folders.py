from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.folder_service import FolderService

router = APIRouter(prefix="/api/folders", tags=["folders"])


class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None


class FolderUpdate(BaseModel):
    name: str


class FolderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    parent_id: Optional[int]
    created_at: datetime


class FolderTreeNode(BaseModel):
    id: int
    name: str
    parent_id: Optional[int]
    children: List["FolderTreeNode"] = []


FolderTreeNode.model_rebuild()


@router.get("", response_model=List[FolderTreeNode])
async def get_folder_tree(db: AsyncSession = Depends(get_db)):
    service = FolderService(db)
    return await service.get_folder_tree()


@router.post("", response_model=FolderResponse, status_code=201)
async def create_folder(data: FolderCreate, db: AsyncSession = Depends(get_db)):
    service = FolderService(db)
    try:
        folder = await service.create_folder(data.name, data.parent_id)
        return folder
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/{folder_id}", response_model=FolderResponse)
async def get_folder(folder_id: int, db: AsyncSession = Depends(get_db)):
    service = FolderService(db)
    folder = await service.get_folder(folder_id)
    if not folder:
        raise HTTPException(404, "Folder not found")
    return folder


@router.put("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: int, data: FolderUpdate, db: AsyncSession = Depends(get_db)
):
    service = FolderService(db)
    folder = await service.update_folder(folder_id, data.name)
    if not folder:
        raise HTTPException(404, "Folder not found")
    return folder


@router.delete("/{folder_id}")
async def delete_folder(folder_id: int, db: AsyncSession = Depends(get_db)):
    service = FolderService(db)
    success = await service.delete_folder(folder_id)
    if not success:
        raise HTTPException(404, "Folder not found")
    return {"message": "Folder deleted"}
