import userEvent from '@testing-library/user-event';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import SearchResults from './SearchResults';

describe('SearchResults', () => {
  it('renders highlighted snippet and triggers preview', async () => {
    const user = userEvent.setup();
    const onPreview = vi.fn();

    render(
      <SearchResults
        items={[
          {
            doc_id: 1,
            file_type: 'md',
            folder_id: null,
            score: 1,
            highlight: 'hello <mark>world</mark>'
          }
        ]}
        total={1}
        loading={false}
        page={1}
        pageSize={10}
        onPageChange={() => undefined}
        onPreview={onPreview}
      />,
    );

    expect(screen.getByText('文档 #1')).toBeInTheDocument();
    expect(screen.getByText('world').tagName.toLowerCase()).toBe('mark');

    await user.click(screen.getByRole('button', { name: '预览' }));
    expect(onPreview).toHaveBeenCalledWith(1);
  });

  it('handles empty highlight safely', () => {
    render(
      <SearchResults
        items={[
          { doc_id: 2, file_type: '', folder_id: null, score: 1, highlight: '' }
        ]}
        total={1}
        page={1}
        pageSize={10}
        onPageChange={() => undefined}
        onPreview={() => undefined}
      />,
    );

    expect(screen.getByText('文档 #2')).toBeInTheDocument();
  });
});

