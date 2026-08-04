/**
 * Warstwa domenowa siatki bezpieczenstwa.
 *
 * Zrodlem prawdy jest Eventhouse. Aplikacja pracuje na jego migawce
 * (src/data/reference.json, generowanej przez tools/export_reference.ps1),
 * bo Rayfin ma wlasna baze SQL i nie siega do Eventhouse ani Lakehouse.
 * Reguly generowania planu sa tu powtorzone jeden do jednego wzgledem funkcji
 * ActivationPlanZ02R z kql/02_update_policies.kql - dzieki temu aplikacja,
 * dashboard i Activator pokazuja te same 44 zadania dla scenariusza powodziowego.
 */
import raw from './reference.json';

export interface Hazard {
  hazard_code: string;
  hazard_name: string;
  category: string;
  probability: number;
  probability_label: string;
  impact: number;
  impact_label: string;
  risk_score: number;
  risk_level: string;
  color: string;
}

export interface Division {
  admin_division: string;
  admin_name: string;
  ministry: string;
  subordinate_institutions: string;
}

export interface TaskModule {
  task_module_id: number;
  task_module_name: string;
  description: string;
}

export interface Spo {
  spo_code: string;
  spo_name: string;
  related_hazards: string;
}

export interface Contact {
  admin_division: string;
  role: string;
  unit: string;
  duty_phone: string;
  email: string;
  deputy: string;
}

export interface ChecklistStep {
  spo_code: string;
  step_number: number;
  step_description: string;
  responsible_admin_division: string;
  sla_hours: number;
  required_document: string;
}

export interface Interdependency {
  task_module_id: number;
  depends_on_task_module_id: number;
  dependency_reason: string;
}

export interface GridRow {
  hazard_code: string;
  admin_division: string;
  phase: string;
  task_modules: string;
  role: string;
  criticality: string;
}

export interface ActivationRow {
  task_module_id: number;
  activation_status: string;
  leading_admin_division: string;
  trigger_reason: string;
  day_offset: number;
  timestamp: string;
}

export interface ReadinessRow {
  admin_division: string;
  task_module_id: number;
  status: string;
  comment: string;
  forces_and_assets: string;
  timestamp: string;
}

interface ReferenceFile {
  generatedAt: string;
  source: string;
  hazards: Hazard[];
  divisions: Division[];
  modules: TaskModule[];
  spo: Spo[];
  contacts: Contact[];
  checklist: ChecklistStep[];
  interdependency: Interdependency[];
  grid: GridRow[];
  activation: ActivationRow[];
  readiness: ReadinessRow[];
}

export const reference = raw as unknown as ReferenceFile;

export const HAZARDS = reference.hazards;
export const DIVISIONS = reference.divisions;
export const MODULES = reference.modules;
export const SPO_LIST = reference.spo;
export const CONTACTS = reference.contacts;
export const CHECKLIST = reference.checklist;
export const INTERDEPENDENCY = reference.interdependency;
export const GRID = reference.grid;
export const ACTIVATION = reference.activation;
export const BASELINE_READINESS = reference.readiness;

export const DIVISION_BY_CODE = new Map(DIVISIONS.map((d) => [d.admin_division, d]));
export const MODULE_BY_ID = new Map(MODULES.map((m) => [m.task_module_id, m]));
export const HAZARD_BY_CODE = new Map(HAZARDS.map((h) => [h.hazard_code, h]));

/** Statusy deklaracji gotowosci w kolejnosci narastania zaawansowania. */
export const STATUSES = ['nie rozpoczęto', 'w toku', 'gotowe', 'zablokowane'] as const;
export type ReadinessStatus = (typeof STATUSES)[number];

/**
 * Sciezka krytyczna scenariusza powodziowego: rozpoznanie, dystrybucja pomocy,
 * ewakuacja i zabezpieczenie infrastruktury. Ta sama definicja co w funkcji
 * CriticalPathBlockers w KQL.
 */
export const CRITICAL_PATH_MODULES = [1, 2, 3, 4];

/** Prog przeciazenia dzialu wiodacego - zgodny z activator/RULES.md. */
export const OVERLOAD_THRESHOLD = 4;

export interface PlanTask {
  key: string;
  admin_division: string;
  admin_name: string;
  ministry: string;
  task_module_id: number;
  task_module_name: string;
  role: string;
  criticality: string;
  sla_hours: number;
  depends_on: number[];
  /** Kolejnosc wynikajaca z zaleznosci miedzy modulami: 1 = brak poprzednikow. */
  dependency_order: number;
}

const CRITICALITY_ORDER: Record<string, number> = {
  krytyczna: 0,
  wysoka: 1,
  średnia: 2,
  srednia: 2,
  niska: 3,
};

export function criticalityRank(value: string): number {
  return CRITICALITY_ORDER[value] ?? 9;
}

