import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes } from 'react-router-dom';

import MainLayout from './components/Layout/MainLayout';
import Documents from './pages/Documents';
import Home from './pages/Home';
import NotFound from './pages/NotFound';
import Search from './pages/Search';
import { ROUTES } from './types/routes';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false
    }
  }
});

export function AppRoutes() {
  return (
    <Routes>
      <Route path={ROUTES.home} element={<MainLayout />}>
        <Route index element={<Home />} />
        <Route path={ROUTES.search.slice(1)} element={<Search />} />
        <Route path={ROUTES.documents.slice(1)} element={<Documents />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
