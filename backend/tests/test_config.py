from app.core.config import Settings, settings


def test_settings_loads_with_defaults():
    loaded = Settings()
    assert loaded.DATABASE_URL == "sqlite+aiosqlite:///./doc_search.db"
    assert loaded.UPLOAD_DIR == "./uploads"
    assert loaded.CORS_ORIGINS == ["*"]


def test_database_url_is_set():
    assert isinstance(settings.DATABASE_URL, str)
    assert settings.DATABASE_URL


def test_upload_dir_is_set():
    assert isinstance(settings.UPLOAD_DIR, str)
    assert settings.UPLOAD_DIR

