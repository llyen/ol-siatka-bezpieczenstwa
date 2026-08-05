import { useMemo, useState } from 'react';

import {
  BarChart,
  Button,
  EmptyState,
  KpiCard,
  Panel,
  StatusBadge,
  Toast,
  formatTimestamp,
} from '@/components/ui';
import {
  OVERLOAD_THRESHOLD,
  buildParticipants,
  computeDivisionLoad,
  criticalityRank,
} from '@/data/model';
import { useScenario } from '@/hooks/ScenarioContext';
import { requestEscalation } from '@/services/readiness';

/**
 * Ekran 4 - pulpit koordynatora RCB.
 *
 * Pulpit odpowiada na jedno pytanie decyzyjne: czy siatka domyka sie sama,
 * czy trzeba zwolac RZZK. Dlatego eskalacja jest tu jedynym przyciskiem akcji,
 * a wszystkie wskazniki sluza jej uzasadnieniu i sa zapisywane razem z wnioskiem.
 */
export function RcbPage() {
  const { tasks, kpis, hazardCode, phase, eventId, eventScale, escalations, refresh } = useScenario();
  const [saving, setSaving] = useState(false);
  const [justification, setJustification] = useState('');
  const [toast, setToast] = useState<{ message: string; tone: 'success' | 'error' } | null>(null);

  const load = useMemo(() => computeDivisionLoad(tasks), [tasks]);
  const blockers = useMemo(
    () =>
      tasks
        .filter((t) => t.status === 'zablokowane')
        .sort(
          (a, b) =>
            Number(b.on_critical_path) - Number(a.on_critical_path) ||
            criticalityRank(a.criticality) - criticalityRank(b.criticality)
        ),
    [tasks]
  );
  const overdue = useMemo(() => tasks.filter((t) => t.overdue), [tasks]);
  const participants = useMemo(() => buildParticipants(tasks), [tasks]);

  const recommendEscalation =
    kpis.criticalPathBlockers > 0 || kpis.readinessPct < 60 || kpis.blocked >= 3;

  const defaultJustification = `Gotowość ${kpis.readinessPct}% (${kpis.ready}/${kpis.total} zadań). Blokady: ${kpis.blocked}, w tym ${kpis.criticalPathBlockers} na ścieżce krytycznej. Zadania po SLA: ${kpis.overdue}. Działy przeciążone: ${kpis.overloadedDivisions}. Wnioskuję o zwołanie RZZK w trybie SPO-1.`;

  const escalate = async () => {
    setSaving(true);
    try {
      await requestEscalation({
        event_id: eventId,
        hazard_code: hazardCode,
        phase,
        event_scale: eventScale,
        recommended_spo: 'SPO-1',
        justification: (justification.trim() || defaultJustification).slice(0, 1000),
        readiness_pct: kpis.readinessPct,
        blockers_count: kpis.blocked,
        overdue_count: kpis.overdue,
        participants_count: participants.length,
      });
      await refresh();
      setJustification('');
      setToast({
        message: `Wniosek o eskalację do RZZK zarejestrowany. Rekomendowana procedura SPO-1, lista uczestników: ${participants.length} punktów kontaktowych.`,
        tone: 'success',
      });
    } catch (err) {
      setToast({
        message: err instanceof Error ? err.message : 'Nie udało się zapisać wniosku o eskalację.',
        tone: 'error',
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <KpiCard
          label="Gotowość siatki"
          value={kpis.readinessPct}
          suffix="%"
          hint={`${kpis.ready} z ${kpis.total} zadań`}
          tone={kpis.readinessPct >= 70 ? 'good' : kpis.readinessPct >= 40 ? 'warn' : 'bad'}
        />
        <KpiCard label="Blokady" value={kpis.blocked} tone={kpis.blocked === 0 ? 'good' : 'bad'} hint="status „zablokowane”" />
        <KpiCard label="Po SLA" value={kpis.overdue} tone={kpis.overdue === 0 ? 'good' : 'warn'} hint="moduł uruchomiony, brak domknięcia" />
        <KpiCard
          label="Ścieżka krytyczna"
          value={kpis.criticalPathBlockers}
          tone={kpis.criticalPathBlockers === 0 ? 'good' : 'bad'}
          hint="blokady w modułach 1–4"
        />
        <KpiCard
          label="Działy przeciążone"
          value={kpis.overloadedDivisions}
          tone={kpis.overloadedDivisions === 0 ? 'good' : 'warn'}
          hint={`próg ${OVERLOAD_THRESHOLD} zadania wiodące`}
        />
      </div>

      <Panel
        title="Decyzja: eskalacja do RZZK"
        description={
          recommendEscalation
            ? 'Wskaźniki uzasadniają zwołanie zespołu. Wniosek zapisuje migawkę stanu, żeby decyzja była rozliczalna po zdarzeniu.'
            : 'Siatka domyka się bez eskalacji. Wniosek można złożyć mimo to — wymaga uzasadnienia.'
        }
        actions={
          <Button variant={recommendEscalation ? 'danger' : 'secondary'} disabled={saving} onClick={() => void escalate()}>
            Eskaluj do RZZK (SPO-1)
          </Button>
        }
      >
        <textarea
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
          rows={3}
          maxLength={1000}
          placeholder={defaultJustification}
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <p className="mt-2 text-xs text-slate-500">
          Puste pole zostanie uzupełnione automatycznie treścią widoczną powyżej.
        </p>

        {escalations.length > 0 && (
          <div className="mt-4 space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Złożone wnioski ({escalations.length})
            </h3>
            {escalations.slice(0, 5).map((e) => (
              <div key={e.id} className="rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
                <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  <span className="rounded bg-gov px-1.5 py-0.5 font-medium text-white">{e.recommended_spo}</span>
                  <span>{formatTimestamp(e.requested_at)}</span>
                  <span>· {e.requested_by_name}</span>
                  <span>· gotowość {e.readiness_pct}%</span>
                  <span>· blokady {e.blockers_count}</span>
                  <span>· uczestnicy {e.participants_count}</span>
                </div>
                <p className="mt-1 text-slate-700">{e.justification}</p>
              </div>
            ))}
          </div>
        )}
      </Panel>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel
          title={`Blokady (${blockers.length})`}
          description="Sortowane wg wpływu: najpierw ścieżka krytyczna, potem krytyczność zadania."
        >
          {blockers.length === 0 ? (
            <EmptyState>Brak zgłoszonych blokad.</EmptyState>
          ) : (
            <ul className="space-y-3">
              {blockers.map((t) => (
                <li key={t.key} className="border-l-4 border-red-500 pl-3">
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="font-semibold text-slate-900">{t.admin_division}</span>
                    <span className="text-slate-700">{t.admin_name}</span>
                    {t.on_critical_path && (
                      <span className="rounded bg-red-600 px-1.5 py-0.5 text-[10px] font-medium text-white">
                        ścieżka krytyczna
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-slate-500">
                    moduł {t.task_module_id}. {t.task_module_name} · {t.criticality} ·{' '}
                    {formatTimestamp(t.declared_at)}
                  </div>
                  <p className="mt-0.5 text-sm text-slate-700">{t.comment || 'brak opisu przyczyny'}</p>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel
          title="Obciążenie działów rolą wiodącą"
          description={`Czerwony słupek oznacza dział na progu przeciążenia (${OVERLOAD_THRESHOLD} zadania wiodące lub więcej).`}
        >
          <BarChart
            rows={load.slice(0, 14).map((d) => ({
              label: `${d.admin_division} ${d.admin_name}`,
              sub: `(${d.ready}/${d.total} gotowe)`,
              value: d.leading,
              tone: d.leading >= OVERLOAD_THRESHOLD ? 'bad' : d.blocked > 0 ? 'warn' : 'normal',
            }))}
          />
        </Panel>
      </div>

      <Panel
        title={`Zadania po SLA (${overdue.length})`}
        description="Moduł jest uruchomiony, a zadanie nie zostało domknięte deklaracją gotowości."
      >
        {overdue.length === 0 ? (
          <EmptyState>Wszystkie uruchomione moduły mają domknięte zadania.</EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-2 py-2">Dział</th>
                  <th className="px-2 py-2">Moduł</th>
                  <th className="px-2 py-2">Stan modułu</th>
                  <th className="px-2 py-2">Status zadania</th>
                  <th className="px-2 py-2 text-right">SLA</th>
                  <th className="px-2 py-2">Ostatnia deklaracja</th>
                </tr>
              </thead>
              <tbody>
                {overdue.map((t) => (
                  <tr key={t.key} className="border-b border-slate-100">
                    <td className="px-2 py-2">
                      <span className="font-semibold">{t.admin_division}</span>{' '}
                      <span className="text-slate-600">{t.admin_name}</span>
                    </td>
                    <td className="px-2 py-2">
                      {t.task_module_id}. {t.task_module_name}
                    </td>
                    <td className="px-2 py-2 text-slate-600">{t.activation_status ?? '—'}</td>
                    <td className="px-2 py-2"><StatusBadge status={t.status} /></td>
                    <td className="px-2 py-2 text-right tabular-nums text-slate-600">{t.sla_hours} h</td>
                    <td className="px-2 py-2 text-xs text-slate-500">{formatTimestamp(t.declared_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </div>
  );
}