/** Rola wiodaca zapisana jest z polskim znakiem, ale sprawdzamy oba warianty. */
export function isLeading(role: string): boolean {
  return role === 'wiodący' || role === 'wiodacy';
}

function isSupporting(role: string): boolean {
  return role === 'wspierający' || role === 'wspierajacy';
}

/**
 * Glebokosc modulu w grafie zaleznosci. Graf jest plytki (7 modulow, 7 krawedzi),
 * wiec liczymy rekurencyjnie z zabezpieczeniem przed cyklem.
 */
const dependsOnMap = new Map<number, number[]>();
for (const row of INTERDEPENDENCY) {
  const list = dependsOnMap.get(row.task_module_id) ?? [];
  list.push(row.depends_on_task_module_id);
  dependsOnMap.set(row.task_module_id, list);
}

function dependencyDepth(moduleId: number, seen = new Set<number>()): number {
  if (seen.has(moduleId)) return 1;
  seen.add(moduleId);
  const parents = dependsOnMap.get(moduleId);
  if (!parents || parents.length === 0) return 1;
  return 1 + Math.max(...parents.map((p) => dependencyDepth(p, new Set(seen))));
}

/** SLA kroku SPO odpowiedzialnego dzialu; 12 h to wartosc domyslna jak w Activatorze. */
const slaByDivision = new Map<string, number>();
for (const step of CHECKLIST) {
  const current = slaByDivision.get(step.responsible_admin_division);
  if (current === undefined || step.sla_hours < current) {
    slaByDivision.set(step.responsible_admin_division, step.sla_hours);
  }
}

/**
 * Plan aktywacji dla zagrozenia i fazy.
 *
 * Dwa filtry sa merytoryczne, nie kosmetyczne:
 * dzialy o roli wspierajacej nie generuja zadan operacyjnych, a pusta lista
 * modulow oznacza deklaracje obecnosci w siatce bez konkretnego zadania.
 * Bez nich Z02/R daje 59 wierszy zamiast 44 opisanych w dokumentacji scenariusza.
 */
export function buildPlan(hazardCode: string, phase: string): PlanTask[] {
  const tasks: PlanTask[] = [];
  for (const row of GRID) {
    if (row.hazard_code !== hazardCode || row.phase !== phase) continue;
    if (isSupporting(row.role)) continue;
    if (!row.task_modules) continue;
    for (const part of row.task_modules.split(';')) {
      const trimmed = part.trim();
      if (!trimmed) continue;
      const moduleId = Number(trimmed);
      if (!Number.isFinite(moduleId)) continue;
      const division = DIVISION_BY_CODE.get(row.admin_division);
      const mod = MODULE_BY_ID.get(moduleId);
      tasks.push({
        key: `${row.admin_division}/${moduleId}`,
        admin_division: row.admin_division,
        admin_name: division?.admin_name ?? row.admin_division,
        ministry: division?.ministry ?? '',
        task_module_id: moduleId,
        task_module_name: mod?.task_module_name ?? `Moduł ${moduleId}`,
        role: row.role,
        criticality: row.criticality,
        sla_hours: slaByDivision.get(row.admin_division) ?? 12,
        depends_on: dependsOnMap.get(moduleId) ?? [],
        dependency_order: dependencyDepth(moduleId),
      });
    }
  }
  tasks.sort(
    (a, b) =>
      a.dependency_order - b.dependency_order ||
      criticalityRank(a.criticality) - criticalityRank(b.criticality) ||
      a.task_module_id - b.task_module_id ||
      a.admin_division.localeCompare(b.admin_division)
  );
  return tasks;
}

export interface TaskState extends PlanTask {
  status: ReadinessStatus;
  comment: string;
  forces_and_assets: string;
  declared_at: string | null;
  /** true, gdy stan pochodzi z deklaracji zapisanej w aplikacji, a nie z migawki. */
  from_app: boolean;
  activation_status: string | null;
  overdue: boolean;
  on_critical_path: boolean;
}

export interface DeclarationInput {
  admin_division: string;
  task_module_id: number;
  status: string;
  comment?: string | null;
  forces_and_assets?: string | null;
  declared_at: string | Date;
}

const activationByModule = new Map(ACTIVATION.map((a) => [a.task_module_id, a]));

/**
 * Naklada na plan migawke z Eventhouse i deklaracje zapisane w aplikacji.
 * Deklaracja z aplikacji zawsze wygrywa, bo powstala pozniej niz migawka.
 */
