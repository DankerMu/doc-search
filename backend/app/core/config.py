from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


from typing import Optional


def _parse_bool(value: str) -> Optional[bool]:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def _parse_cors_origins(value: str) -> Optional[list[str]]:
    raw = value.strip()
    if not raw:
        return None

    # Prefer JSON array syntax: ["http://a", "http://b"]
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
        except Exception:
            return None
        if not isinstance(parsed, list):
            return None
        items = [str(x).strip() for x in parsed]
        return [x for x in items if x]

    # Fallback: comma-separated list: http://a, http://b
    items = [part.strip() for part in raw.split(",")]
    return [x for x in items if x]


@dataclass
class Settings:
    DATABASE_URL: str = "sqlite+aiosqlite:///./doc_search.db"
    UPLOAD_DIR: str = "./uploads"
    INDEX_DIR: str = "./search_index"
    CORS_ORIGINS: list[str] = field(default_factory=lambda: ["*"])
    CORS_ALLOW_CREDENTIALS: bool = False

    def __post_init__(self) -> None:
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            self.DATABASE_URL = database_url

        upload_dir = os.environ.get("UPLOAD_DIR")
        if upload_dir:
            self.UPLOAD_DIR = upload_dir

        index_dir = os.environ.get("INDEX_DIR")
        if index_dir:
            self.INDEX_DIR = index_dir

        cors_origins = os.environ.get("CORS_ORIGINS")
        if cors_origins:
            parsed_origins = _parse_cors_origins(cors_origins)
            if parsed_origins is not None:
                self.CORS_ORIGINS = parsed_origins

        cors_allow_credentials = os.environ.get("CORS_ALLOW_CREDENTIALS")
        if cors_allow_credentials is not None:
            parsed_bool = _parse_bool(cors_allow_credentials)
            if parsed_bool is not None:
                self.CORS_ALLOW_CREDENTIALS = parsed_bool


settings = Settings()
