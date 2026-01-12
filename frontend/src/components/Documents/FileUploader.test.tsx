import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import userEvent from '@testing-library/user-event';
import { render, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import FileUploader from './FileUploader';
import { getApiClient } from '../../services/api';

vi.mock('../../services/api', () => ({
  request: vi.fn(),
  getApiClient: vi.fn()
}));

describe('FileUploader', () => {
  it('uploads file with folder_id', async () => {
    const apiClientRequestMock = vi.fn(async (config: any) => {
      config.onUploadProgress?.({ loaded: 50, total: 100 });
      return {
        data: {
          id: 1,
          filename: 'stored.md',
          original_name: 'test.md',
          file_type: 'md',
          file_size: 10,
          folder_id: 2,
          created_at: new Date().toISOString()
        }
      };
    });
    vi.mocked(getApiClient).mockReturnValue({ request: apiClientRequestMock } as any);

    const onUploaded = vi.fn();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const user = userEvent.setup();

    const { container } = render(
      <QueryClientProvider client={client}>
        <FileUploader folderId={2} onUploaded={onUploaded} />
      </QueryClientProvider>,
    );

    const input = container.querySelector('input[type="file"]');
    if (!input) throw new Error('Expected file input to exist');

    const file = new File(['hello'], 'test.md', { type: 'text/markdown' });
    await user.upload(input, file);

    await waitFor(() =>
      expect(apiClientRequestMock).toHaveBeenCalledWith(
        expect.objectContaining({ method: 'POST', url: '/documents', params: { folder_id: 2 } }),
      ),
    );
    expect(onUploaded).toHaveBeenCalled();
  });
});
