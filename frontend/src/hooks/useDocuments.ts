import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { getApiBaseUrl, getApiClient, request } from '../services/api';
import type { Document, DocumentDetail, DocumentListResponse } from '../types/document';

export type UseDocumentsParams = {
  folderId?: number | null;
  page: number;
  pageSize: number;
};

export function useDocuments(params: UseDocumentsParams) {
  const skip = (params.page - 1) * params.pageSize;
  const limit = params.pageSize;

  return useQuery({
    queryKey: ['documents', { folderId: params.folderId, skip, limit }],
    queryFn: () =>
      request<DocumentListResponse>({
        method: 'GET',
        url: '/documents',
        params: { folder_id: params.folderId ?? undefined, skip, limit }
      }),
    placeholderData: (prev) => prev
  });
}

export function useDocumentDetail(documentId: number | null, enabled = true) {
  return useQuery({
    queryKey: ['document', documentId],
    enabled: enabled && typeof documentId === 'number',
    queryFn: () => request<DocumentDetail>({ method: 'GET', url: `/documents/${documentId}` })
  });
}

export type UploadDocumentInput = {
  file: File;
  folderId?: number | null;
  onProgress?: (percent: number) => void;
};

export async function uploadDocument(input: UploadDocumentInput): Promise<Document> {
  const data = new FormData();
  data.append('file', input.file);

  const response = await getApiClient().request<Document>({
    method: 'POST',
    url: '/documents',
    params: input.folderId ? { folder_id: input.folderId } : undefined,
    data,
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (event) => {
      if (!input.onProgress) return;
      if (!event.total) return;
      input.onProgress(Math.round((event.loaded / event.total) * 100));
    }
  });

  return response.data;
}

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: uploadDocument,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['documents'] });
      await queryClient.invalidateQueries({ queryKey: ['search'] });
    }
  });
}

export function getDocumentDownloadUrl(documentId: number): string {
  const apiBaseUrl = getApiBaseUrl().replace(/\/+$/, '');
  return `${apiBaseUrl}/documents/${documentId}/file`;
}
