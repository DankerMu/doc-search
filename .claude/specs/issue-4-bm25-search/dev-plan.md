# Development Plan: Issue #4 BM25 搜索引擎集成

## Overview
集成 Whoosh 搜索引擎，实现 BM25 全文检索、中文分词和关键词高亮。

## Task Breakdown

### Task 1: search-service
**Description**: 创建搜索服务，集成 Whoosh + jieba
**Type**: default
**Dependencies**: none
**Files**:
- backend/app/services/search_service.py

**Requirements**:
- 使用 Whoosh 创建索引 schema (id, content, file_type, folder_id, created_at)
- 集成 jieba 中文分词作为 analyzer
- 实现 index_document(doc_id, content, metadata)
- 实现 remove_document(doc_id)
- 实现 search(query, filters) -> List[SearchResult]
- 实现 highlight(content, query) -> str (前后约100字)
- BM25 评分模型

### Task 2: search-router
**Description**: 创建搜索 API 端点
**Type**: default
**Dependencies**: search-service
**Files**:
- backend/app/routers/search.py

**Requirements**:
- GET /api/search 端点
- 参数: q(查询词), type, folder_id, tag_ids, date_from, date_to, skip, limit
- 返回: items(带高亮), total, took_ms
- 集成到 main.py

### Task 3: document-indexing
**Description**: 文档上传时自动建立索引
**Type**: default
**Dependencies**: search-service
**Files**:
- backend/app/services/document_service.py (修改)

**Requirements**:
- save_document 后调用 search_service.index_document
- delete_document 后调用 search_service.remove_document

### Task 4: unit-tests
**Description**: 搜索功能单元测试
**Type**: default
**Dependencies**: search-service, search-router, document-indexing
**Files**:
- backend/tests/test_search.py

**Requirements**:
- 测试索引创建/删除
- 测试中文搜索
- 测试关键词高亮
- 测试过滤条件
- 测试性能 (< 500ms)
- 覆盖率 >= 90%

## Dependencies to Add
requirements.txt 需添加:
- whoosh>=2.7.4
- jieba>=0.42.1
