export type SearchFilters = {
  type?: string;
  folder_id?: number | null;
  tag_ids?: number[];
  date_from?: string | null;
  date_to?: string | null;
};

export type SearchResultItem = {
  doc_id: number;
  file_type: string;
  folder_id: number | null;
  score: number;
  highlight: string;
};

export type SearchResponse = {
  items: SearchResultItem[];
  total: number;
  took_ms: number;
};

export type SearchQueryParams = SearchFilters & {
  q: string;
  skip?: number;
  limit?: number;
};

export function buildSearchParams(params: SearchQueryParams): Record<string, string | number> {
  const trimmed = params.q.trim();
  const output: Record<string, string | number> = { q: trimmed };

  if (params.type) output.type = params.type;
  if (typeof params.folder_id === 'number') output.folder_id = params.folder_id;
  if (params.tag_ids?.length) output.tag_ids = params.tag_ids.join(',');
  if (params.date_from) output.date_from = params.date_from;
  if (params.date_to) output.date_to = params.date_to;
  if (typeof params.skip === 'number') output.skip = params.skip;
  if (typeof params.limit === 'number') output.limit = params.limit;

  return output;
}

