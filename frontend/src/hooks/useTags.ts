import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { request } from '../services/api';
import type { Tag, TagCreateInput } from '../types/tag';

export function useTags() {
  return useQuery({
    queryKey: ['tags'],
    queryFn: () => request<Tag[]>({ method: 'GET', url: '/tags' })
  });
}

export function useCreateTag() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: TagCreateInput) =>
      request<Tag>({ method: 'POST', url: '/tags', data: input }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['tags'] });
    }
  });
}

export function useUpdateTag() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: { id: number; patch: Partial<TagCreateInput> }) =>
      request<Tag>({ method: 'PUT', url: `/tags/${input.id}`, data: input.patch }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['tags'] });
    }
  });
}

export function useDeleteTag() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => request<{ message: string }>({ method: 'DELETE', url: `/tags/${id}` }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['tags'] });
    }
  });
}

