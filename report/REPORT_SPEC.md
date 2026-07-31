# Specyfikacja raportu Power BI

## Założenia wspólne

Raport `OL_Siatka_Report` korzysta z modelu semantycznego Direct Lake. Globalne slicery: `hazard_code`, `phase`, `admin_division`, `task_module_id`, `status`, `day_offset`. Domyślny kontekst demo: `Z02`, `R`, `POWODZ_WRZESIEN_2026`. Raport ma wspierać rozmowę decyzyjną, a nie zastępować aplikację write-back.

## Strona 1 — Matryca ryzyka KPZK interaktywna

**Cel:** szybki wybór zagrożenia i pokaz ryzyka.  
**Odbiorca:** minister, RZZK viewer, dyrektor RCB.  
**Wizualizacje:** kafelki 20 zagrożeń (`hazard_code`, `hazard_name`, `color`, `risk_score`), matrix probability × impact, bar chart kategorii, card liczby zagrożeń.  
**Miary:** `Hazard Count`, `Average Risk Score`, `High Risk Hazards`, `Risk x Readiness Heatmap`.  
**Interakcje:** kliknięcie kafelka filtruje kolejne strony; tooltip pokazuje kategorię, prawdopodobieństwo, skutki i kolor.

## Strona 2 — Siatka bezpieczeństwa

**Cel:** pokazać macierz odpowiedzialności jako drill-through.  
**Odbiorca:** RCB coordinator, analityk ministerstwa.  
**Wizualizacje:** matrix `admin_name` × `hazard_name` z wartością `role`/`task_modules`, tabela szczegółowa modułów, slicer `phase`, legenda roli.  
**Pola:** `fact_safety_grid[hazard_code]`, `admin_division`, `phase`, `task_modules`, `role`, `criticality`.  
**Interakcje:** drill-through do panelu działu; kliknięcie komórki pokazuje moduły i ministerstwo. Conditional formatting: rola wiodąca wyróżniona.

## Strona 3 — Panel działu administracji

**Cel:** odpowiedzieć, co ma zrobić konkretny dział.  
**Odbiorca:** dyżurny ministerstwa i koordynator RCB.  
**Wizualizacje:** card ministerstwa, tabela zadań działu, donut statusów gotowości, tabela kontaktów, lista instytucji podległych.  
**Miary:** `Division Load`, `Ready Tasks`, `Blocked Tasks`, `Tasks Over SLA`, `Readiness %`.  
**Filtry:** `admin_division`, `role`, `task_module_id`, `status`.  
**Drill-through:** do historii deklaracji dla modułu.

## Strona 4 — Postęp aktywacji w zdarzeniu

**Cel:** pokazać oś D-1…D+10 i status aktywacji modułów.  
**Odbiorca:** dyrektor RCB, zespół operacyjny.  
**Wizualizacje:** timeline `day_offset` × `task_module_id`, stacked bar `activation_status`, line chart liczby aktywacji dziennie, tabela triggerów.  
**Pola:** `fact_task_activation[timestamp]`, `day_offset`, `task_module_id`, `leading_admin_division`, `activation_status`, `trigger`.  
**Interakcje:** kliknięcie dnia filtruje zadania i deklaracje; tooltip pokazuje dział wiodący i trigger.

## Strona 5 — Analiza luk

**Cel:** wskazać, co wymaga decyzji.  
**Odbiorca:** minister, RCB coordinator.  
**Wizualizacje:** KPI not ready/overdue/blocked, tabela `gap_analysis_overdue`, bar chart przeciążenia działów, graf odpowiedzialności jako custom visual lub link do JSON, heat-map ryzyko × gotowość.  
**Liczby kontrolne:** dla danych demo not ready **28**, overdue **28**, blocked **9**.  
**Interakcje:** kliknięcie blokady prowadzi do karty działu; filtr `critical_path=true` pokazuje moduły `[1,2,4,3]`; przycisk/bookmark „Eskalacja RZZK” pokazuje rekomendację SPO-1.

## Układ i standard wizualny

Nagłówek każdej strony: nazwa zdarzenia, zagrożenie, faza, timestamp ostatniej analizy. Lewy panel slicerów, prawa część treści. Kolory: zielony/żółty/czerwony/brązowy dla ryzyka; niebieski dla informacji; pomarańczowy dla SLA; czerwony dla blokad. Wszystkie tabele mają eksport do CSV i tooltip „dane syntetyczne demo”.

## Drill-through i nawigacja

Raport powinien mieć trzy ścieżki drill-through. Pierwsza: z kafelka zagrożenia na stronę siatki bezpieczeństwa z filtrem `hazard_code`. Druga: z komórki macierzy na panel działu z filtrami `admin_division`, `phase` i `hazard_code`. Trzecia: z tabeli blokad na stronę analizy luk z filtrem `task_module_id` i `status`. Przyciski nawigacyjne w nagłówku: `Ryzyko`, `Siatka`, `Dział`, `Aktywacja`, `Luki`. Każda strona powinna mieć tekstowy opis „jak czytać ekran”, aby prezenter mógł prowadzić demo bez dodatkowych notatek.

## Tooltipy i definicje

Do raportu dodaj tooltip page `Tooltip - Zadanie`, zawierający: `task_module_name`, opis modułu, `admin_name`, `ministry`, `role`, `criticality`, `sla_hours`, ostatni `status`, ostatni `comment`. Dla matrycy ryzyka tooltip ma pokazać `probability_label`, `impact_label`, `risk_score` i `color`. Dla stron decyzyjnych każdy KPI powinien mieć opis biznesowy: „blokada” oznacza status `zablokowane`, „po SLA” oznacza rekord z `gap_analysis_overdue`, a „przeciążenie” oznacza co najmniej 4 zadania wiodące w aktywnym planie.

## Wymagania prezentacyjne

Widok musi być czytelny na projektorze w sali posiedzeń. Minimalny rozmiar czcionki w tabelach: 10–11 pt, KPI: 28 pt, tytuły: 18 pt. Na każdej stronie umieść stopkę: „Dane syntetyczne demo, seed=42”. Eksport do PDF powinien działać dla pięciu stron, aby plan B mógł być pokazany bez dostępu do usługi Fabric.
