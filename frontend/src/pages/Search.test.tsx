import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import userEvent from '@testing-library/user-event';
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import SearchPage from './Search';
import { request } from '../services/api';

vi.mock('../services/api', () => ({
  request: vi.fn(),
  getApiClient: () => ({ request: vi.fn() })
}));

describe('pages/Search', () => {
  it('debounces search and opens preview', async () => {
    const requestMock = vi.mocked(request);
    const user = userEvent.setup();

    requestMock.mockImplementation(async (config: any) => {
      if (config.method === 'GET' && config.url === '/folders') return [];
      if (config.method === 'GET' && config.url === '/tags') return [];
      if (config.method === 'GET' && config.url === '/search') {
        return {
          items: [
            { doc_id: 1, file_type: 'md', folder_id: null, score: 1, highlight: '<mark>hello</mark>' }
          ],
          total: 1,
          took_ms: 1
        };
      }
      if (config.method === 'GET' && config.url === '/documents/1') {
        return {
          id: 1,
          filename: 'stored.md',
          original_name: 'test.md',
          file_type: 'md',
          file_size: 10,
          folder_id: null,
          created_at: new Date().toISOString(),
          content_text: 'hello world'
        };
      }
      throw new Error(`Unexpected request: ${config.method} ${config.url}`);
    });

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <SearchPage />
      </QueryClientProvider>,
    );

    expect(screen.getByText('请输入关键词开始搜索')).toBeInTheDocument();

    await user.type(screen.getByLabelText('search-input'), 'hello');
    expect(requestMock).not.toHaveBeenCalledWith(expect.objectContaining({ url: '/search' }));

    await new Promise((resolve) => window.setTimeout(resolve, 350));
    expect(await screen.findByText('文档 #1')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '预览' }));
    expect(await screen.findByText('test.md')).toBeInTheDocument();
    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByText('hello').tagName.toLowerCase()).toBe('mark');
  });
});
