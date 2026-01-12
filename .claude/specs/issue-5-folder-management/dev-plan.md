# Development Plan: Issue #5 文件夹管理功能

## Overview
实现文件夹目录管理，支持层级结构和文档组织。

## Task Breakdown

### Task 1: folder-service
**Description**: 创建文件夹服务
**Type**: default
**Dependencies**: none
**Files**:
- backend/app/services/folder_service.py

**Requirements**:
- create_folder(name, parent_id) -> Folder
- get_folder(id) -> Folder
- update_folder(id, name) -> Folder
- delete_folder(id) -> bool (文档移至根目录)
- get_folder_tree() -> List[FolderTree]
- validate_depth(parent_id) -> bool (最多5层)

### Task 2: folder-router
**Description**: 创建文件夹 API 端点
**Type**: default
**Dependencies**: folder-service
**Files**:
- backend/app/routers/folders.py

**Requirements**:
- GET /api/folders: 返回树形结构
- POST /api/folders: 创建文件夹
- PUT /api/folders/{id}: 重命名
- DELETE /api/folders/{id}: 删除
- 集成到 main.py

### Task 3: document-move
**Description**: 文档移动功能
**Type**: default
**Dependencies**: folder-service
**Files**:
- backend/app/routers/documents.py (修改)
- backend/app/services/document_service.py (修改)

**Requirements**:
- POST /api/documents/{id}/move: 移动文档到指定文件夹
- move_document(doc_id, folder_id) -> Document

### Task 4: unit-tests
**Description**: 文件夹功能单元测试
**Type**: default
**Dependencies**: folder-service, folder-router, document-move
**Files**:
- backend/tests/test_folders.py

**Requirements**:
- 测试 CRUD 操作
- 测试层级限制
- 测试删除时文档处理
- 测试树形结构
- 测试文档移动
- 覆盖率 >= 90%
