import pytest

from app.core.config import settings
from app.main import app, lifespan


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
async def test_lifespan_creates_upload_dir(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))

    async with lifespan(app):
        assert upload_dir.is_dir()
