# Fabric App — „Siatka Bezpieczeństwa – Pulpit Koordynacji”

## Cel aplikacji

Aplikacja jest głównym elementem demo. Ma pokazać, że siatka bezpieczeństwa KPZK może działać jak narzędzie operacyjne: wybieram zagrożenie, generuję plan zadań, dział potwierdza gotowość lub zgłasza blokadę, RCB widzi skutki i eskaluje do RZZK. Aplikacja pracuje na tabelach Lakehouse i zapisuje statusy w modelu write-back zgodnym z `fact_readiness_declaration`.

## Role i uprawnienia

| Rola | Uprawnienia |
|---|---|
| `RCB coordinator` | Odczyt całości, generowanie planu, podgląd luk, eskalacja do RZZK, odczyt i korekta write-back. |
| `Ministry duty officer` | Odczyt zadań własnego `admin_division`, zapis deklaracji gotowości i blokad tylko dla własnego działu. |
| `RZZK viewer` | Tylko odczyt KPI, planu, listy uczestników i pakietu eskalacyjnego. |
| `Admin` | Konfiguracja słowników, mapowanie użytkowników do działów, ustawienia powiadomień. |

## Ekran 1 — Wybór zagrożenia

**Cel:** wybrać kontekst operacyjny.  
**Użytkownik:** RCB coordinator, RZZK viewer.  
**Wireframe:** nagłówek z nazwą zdarzenia; lewa część: siatka kafelków 20 zagrożeń; prawa część: panel parametrów `phase`, `event_scale`, `event_id`; dół: przycisk `Generate activation plan`.

**Pola i walidacje:**

| Pole | Typ | Walidacja | Źródło |
|---|---|---|---|
| `hazard_code` | string | wymagane, Z01–Z20 | `dim_hazard[hazard_code]` |
| `hazard_name` | string | read-only | `dim_hazard[hazard_name]` |
| `risk_score` | integer | read-only 1–25 | `dim_hazard[risk_score]` |
| `color` | string | mapowanie na kolor kafelka | `dim_hazard[color]` |
| `phase` | enum | wymagane: `R` albo `O` | parametr |
| `event_scale` | integer | wymagane 1–5 | parametr |
| `event_id` | string | wymagane | domyślnie `POWODZ_WRZESIEN_2026` |

**Akcje:** `Generate activation plan` uruchamia notebook/pipeline dla wybranych parametrów i tworzy `activation_plan`. Po sukcesie przejście do ekranu 2. Po błędzie komunikat: „Nie można wygenerować planu; sprawdź parametry i dostępność Lakehouse”.

## Ekran 2 — Lista zadań

**Cel:** pokazać plan operacyjny.  
**Użytkownik:** wszyscy, z filtrowaniem uprawnień.  
**Wireframe:** górny pasek KPI: liczba zadań, liczba modułów, liczba działów wiodących; centralnie tabela; panel filtrów po lewej; przycisk drill-through przy rekordzie.

**Źródła:** `activation_plan` (`hazard_code`, `phase`, `scale`, `task_module_id`, `task_module_name`, `admin_division`, `admin_name`, `ministry`, `role`, `criticality`, `sla_hours`, `dependency_order`) oraz `fact_readiness_declaration` dla statusu. Dla `Z02/R/4` oczekiwane jest **44 zadań**.

**Filtry:** `role`, `criticality`, `status`, `task_module_id`, `admin_division`, `po SLA`.  
**Przejścia:** kliknięcie działu → ekran 3; kliknięcie KPI blokady → ekran 4; kliknięcie modułu → szczegóły modułu.

## Ekran 3 — Karta działu administracji

**Cel:** zebrać deklaracje gotowości i blokady.  
**Użytkownik:** Ministry duty officer, RCB coordinator.  
**Wireframe:** nagłówek działu, karta kontaktowa, lista zadań działu, formularz deklaracji po prawej.

**Pola formularza write-back:**

