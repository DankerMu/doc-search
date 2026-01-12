import { Alert, Empty, Space } from 'antd';
import { useEffect, useState } from 'react';

import DocumentPreview from '../components/Documents/DocumentPreview';
import FilterPanel from '../components/Search/FilterPanel';
import SearchBar from '../components/Search/SearchBar';
import SearchResults from '../components/Search/SearchResults';
import { useFolders } from '../hooks/useFolders';
import { useSearch } from '../hooks/useSearch';
import { useTags } from '../hooks/useTags';
import useDocumentTitle from '../hooks/useDocumentTitle';
import type { SearchFilters } from '../types/search';

export default function SearchPage() {
  useDocumentTitle('Doc Search - 搜索');

  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<SearchFilters>({});
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [previewDocumentId, setPreviewDocumentId] = useState<number | null>(null);

  const foldersQuery = useFolders();
  const tagsQuery = useTags();
  const searchQuery = useSearch({ query, filters, page, pageSize });

  useEffect(() => {
    setPage(1);
  }, [query, filters]);

  const hasQuery = query.trim().length > 0;

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <SearchBar value={query} onChange={setQuery} loading={searchQuery.isFetching} />

      <FilterPanel
        value={filters}
        onChange={setFilters}
        folders={foldersQuery.data ?? []}
        tags={tagsQuery.data ?? []}
      />

      {!hasQuery ? (
        <Empty description="请输入关键词开始搜索" />
      ) : searchQuery.isError ? (
        <Alert type="error" message="搜索失败" showIcon />
      ) : (
        <SearchResults
          items={searchQuery.data?.items ?? []}
          total={searchQuery.data?.total ?? 0}
          loading={searchQuery.isFetching}
          page={page}
          pageSize={pageSize}
          onPageChange={(nextPage, nextSize) => {
            setPage(nextPage);
            setPageSize(nextSize);
          }}
          onPreview={(documentId) => setPreviewDocumentId(documentId)}
        />
      )}

      <DocumentPreview
        open={previewDocumentId !== null}
        documentId={previewDocumentId}
        query={query}
        onClose={() => setPreviewDocumentId(null)}
      />
    </Space>
  );
}

