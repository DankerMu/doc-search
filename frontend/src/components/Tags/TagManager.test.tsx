import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import userEvent from '@testing-library/user-event';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import TagManager from './TagManager';
import { request } from '../../services/api';

vi.mock('../../services/api', () => ({
  request: vi.fn(),
  getApiClient: () => ({ request: vi.fn() })
}));

describe('TagManager', () => {
  it('lists, creates, edits and deletes tags', async () => {
    const requestMock = vi.mocked(request);
    const existingTag = {
      id: 1,
      name: '合同',
      color: '#000000',
      document_count: 0,
      created_at: new Date().toISOString()
    };

    requestMock.mockImplementation(async (config: any) => {
      if (config.method === 'GET' && config.url === '/tags') return [existingTag];
      if (config.method === 'POST' && config.url === '/tags') return { ...existingTag, id: 2, ...config.data };
      if (config.method === 'PUT' && config.url === '/tags/1') return { ...existingTag, ...config.data };
      if (config.method === 'DELETE' && config.url === '/tags/1') return { message: 'ok' };
      throw new Error(`Unexpected request: ${config.method} ${config.url}`);
    });

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const user = userEvent.setup();

    render(
      <QueryClientProvider client={client}>
        <TagManager />
      </QueryClientProvider>,
    );

    expect(await screen.findByText('合同')).toBeInTheDocument();

    await user.click(screen.getByLabelText('tag-create'));
    await user.type(screen.getByLabelText('tag-name'), '新标签');
    await user.clear(screen.getByLabelText('tag-color'));
    await user.type(screen.getByLabelText('tag-color'), '#112233');
    await user.click(screen.getByRole('button', { name: /保\s*存/ }));

    await waitFor(() =>
      expect(requestMock).toHaveBeenCalledWith(
        expect.objectContaining({ method: 'POST', url: '/tags', data: { name: '新标签', color: '#112233' } }),
      ),
    );

    await user.click(screen.getByLabelText('tag-edit-1'));
    await user.clear(screen.getByLabelText('tag-name'));
    await user.type(screen.getByLabelText('tag-name'), '合同-更新');
    await user.click(screen.getByRole('button', { name: /保\s*存/ }));

    await waitFor(() =>
      expect(requestMock).toHaveBeenCalledWith(
        expect.objectContaining({ method: 'PUT', url: '/tags/1', data: { name: '合同-更新', color: '#000000' } }),
      ),
    );

    await user.click(screen.getByLabelText('tag-delete-1'));
    const confirm = await waitFor(() => {
      const button = document.querySelector<HTMLButtonElement>('.ant-popconfirm-buttons .ant-btn-primary');
      if (!button) throw new Error('Missing confirm button');
      return button;
    });
    await user.click(confirm);

    await waitFor(() =>
      expect(requestMock).toHaveBeenCalledWith(
        expect.objectContaining({ method: 'DELETE', url: '/tags/1' }),
      ),
    );
  });
});
