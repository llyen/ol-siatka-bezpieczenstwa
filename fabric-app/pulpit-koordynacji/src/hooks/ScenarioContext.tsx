import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import {
  buildPlan,
  buildTaskState,
  computeKpis,
  type Kpis,
  type PlanTask,
  type TaskState,
} from '@/data/model';
import {
  listEscalations,
  listReadiness,
  type EscalationRecord,
  type ReadinessRecord,
} from '@/services/readiness';

/**
 * Stan sceny: wybrane zagrozenie, faza, skala i identyfikator zdarzenia,
 * plus wyliczony plan i naniesione na niego deklaracje.
 *
 * Domyslne wartosci odpowiadaja scenariuszowi demonstracyjnemu
 * POWODZ_WRZESIEN_2026 opisanemu w RAYFIN_PROMPT.md.
 */

export interface ScenarioSelection {
  hazardCode: string;
  phase: string;
  eventScale: number;
  eventId: string;
}

const DEFAULT_SELECTION: ScenarioSelection = {
  hazardCode: 'Z02',
  phase: 'R',
  eventScale: 4,
  eventId: 'POWODZ_WRZESIEN_2026',
};

interface ScenarioContextValue extends ScenarioSelection {
  plan: PlanTask[];
  tasks: TaskState[];
  kpis: Kpis;
  declarations: ReadinessRecord[];
  escalations: EscalationRecord[];
  planGenerated: boolean;
  loading: boolean;
  error: string | null;
  select: (patch: Partial<ScenarioSelection>) => void;
  generatePlan: () => void;
  refresh: () => Promise<void>;
}

const ScenarioContext = createContext<ScenarioContextValue | undefined>(undefined);

export function ScenarioProvider({ children }: { children: ReactNode }) {
  const [selection, setSelection] = useState<ScenarioSelection>(DEFAULT_SELECTION);
  const [planGenerated, setPlanGenerated] = useState(false);
  const [declarations, setDeclarations] = useState<ReadinessRecord[]>([]);
  const [escalations, setEscalations] = useState<EscalationRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [decl, esc] = await Promise.all([
        listReadiness(selection.eventId),
        listEscalations(selection.eventId),
      ]);
      setDeclarations(decl);
      setEscalations(esc);
    } catch (err) {
      setError(
        err instanceof Error
          ? `Nie udało się pobrać zapisanych deklaracji: ${err.message}`
          : 'Nie udało się pobrać zapisanych deklaracji.'
      );
    } finally {
      setLoading(false);
    }
  }, [selection.eventId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const plan = useMemo(
    () => buildPlan(selection.hazardCode, selection.phase),
    [selection.hazardCode, selection.phase]
  );

  const tasks = useMemo(
    () =>
      buildTaskState(
        plan,
        declarations.map((d) => ({
          admin_division: d.admin_division,
          task_module_id: d.task_module_id,
          status: d.status,
          comment: d.comment,
          forces_and_assets: d.forces_and_assets,
          declared_at: d.declared_at,
        }))
      ),
    [plan, declarations]
  );

  const kpis = useMemo(() => computeKpis(tasks), [tasks]);

  const select = useCallback((patch: Partial<ScenarioSelection>) => {
    setSelection((prev) => ({ ...prev, ...patch }));
    // Zmiana zagrozenia lub fazy uniewaznia wygenerowany plan - uzytkownik
    // musi swiadomie potwierdzic nowy zakres.
    if (patch.hazardCode !== undefined || patch.phase !== undefined) {
      setPlanGenerated(false);
    }
  }, []);

  const value = useMemo<ScenarioContextValue>(
    () => ({
      ...selection,
      plan,
      tasks,
      kpis,
      declarations,
      escalations,
      planGenerated,
      loading,
      error,
      select,
      generatePlan: () => setPlanGenerated(true),
      refresh,
    }),
    [selection, plan, tasks, kpis, declarations, escalations, planGenerated, loading, error, select, refresh]
  );

  return <ScenarioContext.Provider value={value}>{children}</ScenarioContext.Provider>;
}

export function useScenario(): ScenarioContextValue {
  const ctx = useContext(ScenarioContext);
  if (!ctx) throw new Error('useScenario must be used within a ScenarioProvider');
  return ctx;
}
