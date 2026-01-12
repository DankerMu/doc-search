import { beforeEach, describe, expect, it, vi } from 'vitest';

const axiosCreateMock = vi.fn();
const responseUseMock = vi.fn();
const requestMock = vi.fn();

vi.mock('axios', () => ({
  default: {
    create: axiosCreateMock
  }
}));

describe('services/api', () => {
  beforeEach(() => {
    vi.resetModules();
    axiosCreateMock.mockReset();
    responseUseMock.mockReset();
    requestMock.mockReset();
  });

  it('createApiClient configures axios defaults and interceptors', async () => {
    axiosCreateMock.mockReturnValue({
      interceptors: { response: { use: responseUseMock } },
      request: requestMock
    });

    const { DEFAULT_TIMEOUT_MS, createApiClient, getApiBaseUrl } = await import('./api');

    createApiClient();
    expect(axiosCreateMock).toHaveBeenCalledWith(
      expect.objectContaining({ baseURL: '/api', timeout: DEFAULT_TIMEOUT_MS }),
    );
    expect(responseUseMock).toHaveBeenCalledTimes(1);
    expect(getApiBaseUrl({ VITE_API_BASE_URL: 'https://example.test' })).toBe('https://example.test');

    const call = responseUseMock.mock.calls[0];
    if (!call) throw new Error('Expected interceptor to be registered');

    const [onFulfilled, onRejected] = call;
    const response = { data: { ok: true } };
    expect(onFulfilled(response)).toBe(response);
    await expect(onRejected(new Error('fail'))).rejects.toThrow('fail');
  });

  it('request returns response data', async () => {
    axiosCreateMock.mockReturnValue({
      interceptors: { response: { use: responseUseMock } },
      request: requestMock
    });
    requestMock.mockResolvedValue({ data: { ok: true } });

    const { getApiClient, request, resetApiClientForTests } = await import('./api');
    resetApiClientForTests();

    await expect(request<{ ok: boolean }>({ method: 'GET', url: '/health' })).resolves.toEqual({
      ok: true
    });
    expect(requestMock).toHaveBeenCalledWith(expect.objectContaining({ method: 'GET', url: '/health' }));

    getApiClient();
    expect(axiosCreateMock).toHaveBeenCalledTimes(1);
  });
});
