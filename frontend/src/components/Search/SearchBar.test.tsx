import userEvent from '@testing-library/user-event';
import { render, screen } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';

import SearchBar from './SearchBar';

describe('SearchBar', () => {
  it('renders and emits changes', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    function Wrapper() {
      const [value, setValue] = useState('');
      return (
        <SearchBar
          value={value}
          onChange={(next) => {
            setValue(next);
            onChange(next);
          }}
        />
      );
    }

    render(<Wrapper />);

    const input = screen.getByLabelText('search-input');
    await user.type(input, 'hello');

    expect(onChange).toHaveBeenCalled();
    expect(onChange).toHaveBeenLastCalledWith('hello');
  });

  it('disables input when loading', () => {
    render(<SearchBar value="q" onChange={() => undefined} loading />);
    expect(screen.getByLabelText('search-input')).toBeDisabled();
  });
});
