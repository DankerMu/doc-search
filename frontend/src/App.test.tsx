import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import App from './App';

describe('App', () => {
  it('renders home route with layout', async () => {
    window.history.pushState({}, '', '/');
    render(<App />);

    expect(screen.getByRole('heading', { name: 'Doc Search' })).toBeInTheDocument();
    expect(screen.getByText('欢迎使用 Doc Search')).toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe('Doc Search - 首页'));
  });

  it('renders not-found route', async () => {
    window.history.pushState({}, '', '/missing');
    render(<App />);

    expect(screen.getByText('页面不存在')).toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe('Doc Search - 404'));
  });
});
