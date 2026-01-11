from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@router.get("/api/health")
async def api_health_check():
    return {"status": "healthy", "version": "1.0.0"}
