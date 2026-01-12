import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import userEvent from '@testing-library/user-event';
import { act, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import DocumentsPage from './Documents';
import { request } from '../services/api';

vi.mock('../services/api', () => ({
  request: vi.fn(),
  getApiClient: () => ({ request: vi.fn() })
}));

describe('pages/Documents', () => {
  it('lists documents, filters by folder and opens preview', async () => {
    const requestMock = vi.mocked(request);
    requestMock.mockImplementation(async (config: any) => {
      if (config.method === 'GET' && config.url === '/folders') {
        return [{ id: 1, name: 'Root', parent_id: null, children: [{ id: 2, name: 'Child', parent_id: 1, children: [] }] }];
      }
      if (config.method === 'GET' && config.url === '/documents') {
        return {
          items: [
            {
              id: 1,
              filename: 'stored.md',
              original_name: 'a.md',
              file_type: 'md',
              file_size: 10,
              folder_id: config.params?.folder_id ?? null,
              created_at: new Date().toISOString()
            }
          ],
          total: 1
        };
      }
      if (config.method === 'GET' && config.url === '/documents/1') {
        return {
          id: 1,
          filename: 'stored.md',
          original_name: 'a.md',
          file_type: 'md',
          file_size: 10,
          folder_id: 2,
          created_at: new Date().toISOString(),
          content_text: 'content'
        };
      }
      if (config.method === 'GET' && config.url === '/tags') return [];
      throw new Error(`Unexpected request: ${config.method} ${config.url}`);
    });

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const user = userEvent.setup();

    render(
      <QueryClientProvider client={client}>
        <DocumentsPage />
      </QueryClientProvider>,
    );

    expect(await screen.findByText('a.md')).toBeInTheDocument();
    expect(await screen.findByText('Child')).toBeInTheDocument();

    await user.click(screen.getByText('Child'));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(requestMock).toHaveBeenCalledWith(
      expect.objectContaining({ url: '/documents', params: expect.objectContaining({ folder_id: 2 }) }),
    );

    await user.click(screen.getByLabelText('doc-preview-1'));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByText('a.md')).toBeInTheDocument();
    expect(within(dialog).getByText('全文')).toBeInTheDocument();
  });
});
