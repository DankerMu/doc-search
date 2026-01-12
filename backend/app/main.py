from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.database import init_db
from .routers.documents import router as documents_router
from .routers.health import router as health_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    await init_db()
    yield


app = FastAPI(title="Doc Search API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(documents_router)
