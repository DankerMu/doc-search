import { useQuery } from '@tanstack/react-query';

import { request } from '../services/api';
import type { FolderTreeNode } from '../types/folder';

export function useFolders() {
  return useQuery({
    queryKey: ['folders'],
    queryFn: () => request<FolderTreeNode[]>({ method: 'GET', url: '/folders' })
  });
}

