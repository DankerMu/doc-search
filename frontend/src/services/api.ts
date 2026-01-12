import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios';

export const DEFAULT_TIMEOUT_MS = 10_000;

type ApiEnv = {
  VITE_API_BASE_URL?: string;
};

export function getApiBaseUrl(env: ApiEnv = import.meta.env): string {
  return env.VITE_API_BASE_URL ?? '/api';
}

export function createApiClient(config: AxiosRequestConfig = {}): AxiosInstance {
  const client = axios.create({
    baseURL: getApiBaseUrl(),
    timeout: DEFAULT_TIMEOUT_MS,
    ...config
  });

  client.interceptors.response.use(
    (response: AxiosResponse) => response,
    (error) => Promise.reject(error),
  );

  return client;
}

let apiClient: AxiosInstance | null = null;

export function getApiClient(): AxiosInstance {
  if (!apiClient) apiClient = createApiClient();
  return apiClient;
}

export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await getApiClient().request<T>(config);
  return response.data;
}

export function resetApiClientForTests(): void {
  apiClient = null;
}
