export type Document = {
  id: number;
  filename: string;
  original_name: string;
  file_type: string;
  file_size: number;
  folder_id: number | null;
  created_at: string;
};

export type DocumentDetail = Document & {
  content_text: string | null;
};

export type DocumentListResponse = {
  items: Document[];
  total: number;
};

export const FILE_TYPE_OPTIONS = [
  { label: 'PDF', value: 'pdf' },
  { label: 'DOC', value: 'doc' },
  { label: 'DOCX', value: 'docx' },
  { label: 'Markdown', value: 'md' },
  { label: 'XLS', value: 'xls' },
  { label: 'XLSX', value: 'xlsx' }
] as const;

export function formatFileSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return '-';
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  const mb = kb / 1024;
  if (mb < 1024) return `${mb.toFixed(1)} MB`;
  const gb = mb / 1024;
  return `${gb.toFixed(1)} GB`;
}

