import { describe, expect, it } from 'vitest';

import {
  buildParticipants,
  buildPlan,
  buildTaskState,
  computeDivisionLoad,
  computeKpis,
  toCsv,
} from '@/data/model';
import { validateDeclaration } from '@/services/readiness';

/**
 * Aplikacja liczy plan po stronie klienta, a dashboard i Activator po stronie KQL.
 * Te testy pilnuja, zeby obie sciezki dawaly ten sam wynik - rozjazd oznaczalby,
 * ze decydent widzi inna liczbe zadan w aplikacji niz na dashboardzie.
 */
describe('plan aktywacji', () => {
  const plan = buildPlan('Z02', 'R');

  it('daje 44 zadania dla scenariusza powodziowego, zgodnie z ActivationPlanZ02R', () => {
    expect(plan).toHaveLength(44);
  });

  it('pomija dzialy o roli wspierajacej', () => {
    expect(plan.every((t) => t.role !== 'wspierający')).toBe(true);
  });

  it('nie zawiera zadan bez modulu', () => {
    expect(plan.every((t) => t.task_module_id >= 1 && t.task_module_id <= 7)).toBe(true);
  });

  it('porzadkuje zadania wg glebokosci zaleznosci', () => {
    const orders = plan.map((t) => t.dependency_order);
    expect(orders).toEqual([...orders].sort((a, b) => a - b));
  });
});

describe('stan zadan', () => {
  const plan = buildPlan('Z02', 'R');

  it('deklaracja z aplikacji nadpisuje migawke z Eventhouse', () => {
    const target = plan[0];
    const tasks = buildTaskState(plan, [
      {
        admin_division: target.admin_division,
        task_module_id: target.task_module_id,
        status: 'zablokowane',
        comment: 'brak zasobow',
        forces_and_assets: '',
        declared_at: new Date('2099-01-01T00:00:00Z'),
      },
    ]);
    const updated = tasks.find((t) => t.key === target.key);
    expect(updated?.status).toBe('zablokowane');
    expect(updated?.from_app).toBe(true);
  });

  it('liczy wskazniki spojnie z liczba zadan', () => {
    const tasks = buildTaskState(plan, []);
    const kpis = computeKpis(tasks);
    expect(kpis.total).toBe(44);
    expect(kpis.ready + kpis.inProgress + kpis.notStarted + kpis.blocked).toBe(kpis.total);
    expect(kpis.readinessPct).toBe(Math.round((kpis.ready / kpis.total) * 100));
  });

  it('obciazenie dzialow sumuje sie do liczby zadan', () => {
    const tasks = buildTaskState(plan, []);
    const load = computeDivisionLoad(tasks);
    expect(load.reduce((sum, d) => sum + d.total, 0)).toBe(44);
  });

  it('lista uczestnikow zawsze obejmuje RCB', () => {
    const tasks = buildTaskState(plan, []);
    expect(buildParticipants(tasks).some((p) => p.admin_division === 'I')).toBe(true);
  });
});

describe('walidacja deklaracji', () => {
  const base = {
    event_id: 'POWODZ_WRZESIEN_2026',
    hazard_code: 'Z02',
    phase: 'R',
    admin_division: 'I',
    task_module_id: 1,
    status: 'w toku',
  };

  it('przepuszcza poprawna deklaracje w toku', () => {
    expect(validateDeclaration(base)).toHaveLength(0);
  });

  it('wymaga przyczyny przy blokadzie', () => {
    expect(validateDeclaration({ ...base, status: 'zablokowane' })).toHaveLength(1);
  });

  it('wymaga sil i srodkow przy gotowosci', () => {
    expect(validateDeclaration({ ...base, status: 'gotowe' })).toHaveLength(1);
    expect(
      validateDeclaration({ ...base, status: 'gotowe', forces_and_assets: 'zespoły=3' })
    ).toHaveLength(0);
  });

  it('odrzuca modul spoza zakresu 1-7', () => {
    expect(validateDeclaration({ ...base, task_module_id: 9 })).toHaveLength(1);
  });
});

describe('eksport CSV', () => {
  it('cytuje wartosci ze srednikiem', () => {
    const csv = toCsv([{ a: 'x;y', b: 1 }]);
    expect(csv).toBe('a;b\r\n"x;y";1');
  });
});
