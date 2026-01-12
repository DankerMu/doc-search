import { describe, expect, it } from 'vitest';

import { buildSearchParams } from './search';

describe('types/search', () => {
  it('buildSearchParams trims q and includes optional filters', () => {
    expect(
      buildSearchParams({
        q: ' hello ',
        type: 'md',
        folder_id: 1,
        tag_ids: [1, 2],
        date_from: '2026-01-01',
        date_to: '2026-01-31',
        skip: 0,
        limit: 20
      }),
    ).toEqual({
      q: 'hello',
      type: 'md',
      folder_id: 1,
      tag_ids: '1,2',
      date_from: '2026-01-01',
      date_to: '2026-01-31',
      skip: 0,
      limit: 20
    });
  });

  it('buildSearchParams omits empty optional filters', () => {
    expect(
      buildSearchParams({
        q: 'x',
        folder_id: null,
        tag_ids: [],
        date_from: null,
        date_to: null
      }),
    ).toEqual({ q: 'x' });
  });
});
