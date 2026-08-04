import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import {
  Button,
  CriticalityBadge,
  EmptyState,
  KpiCard,
  Panel,
  RoleBadge,
  StatusBadge,
  Toast,
  formatTimestamp,
} from '@/components/ui';
import { CONTACTS, DIVISION_BY_CODE, STATUSES } from '@/data/model';
import { useScenario } from '@/hooks/ScenarioContext';
import { declareReadiness, validateDeclaration } from '@/services/readiness';

/**
 * Ekran 3 - karta dzialu administracji.
 *
 * Dyzurny widzi wylacznie zadania swojego dzialu, jego kontakty i instytucje
 * podlegle. Formularz wymusza to, czego pozniej potrzebuje koordynator RCB:
 * przy blokadzie przyczyne, przy gotowosci konkretne sily i srodki. Bez tego
 * deklaracja jest tylko zmiana koloru na dashboardzie.
 */
export function DivisionPage() {
  const { tasks, hazardCode, phase, eventId, declarations, refresh } = useScenario();
  const [params, setParams] = useSearchParams();

  const availableDivisions = useMemo(
    () => [...new Set(tasks.map((t) => t.admin_division))].sort((a, b) => a.localeCompare(b)),
    [tasks]
  );

  const divisionFromUrl = params.get('dzial');
  const division = divisionFromUrl ?? availableDivisions[0] ?? '';

  useEffect(() => {
    if (!divisionFromUrl && availableDivisions.length > 0) {
      setParams({ dzial: availableDivisions[0] }, { replace: true });
    }
  }, [divisionFromUrl, availableDivisions, setParams]);

  const info = DIVISION_BY_CODE.get(division);
  const divisionTasks = useMemo(
    () => tasks.filter((t) => t.admin_division === division),
    [tasks, division]
  );
  const contacts = useMemo(
    () => CONTACTS.filter((c) => c.admin_division === division),
    [division]
  );
  const history = useMemo(
    () => declarations.filter((d) => d.admin_division === division),
    [declarations, division]
  );

  const [moduleId, setModuleId] = useState<number | null>(null);
  const [status, setStatus] = useState<string>('w toku');
  const [comment, setComment] = useState('');
  const [forces, setForces] = useState('');
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; tone: 'success' | 'error' } | null>(null);

  useEffect(() => {
    setModuleId(divisionTasks[0]?.task_module_id ?? null);
  }, [divisionTasks]);

  const selectedTask = divisionTasks.find((t) => t.task_module_id === moduleId);

  useEffect(() => {
    if (!selectedTask) return;
    setStatus(selectedTask.status);
    setComment(selectedTask.comment ?? '');
    setForces(selectedTask.forces_and_assets ?? '');
  }, [selectedTask]);

  const draft = {
    event_id: eventId,
    hazard_code: hazardCode,
    phase,
    admin_division: division,
    task_module_id: moduleId ?? 0,
    status,
    comment,
    forces_and_assets: forces,
  };
  const errors = moduleId === null ? ['Wybierz moduł zadaniowy.'] : validateDeclaration(draft);

  const submit = async (nextStatus: string) => {
    if (moduleId === null) return;
    const payload = { ...draft, status: nextStatus };
    const problems = validateDeclaration(payload);
    if (problems.length > 0) {
      setToast({ message: problems.join('\n'), tone: 'error' });
      return;
    }
    setSaving(true);
    try {
      const saved = await declareReadiness(payload);
      await refresh();
      setStatus(nextStatus);
      setToast({
        message: `Zapisano deklarację: dział ${division}, moduł ${moduleId}, status „${nextStatus}”. Czas zapisu ${formatTimestamp(saved.declared_at)}.`,
        tone: 'success',
      });
    } catch (err) {
      setToast({
        message: err instanceof Error ? err.message : 'Nie udało się zapisać deklaracji.',
        tone: 'error',
      });
    } finally {
      setSaving(false);
    }
  };

  const ready = divisionTasks.filter((t) => t.status === 'gotowe').length;

  return (
    <div className="space-y-6">
      <Panel title="Wybór działu administracji" description="Dyżurny resortu pracuje na swoim dziale; koordynator RCB może przełączać dowolny.">
        <select
          value={division}
          onChange={(e) => setParams({ dzial: e.target.value })}
          className="w-full max-w-2xl rounded border border-slate-300 px-3 py-2 text-sm"
        >
          {availableDivisions.map((code) => (
            <option key={code} value={code}>
              {code} — {DIVISION_BY_CODE.get(code)?.admin_name ?? code}
            </option>
          ))}
        </select>
      </Panel>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Zadania działu" value={divisionTasks.length} hint={info?.admin_name} />
        <KpiCard
          label="Domknięte"
          value={ready}
          suffix={`/ ${divisionTasks.length}`}
          tone={ready === divisionTasks.length && divisionTasks.length > 0 ? 'good' : 'warn'}
        />
        <KpiCard
          label="Blokady"
          value={divisionTasks.filter((t) => t.status === 'zablokowane').length}
          tone={divisionTasks.some((t) => t.status === 'zablokowane') ? 'bad' : 'good'}
        />
        <KpiCard
          label="Rola wiodąca"
          value={divisionTasks.filter((t) => t.role === 'wiodący' || t.role === 'wiodacy').length}
          hint="zadania, za które dział odpowiada"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Panel title={`Zadania działu ${division}`} description={info?.ministry}>
            {divisionTasks.length === 0 ? (
              <EmptyState>Ten dział nie ma zadań w bieżącym planie.</EmptyState>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-2 py-2">Moduł</th>
                    <th className="px-2 py-2">Rola</th>
                    <th className="px-2 py-2">Krytyczność</th>
                    <th className="px-2 py-2">Status</th>
                    <th className="px-2 py-2">Zadeklarowano</th>
                  </tr>
                </thead>
                <tbody>
                  {divisionTasks.map((t) => (
                    <tr
                      key={t.key}
                      onClick={() => setModuleId(t.task_module_id)}
                      className={`cursor-pointer border-b border-slate-100 hover:bg-blue-50 ${
                        t.task_module_id === moduleId ? 'bg-blue-50' : ''
                      }`}
                    >
                      <td className="px-2 py-2">
                        <span className="text-slate-400">{t.task_module_id}.</span> {t.task_module_name}
                      </td>
                      <td className="px-2 py-2"><RoleBadge role={t.role} /></td>
                      <td className="px-2 py-2"><CriticalityBadge value={t.criticality} /></td>
                      <td className="px-2 py-2"><StatusBadge status={t.status} /></td>
                      <td className="px-2 py-2 text-xs text-slate-500">{formatTimestamp(t.declared_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Panel>

          <Panel
            title="Deklaracja gotowości"
            description="Każdy zapis tworzy nowy wpis w rejestrze — obowiązuje ostatni. Historia pozostaje dostępna do rozliczenia."
          >
            {moduleId === null ? (
              <EmptyState>Wybierz zadanie z listy powyżej.</EmptyState>
            ) : (
              <div className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="block text-sm">
                    <span className="mb-1 block font-medium text-slate-700">Moduł zadaniowy</span>
                    <select
                      value={moduleId}
                      onChange={(e) => setModuleId(Number(e.target.value))}
                      className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
                    >
                      {divisionTasks.map((t) => (
                        <option key={t.key} value={t.task_module_id}>
                          {t.task_module_id}. {t.task_module_name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block text-sm">
                    <span className="mb-1 block font-medium text-slate-700">Status</span>
                    <select
                      value={status}
                      onChange={(e) => setStatus(e.target.value)}
                      className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
                    >
                      {STATUSES.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </label>
                </div>

                <label className="block text-sm">
                  <span className="mb-1 block font-medium text-slate-700">
                    Siły i środki {status === 'gotowe' && <span className="text-red-600">— wymagane</span>}
                  </span>
                  <input
                    value={forces}
                    onChange={(e) => setForces(e.target.value)}
                    maxLength={300}
                    placeholder="np. zespoły=4; pojazdy=6; dyżury=24/7"
                    className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
                  />
                </label>

                <label className="block text-sm">
                  <span className="mb-1 block font-medium text-slate-700">
                    Komentarz {status === 'zablokowane' && <span className="text-red-600">— wymagany przy blokadzie</span>}
                  </span>
                  <textarea
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    maxLength={500}
                    rows={3}
                    placeholder="Opisz stan realizacji albo przyczynę blokady."
                    className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
                  />
                  <span className="mt-1 block text-right text-xs text-slate-400">{comment.length}/500</span>
                </label>

                {errors.length > 0 && (
                  <ul className="rounded bg-amber-50 px-3 py-2 text-sm text-amber-800">
                    {errors.map((e) => (
                      <li key={e}>• {e}</li>
                    ))}
                  </ul>
                )}

                <div className="flex flex-wrap gap-2">
                  <Button variant="success" disabled={saving} onClick={() => void submit('gotowe')}>
                    Potwierdź gotowość
                  </Button>
                  <Button variant="primary" disabled={saving} onClick={() => void submit('w toku')}>
                    Zapisz w toku
                  </Button>
                  <Button variant="danger" disabled={saving} onClick={() => void submit('zablokowane')}>
                    Zgłoś blokadę
                  </Button>
                </div>
              </div>
            )}
          </Panel>
        </div>

        <div className="space-y-6">
          <Panel title="Punkty kontaktowe" description="Dane syntetyczne, zgodne strukturą z książką kontaktów RCB.">
            {contacts.length === 0 ? (
              <EmptyState>Brak kontaktu dla tego działu.</EmptyState>
            ) : (
              contacts.map((c) => (
                <div key={`${c.admin_division}-${c.email}`} className="space-y-1 text-sm">
                  <div className="font-medium text-slate-900">{c.unit}</div>
                  <div className="text-slate-600">{c.role}</div>
                  <div className="text-slate-600">tel. {c.duty_phone}</div>
                  <div className="text-slate-600">{c.email}</div>
                  <div className="text-xs text-slate-500">zastępca: {c.deputy}</div>
                </div>
              ))
            )}
          </Panel>

          <Panel title="Instytucje podległe">
            <ul className="space-y-1 text-sm text-slate-700">
              {(info?.subordinate_institutions ?? '').split(';').map((s) => (
                <li key={s}>• {s.trim()}</li>
              ))}
            </ul>
          </Panel>

          <Panel title={`Historia deklaracji (${history.length})`} description="Wpisy złożone w tej aplikacji.">
            {history.length === 0 ? (
              <EmptyState>Ten dział nie złożył jeszcze deklaracji w aplikacji.</EmptyState>
            ) : (
              <ul className="space-y-2 text-sm">
                {history.slice(0, 12).map((d) => (
                  <li key={d.id} className="border-l-2 border-slate-200 pl-3">
                    <div className="flex items-center gap-2">
                      <StatusBadge status={d.status} />
                      <span className="text-xs text-slate-500">moduł {d.task_module_id}</span>
                    </div>
                    <div className="text-xs text-slate-500">
                      {formatTimestamp(d.declared_at)} · {d.source_user_name}
                    </div>
                    {d.comment && <div className="mt-0.5 text-xs text-slate-600">{d.comment}</div>}
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      </div>

      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </div>
  );
}
