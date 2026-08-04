import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  Button,
  CriticalityBadge,
  EmptyState,
  KpiCard,
  Panel,
  RoleBadge,
  StatusBadge,
  downloadCsv,
  formatTimestamp,
} from '@/components/ui';
import { MODULES, STATUSES, toCsv } from '@/data/model';
import { useScenario } from '@/hooks/ScenarioContext';

const ALL = 'wszystkie';

/**
 * Ekran 2 - lista zadan planu aktywacji.
 *
 * Kolumna „kolejnosc" to glebokosc modulu w grafie wspolzaleznosci: zadania
 * z kolejnoscia 1 nie maja poprzednikow i mozna je uruchomic od razu.
 * Dzieki temu lista czyta sie jako harmonogram, a nie jako plaski rejestr.
 */
export function TasksPage() {
  const { tasks, kpis, select } = useScenario();
  const navigate = useNavigate();

  const [role, setRole] = useState(ALL);
  const [status, setStatus] = useState(ALL);
  const [criticality, setCriticality] = useState(ALL);
  const [moduleId, setModuleId] = useState(ALL);
  const [division, setDivision] = useState(ALL);
  const [query, setQuery] = useState('');

  const roles = useMemo(() => [ALL, ...new Set(tasks.map((t) => t.role))], [tasks]);
  const criticalities = useMemo(
    () => [ALL, ...new Set(tasks.map((t) => t.criticality))],
    [tasks]
  );
  const divisions = useMemo(
    () =>
      [ALL, ...new Set(tasks.map((t) => t.admin_division))].sort((a, b) =>
        a === ALL ? -1 : b === ALL ? 1 : a.localeCompare(b)
      ),
    [tasks]
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return tasks.filter(
      (t) =>
        (role === ALL || t.role === role) &&
        (status === ALL || t.status === status) &&
        (criticality === ALL || t.criticality === criticality) &&
        (moduleId === ALL || String(t.task_module_id) === moduleId) &&
        (division === ALL || t.admin_division === division) &&
        (q === '' ||
          `${t.admin_division} ${t.admin_name} ${t.ministry} ${t.task_module_name} ${t.comment}`
            .toLowerCase()
            .includes(q))
    );
  }, [tasks, role, status, criticality, moduleId, division, query]);

  const reset = () => {
    setRole(ALL);
    setStatus(ALL);
    setCriticality(ALL);
    setModuleId(ALL);
    setDivision(ALL);
    setQuery('');
  };

  const openDivision = (code: string) => {
    select({});
    navigate(`/dzial?dzial=${encodeURIComponent(code)}`);
  };

  const exportCsv = () => {
    downloadCsv(
      'plan_aktywacji.csv',
      toCsv(
        filtered.map((t) => ({
          dzial: t.admin_division,
          nazwa_dzialu: t.admin_name,
          ministerstwo: t.ministry,
          modul: t.task_module_id,
          nazwa_modulu: t.task_module_name,
          rola: t.role,
          krytycznosc: t.criticality,
          sla_h: t.sla_hours,
          kolejnosc: t.dependency_order,
          status: t.status,
          zadeklarowano: t.declared_at ?? '',
        }))
      )
    );
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Zadania w planie" value={kpis.total} hint={`w tym ${kpis.leading} wiodących`} />
        <KpiCard
          label="Gotowość"
          value={kpis.readinessPct}
          suffix="%"
          hint={`${kpis.ready} z ${kpis.total} zadań domkniętych`}
          tone={kpis.readinessPct >= 70 ? 'good' : kpis.readinessPct >= 40 ? 'warn' : 'bad'}
        />
        <KpiCard
          label="Blokady"
          value={kpis.blocked}
          hint={`${kpis.criticalPathBlockers} na ścieżce krytycznej`}
          tone={kpis.blocked === 0 ? 'good' : 'bad'}
        />
        <KpiCard
          label="Zadania po SLA"
          value={kpis.overdue}
          hint="moduł uruchomiony, zadanie niedomknięte"
          tone={kpis.overdue === 0 ? 'good' : 'warn'}
        />
      </div>

      <Panel
        title={`Plan aktywacji — ${filtered.length} z ${tasks.length} zadań`}
        description="Kliknij wiersz, aby przejść do karty działu i złożyć deklarację gotowości."
        actions={
          <>
            <Button onClick={reset}>Wyczyść filtry</Button>
            <Button onClick={exportCsv} disabled={filtered.length === 0}>
              Eksport CSV
            </Button>
          </>
        }
      >
        <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Szukaj: dział, resort, moduł…"
            className="rounded border border-slate-300 px-3 py-1.5 text-sm lg:col-span-2"
          />
          <select value={division} onChange={(e) => setDivision(e.target.value)} className="rounded border border-slate-300 px-2 py-1.5 text-sm">
            {divisions.map((d) => (
              <option key={d} value={d}>{d === ALL ? 'dział: wszystkie' : `dział ${d}`}</option>
            ))}
          </select>
          <select value={moduleId} onChange={(e) => setModuleId(e.target.value)} className="rounded border border-slate-300 px-2 py-1.5 text-sm">
            <option value={ALL}>moduł: wszystkie</option>
            {MODULES.map((m) => (
              <option key={m.task_module_id} value={String(m.task_module_id)}>
                {m.task_module_id}. {m.task_module_name}
              </option>
            ))}
          </select>
          <select value={role} onChange={(e) => setRole(e.target.value)} className="rounded border border-slate-300 px-2 py-1.5 text-sm">
            {roles.map((r) => (
              <option key={r} value={r}>{r === ALL ? 'rola: wszystkie' : r}</option>
            ))}
          </select>
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded border border-slate-300 px-2 py-1.5 text-sm">
            <option value={ALL}>status: wszystkie</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <select value={criticality} onChange={(e) => setCriticality(e.target.value)} className="rounded border border-slate-300 px-2 py-1.5 text-sm lg:col-start-6">
            {criticalities.map((c) => (
              <option key={c} value={c}>{c === ALL ? 'krytyczność: wszystkie' : c}</option>
            ))}
          </select>
        </div>

        {filtered.length === 0 ? (
          <EmptyState>Żadne zadanie nie spełnia wybranych kryteriów.</EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-2 py-2">Dział</th>
                  <th className="px-2 py-2">Resort</th>
                  <th className="px-2 py-2">Moduł zadaniowy</th>
                  <th className="px-2 py-2">Rola</th>
                  <th className="px-2 py-2">Krytyczność</th>
                  <th className="px-2 py-2 text-right">SLA</th>
                  <th className="px-2 py-2 text-right">Kolejność</th>
                  <th className="px-2 py-2">Gotowość</th>
                  <th className="px-2 py-2">Zadeklarowano</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((t) => (
                  <tr
                    key={t.key}
                    onClick={() => openDivision(t.admin_division)}
                    className={`cursor-pointer border-b border-slate-100 hover:bg-blue-50 ${
                      t.status === 'zablokowane' ? 'bg-red-50/60' : ''
                    }`}
                  >
                    <td className="px-2 py-2 font-semibold text-slate-900">{t.admin_division}</td>
                    <td className="px-2 py-2">
                      <div className="text-slate-800">{t.admin_name}</div>
                      <div className="text-xs text-slate-500">{t.ministry}</div>
                    </td>
                    <td className="px-2 py-2">
                      <span className="text-slate-400">{t.task_module_id}.</span> {t.task_module_name}
                      {t.on_critical_path && (
                        <span className="ml-2 rounded bg-[#0f2a52] px-1.5 py-0.5 text-[10px] font-medium text-white">
                          ścieżka krytyczna
                        </span>
                      )}
                    </td>
                    <td className="px-2 py-2"><RoleBadge role={t.role} /></td>
                    <td className="px-2 py-2"><CriticalityBadge value={t.criticality} /></td>
                    <td className="px-2 py-2 text-right tabular-nums text-slate-600">{t.sla_hours} h</td>
                    <td className="px-2 py-2 text-right tabular-nums text-slate-600">{t.dependency_order}</td>
                    <td className="px-2 py-2">
                      <StatusBadge status={t.status} />
                      {t.overdue && (
                        <span className="ml-1 text-xs font-medium text-amber-700">po SLA</span>
                      )}
                    </td>
                    <td className="px-2 py-2 text-xs text-slate-500">
                      {formatTimestamp(t.declared_at)}
                      {t.from_app && <span className="ml-1 text-emerald-600">· z aplikacji</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
