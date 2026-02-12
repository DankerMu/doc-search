import pytest

from app.core.config import settings
from app.core.database import get_db
from app.main import app, lifespan
from app.services import search_service


@pytest.mark.asyncio
async def test_get_health_returns_200_and_correct_json(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "1.0.0"}


@pytest.mark.asyncio
async def test_get_api_health_returns_200_and_correct_json(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "1.0.0"}


@pytest.mark.asyncio
async def test_get_ready_returns_200_and_correct_json(client, monkeypatch):
    monkeypatch.setattr(search_service, "_SEARCH_BACKEND_AVAILABLE", True)
    response = await client.get("/api/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


@pytest.mark.asyncio
async def test_get_ready_returns_503_when_db_not_ready(client, monkeypatch):
    monkeypatch.setattr(search_service, "_SEARCH_BACKEND_AVAILABLE", True)

    class FailingSession:
        async def execute(self, *args, **kwargs):
            raise RuntimeError("db not ready")

    async def override_get_db():
        yield FailingSession()

    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    try:
        response = await client.get("/api/health/ready")
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override

    assert response.status_code == 503
    assert response.json()["detail"] == "Database not ready"


@pytest.mark.asyncio
async def test_get_ready_returns_503_when_search_backend_not_ready(client, monkeypatch):
    monkeypatch.setattr(search_service, "_SEARCH_BACKEND_AVAILABLE", False)
    response = await client.get("/api/health/ready")
    assert response.status_code == 503
    assert response.json()["detail"] == "Search backend not ready"


@pytest.mark.asyncio
async def test_lifespan_creates_upload_dir(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))

    async with lifespan(app):
        assert upload_dir.is_dir()