| Pole | Typ | Walidacja |
|---|---|---|
| `timestamp` | datetime | nadawany automatycznie |
| `event_id` | string | wymagane |
| `admin_division` | string | zgodne z rolą użytkownika |
| `task_module_id` | integer | wymagane, 1–7 |
| `status` | enum | `nie rozpoczęto`, `w toku`, `gotowe`, `zablokowane` |
| `comment` | string | wymagane dla `zablokowane` i `w toku` |
| `forces_and_assets` | string | wymagane dla `gotowe` |
| `source_user` | string | z kontekstu logowania |
| `writeback_id` | string | GUID generowany przez aplikację |

**Efekt akcji:** `Confirm readiness` zapisuje status `gotowe`; `Report blocker` zapisuje `zablokowane`; `Save draft` zapisuje `w toku`. Rekord trafia do `fact_readiness_declaration_writeback` albo staging table, a pipeline scala go z `fact_readiness_declaration`.

## Ekran 4 — Pulpit koordynatora RCB

**Cel:** decyzja o eskalacji.  
**Użytkownik:** RCB coordinator, RZZK viewer.  
**Wireframe:** cztery duże KPI u góry, tabela blokad po lewej, ścieżka krytyczna po prawej, wykres przeciążenia działów na dole, przycisk `Escalate to RZZK`.

**Źródła:** `gap_analysis_summary`, `gap_analysis_overdue`, `responsibility_graph`, `activation_plan`.  
**Liczby kontrolne:** not ready **28**, overdue **28**, blocked **9**, przeciążone `VIII` i `XIX`.

**Akcje:** `Escalate to RZZK` tworzy rekord `escalation_request` z polami `event_id`, `reason`, `blocked_tasks`, `overdue_tasks`, `recommended_spo='SPO-1'`, `created_by`, `created_at`. Wysyła powiadomienie do kanału RCB/RZZK.

## Ekran 5 — Kontakty i SPO-1

**Cel:** przygotować formalne posiedzenie i listę uczestników.  
**Użytkownik:** RCB coordinator, RZZK viewer.  
**Wireframe:** wyszukiwarka kontaktów, tabela dyżurnych, karta `SPO-1`, lista kroków checklisty, przycisk `Generate participant list`.

**Źródła:** `dim_contact_point` (25 rekordów), `dim_spo`, `fact_spo_checklist`, aktywny `activation_plan`.  
**Akcje:** generowanie listy uczestników bierze działy `wiodący` i `współpracujący`, dołącza kontakty i tworzy eksport CSV/Teams message. Kroki SPO-1 są oznaczane jako `planned`, `in_progress`, `done` w tabeli write-back `spo_execution_status`.

## Model danych write-back

### `fact_readiness_declaration_writeback`

Ziarno: `writeback_id`. Pola: `writeback_id`, `timestamp`, `event_id`, `admin_division`, `task_module_id`, `status`, `comment`, `forces_and_assets`, `source_user`, `source_role`, `validation_status`.

### `escalation_request`

Ziarno: `escalation_id`. Pola: `escalation_id`, `event_id`, `created_at`, `created_by`, `reason`, `blocked_tasks`, `overdue_tasks`, `recommended_spo`, `rzzk_participant_list`, `status`.

### `spo_execution_status`

Ziarno: `event_id + spo_code + step_number`. Pola: `status`, `owner`, `updated_at`, `evidence_document`, `comment`.

## Obsługa błędów

- Brak Lakehouse: pokaż banner i wyłącz akcje zapisu.
- Brak uprawnień: komunikat „Nie masz uprawnień do działu `admin_division`”.
- Błąd walidacji: pole wymagane podświetlone, zapis zablokowany.
- Konflikt zapisu: pokaż ostatnią deklarację i poproś o potwierdzenie nadpisania.
- Nieudane powiadomienie: zapisz eskalację lokalnie i oznacz `notification_status='failed'`.
- Brak odświeżenia danych: pokaż timestamp ostatniej analizy i przycisk `Refresh status`.
