from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Settings:
    DATABASE_URL: str = "sqlite+aiosqlite:///./doc_search.db"
    UPLOAD_DIR: str = "./uploads"
    INDEX_DIR: str = "./search_index"
    CORS_ORIGINS: list[str] = field(default_factory=lambda: ["*"])


settings = Settings()
