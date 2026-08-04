import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import { AuthPage } from '@/components/AuthPage';
import { Layout } from '@/components/Layout';
import { useAuth } from '@/hooks/AuthContext';
import { ScenarioProvider } from '@/hooks/ScenarioContext';
import { ContactsPage } from '@/pages/ContactsPage';
import { DivisionPage } from '@/pages/DivisionPage';
import { HazardPage } from '@/pages/HazardPage';
import { RcbPage } from '@/pages/RcbPage';
import { TasksPage } from '@/pages/TasksPage';

function AuthGuard({
  children,
  requireAuth,
}: {
  children: React.ReactNode;
  requireAuth: boolean;
}) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100">
        <div className="text-sm text-slate-500">Wczytywanie danych scenariusza...</div>
      </div>
    );
  }

  if (requireAuth && !isAuthenticated) return <Navigate to="/auth" replace />;
  if (!requireAuth && isAuthenticated) return <Navigate to="/zagrozenie" replace />;

  return <>{children}</>;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/auth"
          element={
            <AuthGuard requireAuth={false}>
              <AuthPage />
            </AuthGuard>
          }
        />
        <Route
          element={
            <AuthGuard requireAuth={true}>
              <ScenarioProvider>
                <Layout />
              </ScenarioProvider>
            </AuthGuard>
          }
        >
          <Route path="/zagrozenie" element={<HazardPage />} />
          <Route path="/zadania" element={<TasksPage />} />
          <Route path="/dzial" element={<DivisionPage />} />
          <Route path="/rcb" element={<RcbPage />} />
          <Route path="/kontakty" element={<ContactsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/zagrozenie" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
