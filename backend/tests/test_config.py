import pytest

from app.core.config import Settings


@pytest.fixture(autouse=True)
def clear_settings_env(monkeypatch):
    # Ensure deterministic tests regardless of developer machine env.
    for key in [
        "DATABASE_URL",
        "UPLOAD_DIR",
        "INDEX_DIR",
        "CORS_ORIGINS",
        "CORS_ALLOW_CREDENTIALS",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_settings_loads_with_defaults():
    loaded = Settings()
    assert loaded.DATABASE_URL == "sqlite+aiosqlite:///./doc_search.db"
    assert loaded.UPLOAD_DIR == "./uploads"
    assert loaded.INDEX_DIR == "./search_index"
    assert loaded.CORS_ORIGINS == ["*"]
    assert loaded.CORS_ALLOW_CREDENTIALS is False


def test_database_url_env_override(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./override.db")
    loaded = Settings()
    assert loaded.DATABASE_URL == "sqlite+aiosqlite:///./override.db"


def test_upload_dir_env_override(monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", "./tmp_uploads")
    loaded = Settings()
    assert loaded.UPLOAD_DIR == "./tmp_uploads"


def test_index_dir_env_override(monkeypatch):
    monkeypatch.setenv("INDEX_DIR", "./tmp_index")
    loaded = Settings()
    assert loaded.INDEX_DIR == "./tmp_index"


def test_cors_origins_json_array(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:5173", "http://example.com"]')
    loaded = Settings()
    assert loaded.CORS_ORIGINS == ["http://localhost:5173", "http://example.com"]


def test_cors_origins_comma_separated(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://a, http://b, ,")
    loaded = Settings()
    assert loaded.CORS_ORIGINS == ["http://a", "http://b"]


def test_cors_allow_credentials_parsing(monkeypatch):
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "true")
    loaded = Settings()
    assert loaded.CORS_ALLOW_CREDENTIALS is True

