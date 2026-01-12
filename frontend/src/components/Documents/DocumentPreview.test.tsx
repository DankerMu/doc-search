import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import DocumentPreview from './DocumentPreview';
import { request } from '../../services/api';

vi.mock('../../services/api', () => ({
  request: vi.fn(),
  getApiClient: () => ({ request: vi.fn() }),
  getApiBaseUrl: () => '/api'
}));

describe('DocumentPreview', () => {
  it('loads document detail, highlights query and shows download link', async () => {
    const requestMock = vi.mocked(request);
    requestMock.mockResolvedValue({
      id: 1,
      filename: 'stored.md',
      original_name: 'test.md',
      file_type: 'md',
      file_size: 1024,
      folder_id: null,
      created_at: new Date('2026-01-01T00:00:00.000Z').toISOString(),
      content_text: 'hello world'
    });

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <DocumentPreview open documentId={1} query="hello" onClose={() => undefined} />
      </QueryClientProvider>,
    );

    expect(requestMock).toHaveBeenCalledWith(expect.objectContaining({ method: 'GET', url: '/documents/1' }));

    expect(await screen.findByText('全文')).toBeInTheDocument();
    expect(screen.getByText('hello').tagName.toLowerCase()).toBe('mark');

    const download = screen.getByRole('link', { name: '下载原文件' });
    expect(download).toHaveAttribute('href', '/api/documents/1/file');
  });

  it('shows empty state when content is empty (even with query)', async () => {
    const requestMock = vi.mocked(request);
    requestMock.mockResolvedValue({
      id: 2,
      filename: 'stored.md',
      original_name: 'empty.md',
      file_type: 'md',
      file_size: 0,
      folder_id: null,
      created_at: new Date('2026-01-01T00:00:00.000Z').toISOString(),
      content_text: ''
    });

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <DocumentPreview open documentId={2} query="hello" onClose={() => undefined} />
      </QueryClientProvider>,
    );

    expect(await screen.findByText('暂无内容')).toBeInTheDocument();
  });
});
