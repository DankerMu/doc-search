import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import MainLayout from './MainLayout';

describe('MainLayout', () => {
  it('renders header, sidebar and outlet content', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route element={<MainLayout />}>
            <Route index element={<div>Outlet Content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: 'Doc Search' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: '首页' })).toBeInTheDocument();
    expect(screen.getByText('Outlet Content')).toBeInTheDocument();
  });
});

