# Development Plan: Issue #3 文档上传与解析模块

## Overview
实现多格式文档上传、内容解析和文本提取功能。

## Task Breakdown

### Task 1: document-parser-service
**Description**: 创建文档解析服务，支持多格式文本提取
**Type**: default
**Dependencies**: none
**Files**:
- backend/app/services/__init__.py
- backend/app/services/parser.py

**Requirements**:
- 支持 PDF (pypdf2), DOCX (python-docx), XLSX (openpyxl), MD (markdown)
- 统一接口: parse_document(file_path, file_type) -> str
- 加密文件检测: is_encrypted()
- 错误处理: 损坏文件返回空字符串 + 标记

### Task 2: document-router
**Description**: 创建文档上传和管理 API
**Type**: default
**Dependencies**: document-parser-service
**Files**:
- backend/app/routers/documents.py
- backend/app/services/document_service.py

**Requirements**:
- POST /api/documents/upload: 文件上传 + 解析
- GET /api/documents: 文档列表
- GET /api/documents/{id}: 单个文档
- DELETE /api/documents/{id}: 删除文档
- 文件大小限制 50MB
- 白名单校验: pdf, doc, docx, md, xls, xlsx

### Task 3: unit-tests
**Description**: 完整单元测试
**Type**: default
**Dependencies**: document-parser-service, document-router
**Files**:
- backend/tests/test_parser.py
- backend/tests/test_documents.py

**Requirements**:
- 测试各格式解析
- 测试 API 端点
- 测试错误处理
- 覆盖率 >= 90%

## Dependencies to Add
requirements.txt 需添加:
- pypdf2>=3.0.0
- python-docx>=1.1.0
- openpyxl>=3.1.0
- markdown>=3.5.0