export function buildTaskState(
  plan: PlanTask[],
  appDeclarations: DeclarationInput[]
): TaskState[] {
  const baseline = new Map<string, ReadinessRow>();
  for (const row of BASELINE_READINESS) {
    baseline.set(`${row.admin_division}/${row.task_module_id}`, row);
  }

  const latestFromApp = new Map<string, DeclarationInput>();
  for (const decl of appDeclarations) {
    const key = `${decl.admin_division}/${decl.task_module_id}`;
    const current = latestFromApp.get(key);
    if (!current || new Date(decl.declared_at) > new Date(current.declared_at)) {
      latestFromApp.set(key, decl);
    }
  }

  return plan.map((task) => {
    const fromApp = latestFromApp.get(task.key);
    const snapshot = baseline.get(task.key);
    const source = fromApp ?? snapshot;
    const status = (source?.status as ReadinessStatus) ?? 'nie rozpoczęto';
    const declaredAt = fromApp
      ? new Date(fromApp.declared_at).toISOString()
      : (snapshot?.timestamp ?? null);
    const activation = activationByModule.get(task.task_module_id);
    // Modul uznajemy za uruchomiony takze w fazie wygaszania - to nadal
    // stan operacyjny, a nie brak aktywacji.
    const started =
      activation?.activation_status === 'aktywny' ||
      activation?.activation_status === 'wygaszanie';
    return {
      ...task,
      status,
      comment: source?.comment ?? '',
      forces_and_assets: source?.forces_and_assets ?? '',
      declared_at: declaredAt,
      from_app: Boolean(fromApp),
      activation_status: activation?.activation_status ?? null,
      // Po SLA jest zadanie z uruchomionego modulu, ktore nie jest domkniete.
      overdue: started && status !== 'gotowe',
      on_critical_path: CRITICAL_PATH_MODULES.includes(task.task_module_id),
    };
  });
}

export interface Kpis {
  total: number;
  leading: number;
  ready: number;
  inProgress: number;
  notStarted: number;
  blocked: number;
  overdue: number;
  readinessPct: number;
  criticalPathBlockers: number;
  overloadedDivisions: number;
}

export function computeKpis(tasks: TaskState[]): Kpis {
  const total = tasks.length;
  const ready = tasks.filter((t) => t.status === 'gotowe').length;
  const blocked = tasks.filter((t) => t.status === 'zablokowane').length;
  const leadCounts = new Map<string, number>();
  for (const t of tasks) {
    if (isLeading(t.role)) {
      leadCounts.set(t.admin_division, (leadCounts.get(t.admin_division) ?? 0) + 1);
    }
  }
  return {
    total,
    leading: tasks.filter((t) => isLeading(t.role)).length,
    ready,
    inProgress: tasks.filter((t) => t.status === 'w toku').length,
    notStarted: tasks.filter((t) => t.status === 'nie rozpoczęto').length,
    blocked,
    overdue: tasks.filter((t) => t.overdue).length,
    readinessPct: total === 0 ? 0 : Math.round((ready / total) * 100),
    criticalPathBlockers: tasks.filter(
      (t) => t.on_critical_path && t.status === 'zablokowane'
    ).length,
    overloadedDivisions: [...leadCounts.values()].filter(
      (n) => n >= OVERLOAD_THRESHOLD
    ).length,
  };
}

export interface DivisionLoad {
  admin_division: string;
  admin_name: string;
  leading: number;
  total: number;
  ready: number;
  blocked: number;
}

export function computeDivisionLoad(tasks: TaskState[]): DivisionLoad[] {
  const map = new Map<string, DivisionLoad>();
  for (const t of tasks) {
    const entry = map.get(t.admin_division) ?? {
      admin_division: t.admin_division,
      admin_name: t.admin_name,
      leading: 0,
      total: 0,
      ready: 0,
      blocked: 0,
    };
    entry.total += 1;
    if (isLeading(t.role)) entry.leading += 1;
    if (t.status === 'gotowe') entry.ready += 1;
    if (t.status === 'zablokowane') entry.blocked += 1;
    map.set(t.admin_division, entry);
  }
  return [...map.values()].sort(
    (a, b) => b.leading - a.leading || b.total - a.total
  );
}

/**
 * Lista uczestnikow posiedzenia RZZK wg SPO-1: dzialy wiodace i wspolpracujace
 * z aktywnego planu plus RCB (dzial I) jako organizator.
 */
export function buildParticipants(tasks: TaskState[]): Contact[] {
  const codes = new Set(tasks.map((t) => t.admin_division));
  codes.add('I');
  return CONTACTS.filter((c) => codes.has(c.admin_division)).sort((a, b) =>
    a.admin_division.localeCompare(b.admin_division, 'pl', { numeric: false })
  );
}

export function spoForHazard(hazardCode: string): Spo[] {
  return SPO_LIST.filter((s) =>
    s.related_hazards.split(';').map((x) => x.trim()).includes(hazardCode)
  );
}

export function toCsv(rows: Record<string, unknown>[]): string {
  if (rows.length === 0) return '';
  const headers = Object.keys(rows[0]);
  const escape = (v: unknown) => {
    const s = v === null || v === undefined ? '' : String(v);
    return /[";\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [
    headers.join(';'),
    ...rows.map((r) => headers.map((h) => escape(r[h])).join(';')),
  ].join('\r\n');
}
