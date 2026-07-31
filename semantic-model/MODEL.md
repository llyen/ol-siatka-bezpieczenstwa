# Model semantyczny — gwiazda

## Cel modelu

Model semantyczny `OL_Siatka_SemanticModel` jest wspólną warstwą analityczną dla Power BI, Fabric App, Data Agent i reguł Activator. Powinien działać w trybie **Direct Lake**, aby raport i aplikacja czytały te same tabele Lakehouse bez dodatkowego importu i bez tworzenia równoległych kopii danych. Model jest zaprojektowany jako gwiazda z kilkoma faktami zdarzeniowymi oraz wymiarami referencyjnymi KPZK.

## Tabele faktów

| Tabela | Ziarno | Rola w modelu |
|---|---|---|
| `fact_safety_grid` | `hazard_code + admin_division + phase` | Kanoniczna macierz odpowiedzialności: dział × zagrożenie × faza, lista modułów, rola, krytyczność. |
| `fact_readiness_declaration` | `timestamp + event_id + admin_division + task_module_id` | Zdarzenia write-back: status gotowości, blokady, komentarz, siły i środki. |
| `fact_task_activation` | `timestamp + event_id + day_offset + task_module_id` | Oś czasu aktywacji modułów D-1…D+10 dla scenariusza powodziowego. |
| `fact_spo_checklist` | `spo_code + step_number` | Kroki procedur SPO z SLA, odpowiedzialnym działem i dokumentem. |
| `fact_interdependency` | `task_module_id + depends_on_task_module_id` | Relacje zależności między modułami, używane do ścieżki krytycznej i reguł blokad. |
| `activation_plan` | `hazard_code + phase + scale + admin_division + task_module_id` | Wynik notebooka aktywacji; tabela robocza dla raportu i aplikacji. |
| `gap_analysis_overdue` | `admin_division + task_module_id + hazard_code + phase` | Zadania niegotowe po SLA, używane przez stronę analizy luk i Activator. |

## Wymiary

| Tabela | Ziarno | Atrybuty biznesowe |
|---|---|---|
| `dim_hazard` | `hazard_code` | nazwa zagrożenia, kategoria, probability, impact, risk_score, risk_level, color. |
| `dim_admin_division` | `admin_division` | nazwa działu, ministerstwo, instytucje podległe. |
| `dim_task_module` | `task_module_id` | nazwa modułu i opis. |
| `dim_spo` | `spo_code` | nazwa SPO i powiązane zagrożenia. |
| `dim_contact_point` | `admin_division` | syntetyczne dane dyżurnych; najlepiej ukryć w widokach decyzyjnych i używać w aplikacji. |
| `dim_date` | `date` | kalendarz wspólny dla timestampów deklaracji i aktywacji. |

## Tabela dat

Utwórz `dim_date` w modelu lub Lakehouse z zakresem obejmującym co najmniej `2026-09-14` do `2026-09-26`. Kolumny: `date`, `year`, `quarter`, `month_number`, `month_name`, `day`, `day_of_week`, `is_demo_window`. Relacje do faktów powinny używać kolumn daty wyprowadzonych z `timestamp`, np. `readiness_date` i `activation_date`. Tabela dat powinna być oznaczona jako Date table w Power BI.

## Relacje i kierunki filtrowania

| Od | Do | Kardynalność | Kierunek | Uzasadnienie |
|---|---|---|---|---|
| `dim_hazard[hazard_code]` | `fact_safety_grid[hazard_code]` | 1:* | single | Zagrożenie filtruje komórki siatki. |
| `dim_hazard[hazard_code]` | `fact_task_activation[hazard_code]` | 1:* | single | Zagrożenie filtruje oś aktywacji. |
| `dim_admin_division[admin_division]` | `fact_safety_grid[admin_division]` | 1:* | single | Dział filtruje macierz odpowiedzialności. |
| `dim_admin_division[admin_division]` | `fact_readiness_declaration[admin_division]` | 1:* | single | Dział filtruje deklaracje. |
| `dim_admin_division[admin_division]` | `fact_spo_checklist[responsible_admin_division]` | 1:* | single | Dział filtruje kroki SPO. |
| `dim_task_module[task_module_id]` | `fact_readiness_declaration[task_module_id]` | 1:* | single | Moduł filtruje statusy gotowości. |
| `dim_task_module[task_module_id]` | `fact_task_activation[task_module_id]` | 1:* | single | Moduł filtruje aktywacje. |
| `dim_spo[spo_code]` | `fact_spo_checklist[spo_code]` | 1:* | single | Procedura filtruje checklistę. |
| `dim_date[date]` | `fact_readiness_declaration[readiness_date]` | 1:* | single | Analiza deklaracji w czasie. |
| `dim_date[date]` | `fact_task_activation[activation_date]` | 1:* | single | Analiza aktywacji w czasie. |

Dla `fact_safety_grid[task_modules]` zalecane jest utworzenie bridge `bridge_grid_module` przez rozbicie listy rozdzielonej średnikami. Relacje: `fact_safety_grid[grid_key]` 1:* `bridge_grid_module[grid_key]` oraz `dim_task_module[task_module_id]` 1:* `bridge_grid_module[task_module_id]`. Kierunek filtrowania pozostaje single, aby uniknąć dwuznacznych ścieżek.

## Hierarchie

- **Dział → ministerstwo:** praktycznie najlepiej prezentować jako `ministry` → `admin_name`, mimo że formalne ziarno działu jest niżej. Umożliwia szybkie grupowanie obciążenia resortowego.
- **Zagrożenie → kategoria:** `category` → `hazard_name` → `hazard_code`; sortowanie po `risk_score` malejąco lub kodzie zagrożenia.
- **Moduł → faza:** w raportach użyj hierarchii prezentacyjnej `phase` → `task_module_name`, bo moduł jest wykonywany w kontekście fazy `R/O`.
- **SPO → krok:** `spo_code` → `step_number` → `step_description`.
- **Data:** `year` → `month_name` → `date`; dla demo można dodać `day_offset` z `fact_task_activation` jako osobną oś zdarzenia.

## Kolumny ukryte

Ukryj techniczne kolumny pomocnicze: `grid_key`, klucze bridge, surowe listy `task_modules` po utworzeniu bridge, pola systemowe write-back (`writeback_id`, `source_user`, `validation_status`) oraz długie pola opisowe w widokach KPI. Nie ukrywaj `comment` w tabelach operacyjnych, bo jest potrzebny do diagnozy blokad.

## Sortowanie i formatowanie

- `hazard_code` sortuj rosnąco `Z01…Z20`; opcjonalnie dodaj `hazard_sort` jako liczbową część kodu.
- `admin_division` sortuj według katalogowego porządku I–XXV; zalecane jest dodanie `admin_sort`.
- `task_module_id` sortuje `task_module_name`.
- `spo_code` sortuj po liczbie po prefiksie `SPO-`.
- Miary procentowe formatuj jako Percentage z 1 miejscem dziesiętnym; SLA jako Whole number z sufiksem `h`; indeksy jako Decimal 0.00.

## Tryb przechowywania

Rekomendowany tryb to **Direct Lake** dla tabel Lakehouse. Uzasadnienie: demo pokazuje jedną platformę danych, a Direct Lake minimalizuje opóźnienie między write-back w aplikacji, odświeżeniem analiz i raportem. Import można stosować tylko jako plan B offline lub przy bardzo małych prezentacjach bez dostępu do capacity. DirectQuery do SQL endpoint nie jest preferowany, bo wprowadza dodatkową warstwę i zwykle gorszą responsywność dla modelu gwiazdy.
