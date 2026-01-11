# Doc Search

团队文档管理与搜索系统

## Features

- **多格式支持**: PDF, DOC, DOCX, Markdown, Excel
- **BM25 全文检索**: 高效的关键词搜索，结果按相关度排序
- **关键词高亮**: 搜索结果和预览中高亮显示匹配词
- **高级过滤**: 按文件类型、日期范围、标签筛选
- **文档组织**: 文件夹目录 + 标签系统双重分类
- **全文预览**: 无需下载即可查看文档内容

## Tech Stack

**Backend:**
- Python 3.11+ / FastAPI
- Whoosh (BM25 search engine)
- SQLite / PostgreSQL

**Frontend:**
- React 18+ / TypeScript
- Ant Design / shadcn-ui
- Vite

## Quick Start

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Project Structure

```
doc-search/
├── backend/          # FastAPI backend
├── frontend/         # React frontend
├── docs/             # Documentation
└── docker-compose.yml
```

## Documentation

- [PRD](docs/doc-search-prd.md) - Product Requirements Document

## License

MIT
