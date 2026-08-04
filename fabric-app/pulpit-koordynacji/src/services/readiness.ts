/**
 * Zapis zwrotny do bazy Rayfin.
 *
 * Deklaracja gotowosci jest zdarzeniem, nie stanem - zapisujemy zawsze nowy
 * wiersz, a stan biezacy wyznacza ostatni wpis dla pary (dzial, modul).
 * Ta sama zasada obowiazuje w Eventhouse (funkcja CurrentReadiness).
 *
 * W trybie lokalnym, bez backendu Fabric, dane trzymamy w pamieci, zeby
 * aplikacje dalo sie demonstrowac takze poza portalem.
 */
import { getRayfinClient, isLocalBackend } from './rayfinClient';

export interface ReadinessRecord {
  id: string;
  event_id: string;
  hazard_code: string;
  phase: string;
  admin_division: string;
  task_module_id: number;
  status: string;
  comment?: string | null;
  forces_and_assets?: string | null;
  source_user: string;
  source_user_name: string;
  declared_at: Date;
}

export interface EscalationRecord {
  id: string;
  event_id: string;
  hazard_code: string;
  phase: string;
  event_scale: number;
  recommended_spo: string;
  justification: string;
  readiness_pct: number;
  blockers_count: number;
  overdue_count: number;
  participants_count: number;
  status: string;
  requested_by: string;
  requested_by_name: string;
  requested_at: Date;
}

const READINESS_FIELDS = [
  'id',
  'event_id',
  'hazard_code',
  'phase',
  'admin_division',
  'task_module_id',
  'status',
  'comment',
  'forces_and_assets',
  'source_user',
  'source_user_name',
  'declared_at',
] as const;

const ESCALATION_FIELDS = [
  'id',
  'event_id',
  'hazard_code',
  'phase',
  'event_scale',
  'recommended_spo',
  'justification',
  'readiness_pct',
  'blockers_count',
  'overdue_count',
  'participants_count',
  'status',
  'requested_by',
  'requested_by_name',
  'requested_at',
] as const;

let memoryReadiness: ReadinessRecord[] = [];
let memoryEscalations: EscalationRecord[] = [];

function currentUser(): { id: string; name: string } {
  if (isLocalBackend()) return { id: 'local-dev', name: 'Tryb lokalny' };
  const session = getRayfinClient().auth.getSession();
  if (!session.isAuthenticated || !session.user) {
    throw new Error('Sesja wygasła. Zaloguj się ponownie, aby zapisać dane.');
  }
  const user = session.user as { id: string; email?: string; name?: string };
  return { id: user.id, name: user.name ?? user.email ?? user.id };
}

export async function listReadiness(eventId: string): Promise<ReadinessRecord[]> {
  if (isLocalBackend()) {
    return memoryReadiness.filter((r) => r.event_id === eventId);
  }
  const client = getRayfinClient();
  const rows = await client.data.ReadinessWriteback.select([...READINESS_FIELDS])
    .orderBy({ declared_at: 'desc' })
    .execute();
  return (rows as ReadinessRecord[])
    .map((r) => ({ ...r, declared_at: new Date(r.declared_at) }))
    .filter((r) => r.event_id === eventId);
}

export interface DeclareInput {
  event_id: string;
  hazard_code: string;
  phase: string;
  admin_division: string;
  task_module_id: number;
  status: string;
  comment?: string;
  forces_and_assets?: string;
}

/**
 * Walidacje odpowiadaja tresci RAYFIN_PROMPT.md. Komunikaty sa pisane pod
 * uzytkownika nietechnicznego - dyzurny ma wiedziec, czego brakuje, a nie
 * ktore pole formularza jest puste.
 */
export function validateDeclaration(input: DeclareInput): string[] {
  const errors: string[] = [];
  if (!Number.isInteger(input.task_module_id) || input.task_module_id < 1 || input.task_module_id > 7) {
    errors.push('Moduł zadaniowy musi mieć numer od 1 do 7.');
  }
  if (input.status === 'zablokowane' && !input.comment?.trim()) {
    errors.push('Zgłoszenie blokady wymaga opisu przyczyny - koordynator RCB musi wiedzieć, co odblokować.');
  }
  if (input.status === 'gotowe' && !input.forces_and_assets?.trim()) {
    errors.push('Potwierdzenie gotowości wymaga wskazania sił i środków, np. "zespoły=4; pojazdy=6; dyżury=24/7".');
  }
  if ((input.comment?.length ?? 0) > 500) {
    errors.push('Komentarz może mieć najwyżej 500 znaków.');
  }
  if ((input.forces_and_assets?.length ?? 0) > 300) {
    errors.push('Opis sił i środków może mieć najwyżej 300 znaków.');
  }
  return errors;
}

export async function declareReadiness(input: DeclareInput): Promise<ReadinessRecord> {
  const errors = validateDeclaration(input);
  if (errors.length > 0) throw new Error(errors.join(' '));

  const user = currentUser();
  const payload = {
    event_id: input.event_id,
    hazard_code: input.hazard_code,
    phase: input.phase,
    admin_division: input.admin_division,
    task_module_id: input.task_module_id,
    status: input.status,
    comment: input.comment?.trim() || undefined,
    forces_and_assets: input.forces_and_assets?.trim() || undefined,
    source_user: user.id,
    source_user_name: user.name,
    declared_at: new Date(),
  };

  if (isLocalBackend()) {
    const record: ReadinessRecord = { id: crypto.randomUUID(), ...payload };
    memoryReadiness = [record, ...memoryReadiness];
    return record;
  }

  const client = getRayfinClient();
  const created = await client.data.ReadinessWriteback.create(payload);
  return { ...(created as ReadinessRecord), declared_at: new Date((created as ReadinessRecord).declared_at) };
}

export async function listEscalations(eventId: string): Promise<EscalationRecord[]> {
  if (isLocalBackend()) {
    return memoryEscalations.filter((e) => e.event_id === eventId);
  }
  const client = getRayfinClient();
  const rows = await client.data.EscalationRequest.select([...ESCALATION_FIELDS])
    .orderBy({ requested_at: 'desc' })
    .execute();
  return (rows as EscalationRecord[])
    .map((r) => ({ ...r, requested_at: new Date(r.requested_at) }))
    .filter((r) => r.event_id === eventId);
}

export type EscalationInput = Omit<
  EscalationRecord,
  'id' | 'requested_by' | 'requested_by_name' | 'requested_at' | 'status'
>;

export async function requestEscalation(input: EscalationInput): Promise<EscalationRecord> {
  const user = currentUser();
  const payload = {
    ...input,
    status: 'złożony',
    requested_by: user.id,
    requested_by_name: user.name,
    requested_at: new Date(),
  };

  if (isLocalBackend()) {
    const record: EscalationRecord = { id: crypto.randomUUID(), ...payload };
    memoryEscalations = [record, ...memoryEscalations];
    return record;
  }

  const client = getRayfinClient();
  const created = await client.data.EscalationRequest.create(payload);
  return { ...(created as EscalationRecord), requested_at: new Date((created as EscalationRecord).requested_at) };
}
