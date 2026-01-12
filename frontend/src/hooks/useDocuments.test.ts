import { describe, expect, it, vi } from 'vitest';

import { getApiClient } from '../services/api';
import { uploadDocument } from './useDocuments';

vi.mock('../services/api', () => ({
  request: vi.fn(),
  getApiClient: vi.fn()
}));

describe('hooks/useDocuments', () => {
  it('uploadDocument omits params when folderId is missing and skips progress without handler', async () => {
    const apiRequestMock = vi.fn(async (config: any) => {
      config.onUploadProgress?.({ loaded: 1, total: 10 });
      return {
        data: {
          id: 1,
          filename: 'stored.md',
          original_name: 'test.md',
          file_type: 'md',
          file_size: 1,
          folder_id: null,
          created_at: new Date().toISOString()
        }
      };
    });
    vi.mocked(getApiClient).mockReturnValue({ request: apiRequestMock } as any);

    await uploadDocument({ file: new File(['x'], 'test.md') });
    expect(apiRequestMock).toHaveBeenCalledWith(expect.objectContaining({ params: undefined }));
  });

  it('uploadDocument skips progress when total is missing', async () => {
    const onProgress = vi.fn();
    const apiRequestMock = vi.fn(async (config: any) => {
      config.onUploadProgress?.({ loaded: 1 });
      return {
        data: {
          id: 1,
          filename: 'stored.md',
          original_name: 'test.md',
          file_type: 'md',
          file_size: 1,
          folder_id: null,
          created_at: new Date().toISOString()
        }
      };
    });
    vi.mocked(getApiClient).mockReturnValue({ request: apiRequestMock } as any);

    await uploadDocument({ file: new File(['x'], 'test.md'), folderId: 2, onProgress });
    expect(onProgress).not.toHaveBeenCalled();
    expect(apiRequestMock).toHaveBeenCalledWith(expect.objectContaining({ params: { folder_id: 2 } }));
  });
});

