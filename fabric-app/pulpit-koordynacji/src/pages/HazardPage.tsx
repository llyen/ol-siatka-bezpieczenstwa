import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Button, KpiCard, Panel, hazardColorClass } from '@/components/ui';
import { HAZARDS, buildPlan } from '@/data/model';
import { useScenario } from '@/hooks/ScenarioContext';

/**
 * Ekran 1 - wybor zagrozenia.
 *
 * Kafelek pokazuje kolor i ocene ryzyka z KPZK, wiec decydent widzi od razu,
 * ktore zagrozenia sa najwyzej w macierzy. Liczba zadan liczona jest na biezaco
 * z siatki, zeby wybor fazy mial widoczna konsekwencje jeszcze przed
 * wygenerowaniem planu.
 */
export function HazardPage() {
  const { hazardCode, phase, eventScale, eventId, select, generatePlan } = useScenario();
  const [category, setCategory] = useState('wszystkie');
  const navigate = useNavigate();

  const categories = useMemo(
    () => ['wszystkie', ...new Set(HAZARDS.map((h) => h.category))],
    []
  );

  const visible = useMemo(
    () => HAZARDS.filter((h) => category === 'wszystkie' || h.category === category),
    [category]
  );

  const taskCounts = useMemo(() => {
    const map = new Map<string, number>();
    for (const h of HAZARDS) map.set(h.hazard_code, buildPlan(h.hazard_code, phase).length);
    return map;
  }, [phase]);

  const selected = HAZARDS.find((h) => h.hazard_code === hazardCode);
  const plannedTasks = taskCounts.get(hazardCode) ?? 0;

  const handleGenerate = () => {
    generatePlan();
    navigate('/zadania');
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Wybrane zagrożenie" value={hazardCode} hint={selected?.hazard_name} />
        <KpiCard
          label="Ocena ryzyka"
          value={selected?.risk_score ?? 0}
          hint={`${selected?.probability_label ?? ''} / skutki ${selected?.impact_label ?? ''}`}
          tone={(selected?.risk_score ?? 0) >= 15 ? 'bad' : (selected?.risk_score ?? 0) >= 9 ? 'warn' : 'good'}
        />
        <KpiCard label="Zadania w planie" value={plannedTasks} hint={`faza ${phase}`} />
        <KpiCard label="Skala zdarzenia" value={eventScale} hint="1 lokalna — 5 krajowa" />
      </div>

      <Panel
        title="Parametry zdarzenia"
        description="Ustawienia obowiązują na wszystkich ekranach aplikacji."
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-slate-700">Identyfikator zdarzenia</span>
            <input
              value={eventId}
              onChange={(e) => select({ eventId: e.target.value.toUpperCase() })}
              className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-slate-700">Faza</span>
            <select
              value={phase}
              onChange={(e) => select({ phase: e.target.value })}
              className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
            >
              <option value="R">R — reagowanie</option>
              <option value="O">O — odbudowa</option>
            </select>
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-slate-700">Skala zdarzenia</span>
            <select
              value={eventScale}
              onChange={(e) => select({ eventScale: Number(e.target.value) })}
              className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-slate-700">Kategoria zagrożeń</span>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
            >
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Panel>

      <Panel
        title={`Zagrożenia KPZK (${visible.length})`}
        description="Kolor kafelka odpowiada poziomowi ryzyka w macierzy KPZK. Liczba w prawym dolnym rogu to zadania, jakie wygeneruje plan dla wybranej fazy."
        actions={
          <Button variant="primary" onClick={handleGenerate} disabled={plannedTasks === 0}>
            Generuj plan aktywacji ({plannedTasks} zadań)
          </Button>
        }
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5">
          {visible.map((h) => {
            const isSelected = h.hazard_code === hazardCode;
            const count = taskCounts.get(h.hazard_code) ?? 0;
            return (
              <button
                key={h.hazard_code}
                onClick={() => select({ hazardCode: h.hazard_code })}
                className={`rounded-lg border-2 p-3 text-left transition-all ${hazardColorClass(h.color)} ${
                  isSelected ? 'ring-4 ring-gov ring-offset-2' : 'opacity-90 hover:opacity-100'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="text-xs font-bold tracking-wide">{h.hazard_code}</span>
                  <span className="rounded bg-black/20 px-1.5 py-0.5 text-xs font-semibold">
                    {h.risk_score}
                  </span>
                </div>
                <div className="mt-1 text-sm font-semibold leading-tight">{h.hazard_name}</div>
                <div className="mt-2 flex items-end justify-between text-[11px] opacity-80">
                  <span>{h.category}</span>
                  <span>{count} zadań</span>
                </div>
              </button>
            );
          })}
        </div>
        {plannedTasks === 0 && (
          <p className="mt-4 rounded bg-amber-50 px-3 py-2 text-sm text-amber-800">
            Dla tego zagrożenia i fazy siatka nie przewiduje zadań operacyjnych. Wybierz inną fazę
            albo inne zagrożenie.
          </p>
        )}
      </Panel>
    </div>
  );
}
