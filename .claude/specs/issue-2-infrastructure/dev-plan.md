# Development Plan: Issue #2 项目基础设施搭建

## Overview
搭建 FastAPI 后端骨架，包含数据库模型、CORS 配置和健康检查端点。

## Tech Decisions
- Database: SQLite + SQLAlchemy (async)
- Migration: 简化版 (create_all, 无 Alembic)
- Structure: 标准 FastAPI 项目布局

## Task Breakdown

### Task 1: project-skeleton
**Description**: 创建项目骨架和核心配置
**Type**: default
**Dependencies**: none
**Files**:
- backend/requirements.txt
- backend/app/__init__.py
- backend/app/main.py
- backend/app/core/__init__.py
- backend/app/core/config.py
- backend/app/core/database.py

**Requirements**:
- requirements.txt: fastapi, uvicorn, sqlalchemy, aiosqlite, python-multipart, pytest, pytest-asyncio, httpx, pytest-cov
- config.py: Settings class with database URL, upload dir, CORS origins
- database.py: async SQLAlchemy engine, sessionmaker, Base, get_db dependency
- main.py: FastAPI app instance, lifespan for DB init, include routers

**Test**: pytest backend/tests/test_config.py -v

---

### Task 2: data-models
**Description**: 创建 Document, Folder, Tag 数据模型
**Type**: default
**Dependencies**: project-skeleton
**Files**:
- backend/app/models/__init__.py
- backend/app/models/document.py
- backend/app/models/folder.py
- backend/app/models/tag.py

**Requirements**:
- Document: id, filename, original_name, content_text, file_type, file_size, folder_id (FK), created_at, updated_at
- Folder: id, name, parent_id (self-ref FK), created_at
- Tag: id, name, color, created_at
- DocumentTag: association table (document_id, tag_id)
- All models inherit from Base

**Test**: pytest backend/tests/test_models.py -v

---

### Task 3: health-router
**Description**: 健康检查端点和 CORS 中间件
**Type**: default
**Dependencies**: project-skeleton
**Files**:
- backend/app/routers/__init__.py
- backend/app/routers/health.py

**Requirements**:
- GET /health returns {"status": "healthy", "version": "1.0.0"}
- GET /api/health same response (API prefix)
- CORS middleware configured in main.py (allow all origins for dev)

**Test**: pytest backend/tests/test_health.py -v

---

### Task 4: unit-tests
**Description**: 完整单元测试套件
**Type**: default
**Dependencies**: project-skeleton, data-models, health-router
**Files**:
- backend/tests/__init__.py
- backend/tests/conftest.py
- backend/tests/test_config.py
- backend/tests/test_models.py
- backend/tests/test_health.py

**Requirements**:
- conftest.py: async test client fixture, test database fixture
- test_config.py: verify Settings loads correctly
- test_models.py: CRUD operations for Document, Folder, Tag
- test_health.py: health endpoint returns 200 with correct JSON
- Coverage >= 90%

**Test**: pytest backend/tests/ -v --cov=backend/app --cov-report=term-missing

---

## Execution Order
1. project-skeleton (independent)
2. data-models, health-router (parallel, depend on skeleton)
3. unit-tests (depends on all above)

## Success Criteria
- [x] GET /health returns 200
- [x] Database tables created on startup
- [x] All models have proper relationships
- [x] Test coverage >= 90%
