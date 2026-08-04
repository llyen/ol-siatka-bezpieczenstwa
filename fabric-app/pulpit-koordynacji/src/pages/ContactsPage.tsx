import { useMemo, useState } from 'react';

import {
  Button,
  EmptyState,
  KpiCard,
  Panel,
  downloadCsv,
} from '@/components/ui';
import {
  CHECKLIST,
  CONTACTS,
  DIVISION_BY_CODE,
  SPO_LIST,
  buildParticipants,
  spoForHazard,
  toCsv,
} from '@/data/model';
import { useScenario } from '@/hooks/ScenarioContext';

/**
 * Ekran 5 - kontakty i procedura SPO.
 *
 * Lista uczestnikow nie jest statyczna: wynika z aktywnego planu, wiec zmiana
 * zagrozenia albo fazy zmienia sklad posiedzenia. To jest sedno demonstracji -
 * zwolanie zespolu przestaje byc reczna praca na zalaczniku do procedury.
 */
export function ContactsPage() {
  const { tasks, hazardCode, eventId } = useScenario();
  const relevant = useMemo(() => spoForHazard(hazardCode), [hazardCode]);
  const [spoCode, setSpoCode] = useState('SPO-1');
  const [done, setDone] = useState<Set<number>>(new Set());
  const [query, setQuery] = useState('');

  const spo = SPO_LIST.find((s) => s.spo_code === spoCode);
  const steps = useMemo(
    () => CHECKLIST.filter((c) => c.spo_code === spoCode).sort((a, b) => a.step_number - b.step_number),
    [spoCode]
  );

  const participants = useMemo(() => buildParticipants(tasks), [tasks]);
  const participantCodes = useMemo(
    () => new Set(participants.map((p) => p.admin_division)),
    [participants]
  );

  const filteredContacts = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return CONTACTS;
    return CONTACTS.filter((c) =>
      `${c.admin_division} ${c.unit} ${c.role} ${c.email} ${c.duty_phone} ${DIVISION_BY_CODE.get(c.admin_division)?.admin_name ?? ''}`
        .toLowerCase()
        .includes(q)
    );
  }, [query]);

  const toggle = (step: number) => {
    setDone((prev) => {
      const next = new Set(prev);
      if (next.has(step)) next.delete(step);
      else next.add(step);
      return next;
    });
  };

  const exportParticipants = () => {
    downloadCsv(
      `lista_uczestnikow_${eventId}.csv`,
      toCsv(
        participants.map((p) => ({
          dzial: p.admin_division,
          nazwa_dzialu: DIVISION_BY_CODE.get(p.admin_division)?.admin_name ?? '',
          ministerstwo: DIVISION_BY_CODE.get(p.admin_division)?.ministry ?? '',
          komorka: p.unit,
          rola: p.role,
          telefon_dyzurny: p.duty_phone,
          email: p.email,
          zastepca: p.deputy,
        }))
      )
    );
  };

  const teamsMessage = `Zwołanie RZZK — ${eventId}\nProcedura: ${spoCode} ${spo?.spo_name ?? ''}\nUczestnicy: ${participants.length} punktów kontaktowych (działy: ${participants.map((p) => p.admin_division).join(', ')})\nPodstawa: aktywny plan aktywacji zadań dla zagrożenia ${hazardCode}.`;

  const copyTeams = () => {
    void navigator.clipboard.writeText(teamsMessage);
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Uczestnicy posiedzenia" value={participants.length} hint="z aktywnego planu + RCB" />
        <KpiCard label="Kroki procedury" value={steps.length} hint={spoCode} />
        <KpiCard
          label="Odhaczone kroki"
          value={done.size}
          suffix={`/ ${steps.length}`}
          tone={done.size === steps.length && steps.length > 0 ? 'good' : 'warn'}
        />
        <KpiCard label="Procedury dla zagrożenia" value={relevant.length} hint={hazardCode} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel
          title="Procedura operacyjna"
          description={spo?.spo_name}
          actions={
            <select
              value={spoCode}
              onChange={(e) => {
                setSpoCode(e.target.value);
                setDone(new Set());
              }}
              className="rounded border border-slate-300 px-2 py-1.5 text-sm"
            >
              {(relevant.length > 0 ? relevant : SPO_LIST).map((s) => (
                <option key={s.spo_code} value={s.spo_code}>
                  {s.spo_code}
                </option>
              ))}
            </select>
          }
        >
          {steps.length === 0 ? (
            <EmptyState>Ta procedura nie ma zdefiniowanej listy kroków.</EmptyState>
          ) : (
            <ol className="space-y-2">
              {steps.map((s) => {
                const checked = done.has(s.step_number);
                return (
                  <li
                    key={s.step_number}
                    className={`flex gap-3 rounded border px-3 py-2 ${
                      checked ? 'border-emerald-200 bg-emerald-50' : 'border-slate-200'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggle(s.step_number)}
                      className="mt-1 h-4 w-4"
                    />
                    <div className="text-sm">
                      <div className={checked ? 'text-slate-500 line-through' : 'text-slate-800'}>
                        <span className="font-semibold">{s.step_number}.</span> {s.step_description}
                      </div>
                      <div className="mt-0.5 text-xs text-slate-500">
                        dział {s.responsible_admin_division} · SLA {s.sla_hours} h · dokument:{' '}
                        {s.required_document || 'brak'}
                      </div>
                    </div>
                  </li>
                );
              })}
            </ol>
          )}
        </Panel>

        <Panel
          title={`Lista uczestników (${participants.length})`}
          description="Skład wynika z aktywnego planu: działy wiodące i współpracujące oraz RCB jako organizator."
          actions={
            <>
              <Button onClick={exportParticipants}>Eksport CSV</Button>
              <Button onClick={copyTeams}>Kopiuj wiadomość Teams</Button>
            </>
          }
        >
          <div className="max-h-[26rem] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-white">
                <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-2 py-2">Dział</th>
                  <th className="px-2 py-2">Komórka dyżurna</th>
                  <th className="px-2 py-2">Telefon</th>
                </tr>
              </thead>
              <tbody>
                {participants.map((p) => (
                  <tr key={`${p.admin_division}-${p.email}`} className="border-b border-slate-100">
                    <td className="px-2 py-2">
                      <div className="font-semibold">{p.admin_division}</div>
                      <div className="text-xs text-slate-500">
                        {DIVISION_BY_CODE.get(p.admin_division)?.admin_name}
                      </div>
                    </td>
                    <td className="px-2 py-2 text-slate-700">{p.unit}</td>
                    <td className="px-2 py-2 tabular-nums text-slate-600">{p.duty_phone}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <pre className="mt-4 whitespace-pre-wrap rounded bg-slate-50 p-3 text-xs text-slate-600">
            {teamsMessage}
          </pre>
        </Panel>
      </div>

      <Panel
        title="Książka kontaktów"
        description="Pełny wykaz punktów kontaktowych. Wiersze wyróżnione należą do aktywnego planu."
        actions={
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Szukaj kontaktu…"
            className="rounded border border-slate-300 px-3 py-1.5 text-sm"
          />
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="px-2 py-2">Dział</th>
                <th className="px-2 py-2">Resort</th>
                <th className="px-2 py-2">Komórka</th>
                <th className="px-2 py-2">Telefon</th>
                <th className="px-2 py-2">E-mail</th>
                <th className="px-2 py-2">Zastępca</th>
              </tr>
            </thead>
            <tbody>
              {filteredContacts.map((c) => (
                <tr
                  key={`${c.admin_division}-${c.email}`}
                  className={`border-b border-slate-100 ${
                    participantCodes.has(c.admin_division) ? 'bg-blue-50/50' : ''
                  }`}
                >
                  <td className="px-2 py-2 font-semibold">{c.admin_division}</td>
                  <td className="px-2 py-2 text-xs text-slate-600">
                    {DIVISION_BY_CODE.get(c.admin_division)?.ministry}
                  </td>
                  <td className="px-2 py-2 text-slate-700">{c.unit}</td>
                  <td className="px-2 py-2 tabular-nums text-slate-600">{c.duty_phone}</td>
                  <td className="px-2 py-2 text-slate-600">{c.email}</td>
                  <td className="px-2 py-2 text-xs text-slate-500">{c.deputy}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
