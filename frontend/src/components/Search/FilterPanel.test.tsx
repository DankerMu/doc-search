import userEvent from '@testing-library/user-event';
import { fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';

import FilterPanel from './FilterPanel';
import type { SearchFilters } from '../../types/search';

describe('FilterPanel', () => {
  it('updates filters and supports reset', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    function Wrapper() {
      const [value, setValue] = useState<SearchFilters>({});
      return (
        <FilterPanel
          value={value}
          onChange={(next) => {
            setValue(next);
            onChange(next);
          }}
          folders={[
            {
              id: 1,
              name: 'Root',
              parent_id: null,
              children: [{ id: 2, name: 'Child', parent_id: 1, children: [] }]
            }
          ]}
          tags={[
            {
              id: 10,
              name: '合同',
              color: '#000000',
              document_count: 0,
              created_at: new Date().toISOString()
            }
          ]}
        />
      );
    }

    render(<Wrapper />);

    const typeCombobox = screen.getByRole('combobox', { name: 'filter-type' });
    const typeSelect = typeCombobox.closest('.ant-select');
    if (!typeSelect) throw new Error('Missing type select');
    fireEvent.mouseDown(typeSelect.querySelector('.ant-select-selector') as Element);
    await user.click(screen.getByText('PDF'));
    expect(onChange).toHaveBeenLastCalledWith({ type: 'pdf' });

    const folderCombobox = screen.getByRole('combobox', { name: 'filter-folder' });
    const folderSelect = folderCombobox.closest('.ant-select');
    if (!folderSelect) throw new Error('Missing folder select');
    fireEvent.mouseDown(folderSelect.querySelector('.ant-select-selector') as Element);
    await user.click(await screen.findByText('Root'));
    expect(onChange).toHaveBeenLastCalledWith({ folder_id: 1, type: 'pdf' });

    const tagsCombobox = screen.getByRole('combobox', { name: 'filter-tags' });
    const tagsSelect = tagsCombobox.closest('.ant-select');
    if (!tagsSelect) throw new Error('Missing tags select');
    fireEvent.mouseDown(tagsSelect.querySelector('.ant-select-selector') as Element);
    await user.click(screen.getByText('合同'));
    expect(onChange).toHaveBeenLastCalledWith({ folder_id: 1, tag_ids: [10], type: 'pdf' });

    fireEvent.change(screen.getByLabelText('filter-date-from'), { target: { value: '2026-01-01' } });
    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ date_from: '2026-01-01' }),
    );

    fireEvent.change(screen.getByLabelText('filter-date-to'), { target: { value: '2026-01-31' } });
    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ date_to: '2026-01-31' }),
    );

    fireEvent.change(screen.getByLabelText('filter-date-from'), { target: { value: '' } });
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ date_from: null }));

    fireEvent.change(screen.getByLabelText('filter-date-to'), { target: { value: '' } });
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ date_to: null }));

    await user.click(screen.getByLabelText('filters-reset'));
    expect(onChange).toHaveBeenLastCalledWith({});
  });
});
