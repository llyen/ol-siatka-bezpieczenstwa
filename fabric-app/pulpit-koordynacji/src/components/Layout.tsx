import { NavLink, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '@/hooks/AuthContext';
import { useScenario } from '@/hooks/ScenarioContext';
import { HAZARD_BY_CODE } from '@/data/model';

const NAV = [
  { to: '/zagrozenie', label: 'Zagrożenie' },
  { to: '/zadania', label: 'Lista zadań' },
  { to: '/dzial', label: 'Karta działu' },
  { to: '/rcb', label: 'Pulpit RCB' },
  { to: '/kontakty', label: 'Kontakty i SPO-1' },
];

const PHASE_LABEL: Record<string, string> = {
  R: 'reagowanie',
  O: 'odbudowa',
};

export function Layout() {
  const { user, signOut } = useAuth();
  const { hazardCode, phase, eventId, eventScale } = useScenario();
  const location = useLocation();

  const hazard = HAZARD_BY_CODE.get(hazardCode);
  const screen = NAV.find((n) => location.pathname.startsWith(n.to))?.label ?? '';

  return (
    <div className="min-h-screen bg-slate-100">
      <div className="h-1 w-full bg-gov" />
      <header className="border-b border-slate-200 bg-white text-slate-900">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-3 px-6 py-3">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-slate-500">
              Rządowe Centrum Bezpieczeństwa · demonstracja na danych syntetycznych
            </div>
            <h1 className="text-lg font-semibold text-slate-900">
              Siatka Bezpieczeństwa — Pulpit Koordynacji
            </h1>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <div className="text-right">
              <div className="font-medium text-slate-900">
                {user?.name ?? user?.email ?? 'użytkownik'}
              </div>
              <div className="text-xs text-slate-500">{eventId}</div>
            </div>
            <button
              onClick={() => void signOut()}
              className="rounded px-3 py-1.5 text-sm text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50"
            >
              Wyloguj
            </button>
          </div>
        </div>
        <nav className="border-t border-slate-200">
          <div className="mx-auto flex max-w-[1600px] gap-1 px-6">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `border-b-2 px-3 py-2 text-sm transition-colors ${
                    isActive
                      ? 'border-gov font-semibold text-gov'
                      : 'border-transparent text-slate-500 hover:text-slate-900'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>
      </header>

      <div className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-[1600px] px-6 py-2 text-xs text-slate-500">
          {eventId} <span className="mx-1 text-slate-300">›</span>
          {hazardCode} {hazard?.hazard_name ?? ''} <span className="mx-1 text-slate-300">›</span>
          faza {phase} ({PHASE_LABEL[phase] ?? phase}), skala {eventScale}
          {screen && (
            <>
              <span className="mx-1 text-slate-300">›</span>
              <span className="font-medium text-slate-700">{screen}</span>
            </>
          )}
        </div>
      </div>

      <main className="mx-auto max-w-[1600px] px-6 py-6">
        <Outlet />
      </main>

      <footer className="mx-auto max-w-[1600px] px-6 pb-8 text-xs text-slate-400">
        Dane syntetyczne. Aplikacja demonstracyjna Microsoft Fabric App (Rayfin) dla scenariusza
        „Siatka bezpieczeństwa i plan aktywacji zadań”.
      </footer>
    </div>
  );
}
