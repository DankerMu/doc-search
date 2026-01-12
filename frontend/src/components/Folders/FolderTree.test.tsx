import userEvent from '@testing-library/user-event';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import FolderTree from './FolderTree';

describe('FolderTree', () => {
  it('selects folder and supports selecting all', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();

    render(
      <FolderTree
        folders={[
          { id: 1, name: 'Root', parent_id: null, children: [{ id: 2, name: 'Child', parent_id: 1, children: [] }] }
        ]}
        selectedId={null}
        onSelect={onSelect}
      />,
    );

    await user.click(screen.getByText('Child'));
    expect(onSelect).toHaveBeenLastCalledWith(2);

    await user.click(screen.getByText('全部文件夹'));
    expect(onSelect).toHaveBeenLastCalledWith(null);
  });
});

