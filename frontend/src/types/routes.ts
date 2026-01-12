export const ROUTES = {
  home: '/',
  search: '/search',
  documents: '/documents'
} as const;

export type RoutePath = (typeof ROUTES)[keyof typeof ROUTES];
