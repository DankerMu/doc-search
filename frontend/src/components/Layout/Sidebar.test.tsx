import userEvent from '@testing-library/user-event';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import Sidebar from './Sidebar';

function LocationDisplay() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}</div>;
}

describe('Sidebar', () => {
  it('navigates when menu item is clicked', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/other']}>
        <Routes>
          <Route
            path="*"
            element={
              <>
                <Sidebar />
                <LocationDisplay />
              </>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByTestId('location')).toHaveTextContent('/other');
    await user.click(screen.getByRole('menuitem', { name: '首页' }));
    expect(screen.getByTestId('location')).toHaveTextContent('/');

    await user.click(screen.getByRole('menuitem', { name: '搜索' }));
    expect(screen.getByTestId('location')).toHaveTextContent('/search');

    await user.click(screen.getByRole('menuitem', { name: '文档' }));
    expect(screen.getByTestId('location')).toHaveTextContent('/documents');
  });
});
