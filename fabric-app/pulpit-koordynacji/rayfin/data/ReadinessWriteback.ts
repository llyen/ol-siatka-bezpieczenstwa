import { entity, role, text, int, date, uuid } from '@microsoft/rayfin-core';

/**
 * Deklaracja gotowosci zapisana z aplikacji.
 *
 * Odpowiednik tabeli fact_readiness_declaration_writeback z RAYFIN_PROMPT.md.
 * Deklaracja jest zdarzeniem, nie stanem - dzial moze zglaszac ten sam modul
 * wielokrotnie, a obowiazuje ostatni zapis. Dlatego encja nie ma klucza
 * naturalnego na parze (admin_division, task_module_id) i nigdy nie jest
 * aktualizowana w miejscu.
 *
 * Odczyt jest wspolny dla wszystkich zalogowanych - koordynator RCB i RZZK
 * musza widziec calosc. Zapis przypisuje autora, a modyfikacja i usuniecie
 * sa mozliwe wylacznie dla wlasnego wpisu, wiec dyzurny nie skasuje deklaracji
 * innego resortu.
 */
@entity()
@role('authenticated', ['create', 'read'])
@role('authenticated', ['update', 'delete'], {
  policy: (claims, item) => claims.sub.eq(item.source_user),
})
export class ReadinessWriteback {
  @uuid() id!: string;
  @text({ max: 60 }) event_id!: string;
  @text({ max: 10 }) hazard_code!: string;
  @text({ max: 4 }) phase!: string;
  @text({ max: 10 }) admin_division!: string;
  @int() task_module_id!: number;
  /** gotowe | w toku | nie rozpoczeto | zablokowane */
  @text({ max: 20 }) status!: string;
  @text({ max: 500 }) comment?: string;
  @text({ max: 300 }) forces_and_assets?: string;
  @text({ max: 200 }) source_user!: string;
  @text({ max: 200 }) source_user_name!: string;
  @date() declared_at!: Date;
}

