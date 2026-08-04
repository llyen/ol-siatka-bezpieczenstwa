import { entity, role, text, int, date, uuid } from '@microsoft/rayfin-core';

/**
 * Wniosek o eskalacje do RZZK skladany z pulpitu koordynatora RCB.
 *
 * Eskalacja jest w scenariuszu jedyna akcja, ktora wychodzi poza siatke
 * bezpieczenstwa i uruchamia procedure SPO-1 (zwolanie zespolu). Zapisujemy
 * migawke wskaznikow z chwili zlozenia wniosku, bo uzasadnienie eskalacji
 * musi byc czytelne pozniej, kiedy stan gotowosci juz sie zmieni.
 */
@entity()
@role('authenticated', ['create', 'read'])
@role('authenticated', ['update', 'delete'], {
  policy: (claims, item) => claims.sub.eq(item.requested_by),
})
export class EscalationRequest {
  @uuid() id!: string;
  @text({ max: 60 }) event_id!: string;
  @text({ max: 10 }) hazard_code!: string;
  @text({ max: 4 }) phase!: string;
  @int() event_scale!: number;
  @text({ max: 20 }) recommended_spo!: string;
  @text({ max: 1000 }) justification!: string;
  /** Migawka wskaznikow z chwili zlozenia wniosku. */
  @int() readiness_pct!: number;
  @int() blockers_count!: number;
  @int() overdue_count!: number;
  @int() participants_count!: number;
  /** zlozony | przyjety | odrzucony */
  @text({ max: 20 }) status!: string;
  @text({ max: 200 }) requested_by!: string;
  @text({ max: 200 }) requested_by_name!: string;
  @date() requested_at!: Date;
}

