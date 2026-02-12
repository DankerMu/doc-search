from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services import search_service

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@router.get("/api/health")
async def api_health_check():
    return {"status": "healthy", "version": "1.0.0"}


@router.get("/api/health/ready")
async def ready_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database not ready") from exc

    if not search_service._SEARCH_BACKEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="Search backend not ready")

    return {"status": "ready"}
