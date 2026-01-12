from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import jieba
    from whoosh import index
    from whoosh.analysis import Token, Tokenizer
    from whoosh.fields import DATETIME, ID, KEYWORD, TEXT, Schema
    from whoosh.qparser import MultifieldParser, QueryParser
    from whoosh.scoring import BM25F
except ImportError:  # pragma: no cover
    jieba = None
    index = None
    Token = None
    Tokenizer = None
    DATETIME = None
    ID = None
    KEYWORD = None
    TEXT = None
    Schema = None
    MultifieldParser = None
    QueryParser = None
    BM25F = None

from app.core.config import settings


_SEARCH_BACKEND_AVAILABLE = jieba is not None and index is not None

if _SEARCH_BACKEND_AVAILABLE:

    class JiebaTokenizer(Tokenizer):
        """Custom tokenizer using jieba for Chinese text."""

        def __call__(
            self,
            value,
            positions=False,
            chars=False,
            keeporiginal=False,
            removestops=True,
            start_pos=0,
            start_char=0,
            mode="",
            **kwargs,
        ):
            words = jieba.cut_for_search(value)
            pos = start_pos
            char_pos = start_char
            for word in words:
                word = word.strip()
                if not word:
                    continue
                token = Token(positions, chars, removestops=removestops, mode=mode)
                token.text = word
                token.pos = pos
                token.startchar = char_pos
                token.endchar = char_pos + len(word)
                pos += 1
                char_pos += len(word)
                yield token

    def get_jieba_analyzer():
        return JiebaTokenizer()

    # Schema for document index
    SCHEMA = Schema(
        doc_id=ID(stored=True, unique=True),
        content=TEXT(analyzer=get_jieba_analyzer(), stored=True),
        file_type=KEYWORD(stored=True),
        folder_id=ID(stored=True),
        tag_ids=KEYWORD(stored=True, commas=True),
        created_at=DATETIME(stored=True),
    )
else:
    SCHEMA = None


class SearchService:
    def __init__(self, index_dir: Optional[str] = None):
        self.index_dir = Path(index_dir or settings.INDEX_DIR)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._ix = None

    def _require_backend(self) -> None:
        if not _SEARCH_BACKEND_AVAILABLE or SCHEMA is None:
            raise RuntimeError(
                "Search backend is not available. Install 'whoosh' and 'jieba' to enable search."
            )

    @property
    def ix(self):
        self._require_backend()
        if self._ix is None:
            if index.exists_in(str(self.index_dir)):
                self._ix = index.open_dir(str(self.index_dir))
            else:
                self._ix = index.create_in(str(self.index_dir), SCHEMA)
        return self._ix

    def index_document(
        self,
        doc_id: int,
        content: str,
        file_type: str,
        folder_id: Optional[int],
        tag_ids: List[int],
        created_at: datetime,
    ) -> None:
        if not _SEARCH_BACKEND_AVAILABLE:
            return
        writer = self.ix.writer()
        writer.update_document(
            doc_id=str(doc_id),
            content=content or "",
            file_type=file_type,
            folder_id=str(folder_id) if folder_id else "",
            tag_ids=",".join(str(t) for t in tag_ids) if tag_ids else "",
            created_at=created_at,
        )
        writer.commit()

    def remove_document(self, doc_id: int) -> None:
        if not _SEARCH_BACKEND_AVAILABLE:
            return
        writer = self.ix.writer()
        writer.delete_by_term("doc_id", str(doc_id))
        writer.commit()

    def search(
        self,
        query: str,
        file_type: Optional[str] = None,
        folder_id: Optional[int] = None,
        tag_ids: Optional[List[int]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[dict], int]:
        self._require_backend()
        with self.ix.searcher(weighting=BM25F()) as searcher:
            parser = MultifieldParser(["content"], self.ix.schema)
            q = parser.parse(query)

            # Apply filters
            filter_queries = []
            if file_type:
                filter_queries.append(
                    QueryParser("file_type", self.ix.schema).parse(file_type)
                )
            if folder_id:
                filter_queries.append(
                    QueryParser("folder_id", self.ix.schema).parse(str(folder_id))
                )

            results = searcher.search(q, limit=skip + limit + 100)

            # Post-filter and paginate
            filtered = []
            for hit in results:
                if file_type and hit.get("file_type") != file_type:
                    continue
                if folder_id and hit.get("folder_id") != str(folder_id):
                    continue
                if tag_ids:
                    hit_tags = set(hit.get("tag_ids", "").split(","))
                    if not any(str(t) in hit_tags for t in tag_ids):
                        continue
                if date_from and hit.get("created_at") and hit["created_at"] < date_from:
                    continue
                if date_to and hit.get("created_at") and hit["created_at"] > date_to:
                    continue
                filtered.append(hit)

            total = len(filtered)
            paginated = filtered[skip : skip + limit]

            items = []
            for hit in paginated:
                highlighted = self.highlight(hit.get("content", ""), query)
                items.append(
                    {
                        "doc_id": int(hit["doc_id"]),
                        "file_type": hit.get("file_type", ""),
                        "folder_id": int(hit["folder_id"]) if hit.get("folder_id") else None,
                        "score": hit.score,
                        "highlight": highlighted,
                    }
                )

            return items, total

    def highlight(self, content: str, query: str, context_chars: int = 100) -> str:
        if not content or not query:
            return content[:200] if content else ""

        if jieba is None:
            return content[:200] + ("..." if len(content) > 200 else "")

        # Simple highlight: find query terms and extract context
        terms = list(jieba.cut_for_search(query))
        content_lower = content.lower()

        for term in terms:
            term_lower = term.lower()
            idx = content_lower.find(term_lower)
            if idx != -1:
                start = max(0, idx - context_chars)
                end = min(len(content), idx + len(term) + context_chars)
                snippet = content[start:end]
                # Highlight the term
                highlighted = snippet.replace(term, f"<mark>{term}</mark>")
                prefix = "..." if start > 0 else ""
                suffix = "..." if end < len(content) else ""
                return f"{prefix}{highlighted}{suffix}"

        return content[:200] + ("..." if len(content) > 200 else "")


# Singleton instance
_search_service: Optional[SearchService] = None


def get_search_service() -> SearchService:
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service
