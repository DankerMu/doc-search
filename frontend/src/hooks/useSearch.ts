import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { request } from '../services/api';
import type { SearchFilters, SearchResponse } from '../types/search';
import { buildSearchParams } from '../types/search';

export const SEARCH_DEBOUNCE_MS = 300;

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const handle = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(handle);
  }, [delayMs, value]);

  return debounced;
}

export type UseSearchParams = {
  query: string;
  filters: SearchFilters;
  page: number;
  pageSize: number;
};

export function useSearch(params: UseSearchParams) {
  const debouncedQuery = useDebouncedValue(params.query, SEARCH_DEBOUNCE_MS);
  const trimmed = debouncedQuery.trim();
  const enabled = trimmed.length > 0;

  const skip = (params.page - 1) * params.pageSize;
  const limit = params.pageSize;

  return useQuery({
    queryKey: ['search', { q: trimmed, filters: params.filters, skip, limit }],
    enabled,
    queryFn: () =>
      request<SearchResponse>({
        method: 'GET',
        url: '/search',
        params: buildSearchParams({ q: trimmed, ...params.filters, skip, limit })
      }),
    placeholderData: (prev) => prev
  });
}

