import time
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.search_service import get_search_service

router = APIRouter(prefix="/api", tags=["search"])


class SearchResultItem(BaseModel):
    doc_id: int
    file_type: str
    folder_id: Optional[int]
    score: float
    highlight: str


class SearchResponse(BaseModel):
    items: List[SearchResultItem]
    total: int
    took_ms: int


@router.get("/search", response_model=SearchResponse)
async def search_documents(
    q: str = Query(..., min_length=1, description="Search query"),
    type: Optional[str] = Query(None, description="Filter by file type"),
    folder_id: Optional[int] = Query(None, description="Filter by folder"),
    tag_ids: Optional[str] = Query(None, description="Filter by tag IDs (comma-separated)"),
    date_from: Optional[datetime] = Query(None, description="Filter by date from"),
    date_to: Optional[datetime] = Query(None, description="Filter by date to"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    start = time.time()

    search_service = get_search_service()

    tag_id_list = None
    if tag_ids:
        try:
            tag_id_list = [int(t.strip()) for t in tag_ids.split(",") if t.strip()]
        except ValueError as exc:
            raise HTTPException(400, "Invalid tag_ids format") from exc

    try:
        items, total = search_service.search(
            query=q,
            file_type=type,
            folder_id=folder_id,
            tag_ids=tag_id_list,
            date_from=date_from,
            date_to=date_to,
            skip=skip,
            limit=limit,
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

    took_ms = int((time.time() - start) * 1000)

    return SearchResponse(
        items=[SearchResultItem(**item) for item in items],
        total=total,
        took_ms=took_ms,
    )
