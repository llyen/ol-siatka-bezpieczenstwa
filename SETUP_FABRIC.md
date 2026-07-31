# Setup Microsoft Fabric — krok po kroku

## Założenia

Instrukcja zakłada, że lokalnie wygenerowano dane w `C:\repos\OchronaLudnosci\ol-siatka-bezpieczenstwa\datasets` i wyniki kontrolne w `datasets\derived`. Nazwy techniczne proponowane w Fabric są po angielsku bez polskich znaków: workspace `OL_Siatka_Demo_WS`, Lakehouse `OL_Siatka_Lakehouse`, semantic model `OL_Siatka_SemanticModel`, report `OL_Siatka_Report`, app `Siatka Bezpieczenstwa - Pulpit Koordynacji`.

## 1. Workspace i capacity

**Cel:** utworzyć odizolowaną przestrzeń demo.  
**Czynności:** w Fabric wybierz `Workspaces` → `New workspace`, nazwa `OL_Siatka_Demo_WS`. Przypisz capacity Fabric (np. F2+ w środowisku demo). Dodaj prowadzącego jako Admin, odbiorców demo jako Viewer.  
**Oczekiwany rezultat:** pusty workspace z aktywną capacity, widoczny w portalu Fabric.

## 2. Lakehouse

**Cel:** utworzyć jedno źródło prawdy.  
**Czynności:** `New item` → `Lakehouse`, nazwa `OL_Siatka_Lakehouse`. W sekcji Files utwórz folder `Files/ol-siatka/raw`. Wgraj wszystkie pliki z lokalnego `datasets\`: dim_admin_division.csv, dim_contact_point.csv, dim_hazard.csv, dim_spo.csv, dim_task_module.csv, fact_interdependency.csv, fact_readiness_declaration.jsonl, fact_safety_grid.csv, fact_spo_checklist.csv, fact_task_activation.jsonl.  
**Oczekiwany rezultat:** pliki są widoczne w OneLake, a liczby rekordów zgadzają się z `datasets\derived\dataset_counts.json`.

## 3. Notebook ładowania

**Cel:** zamienić pliki na tabele robocze.  
**Czynności:** utwórz notebook `01_load_grid`, wklej logikę z `notebooks\01_load_grid.py`. W Fabric zamień lokalne ścieżki na `Files/ol-siatka/raw` i zapisuj dane jako Delta tables: `dim_hazard`, `dim_admin_division`, `dim_task_module`, `fact_safety_grid`, `dim_spo`, `fact_spo_checklist`, `dim_contact_point`, `fact_interdependency`, `fact_readiness_declaration`, `fact_task_activation`.  
**Oczekiwany rezultat:** w Lakehouse pojawia się 10 tabel o wolumenach zgodnych z README.

## 4. Notebook aktywacji

**Cel:** tworzyć plan operacyjny dla zagrożenia/fazy/skali.  
**Czynności:** utwórz notebook `02_activation_engine`. Parametry: `hazard_code='Z02'`, `phase='R'`, `scale=4`. Zapisz wynik jako tabela `activation_plan` i opcjonalnie jako plik `Files/ol-siatka/derived/activation_plan_Z02_R.csv`.  
**Oczekiwany rezultat:** plan ma **44 zadań**, moduły `[1, 2, 4, 5, 7]` i `dependency_order` zgodny z `{'1': 1, '2': 2, '4': 3, '5': 4, '7': 5}`.

## 5. Notebook analizy luk

**Cel:** obliczyć statusy, SLA, przeciążenia i ścieżkę krytyczną.  
**Czynności:** utwórz notebook `03_gap_analysis`, jako wejście podłącz `activation_plan` i `fact_readiness_declaration`. Zapisz `gap_analysis_summary` i `gap_analysis_overdue`. Ustaw harmonogram odświeżania co 15 minut w trakcie demo.  
**Oczekiwany rezultat:** summary pokazuje **28 not ready**, **28 overdue**, **9 blocked**, przeciążenia `VIII` i `XIX`.

## 6. Notebook grafu

**Cel:** przygotować widok zależności organizacyjnych.  
**Czynności:** utwórz `04_graph_view`, użyj `NetworkX` jeśli jest dostępny albo trybu eksportu JSON. Zapisz tabelę/widok `responsibility_graph_nodes`, `responsibility_graph_edges` albo plik JSON.  
**Oczekiwany rezultat:** graf ma **12 nodes**, **20 edges** i **9 single points of failure**.

## 7. Model semantyczny

**Cel:** utworzyć wspólną warstwę miar.  
**Czynności:** `New semantic model` z Lakehouse, tryb Direct Lake. Relacje według `semantic-model\MODEL.md`. Utwórz bridge `bridge_grid_module` przez split `fact_safety_grid[task_modules]`, jeśli raport ma filtrować po pojedynczym module. Dodaj miary z `semantic-model\MEASURES.md`.  
**Oczekiwany rezultat:** model umożliwia liczenie `% gotowości`, zadań po SLA, blokad i obciążenia działu.

## 8. Raport Power BI

**Cel:** zbudować warstwę decyzyjną.  
**Czynności:** utwórz raport `OL_Siatka_Report` według `report\REPORT_SPEC.md`: 5 stron, slicery `hazard_code`, `phase`, `admin_division`, `task_module_id`, `status`.  
**Oczekiwany rezultat:** użytkownik widzi matrycę ryzyka, siatkę bezpieczeństwa, panel działu, postęp aktywacji i analizę luk.

## 9. Data Agent

**Cel:** odpowiadać językiem naturalnym.  
**Czynności:** utwórz Data Agent `OL_Siatka_Data_Agent`. Wklej instrukcję systemową z `ai\DATA_AGENT.md`. Udostępnij tabele: `dim_hazard`, `dim_admin_division`, `dim_task_module`, `fact_safety_grid`, `fact_readiness_declaration`, `fact_spo_checklist`, `activation_plan`, `gap_analysis_summary`. Dodaj przykładowe pytania.  
**Oczekiwany rezultat:** agent odpowiada np. kto odpowiada za łączność przy powodzi w odbudowie i które działy są przeciążone.

## 10. Fabric App / Rayfin

**Cel:** utworzyć aplikację operacyjną z write-back.  
**Czynności:** uruchom Rayfin/Fabric Apps, wklej `fabric-app\RAYFIN_PROMPT.md`, wskaż Lakehouse jako źródło, utwórz role `RCB coordinator`, `Ministry duty officer`, `RZZK viewer`, `Admin`. Skonfiguruj akcje zapisu do tabeli `fact_readiness_declaration_writeback` lub bezpośrednio do staging table.  
**Oczekiwany rezultat:** 5 ekranów aplikacji: wybór zagrożenia, lista zadań, karta działu, pulpit RCB, kontakty i SPO-1.

## 11. Data Activator

**Cel:** alerty i automatyzacja.  
**Czynności:** utwórz reguły według `activator\RULES.md`: SLA exceeded, Missing readiness declaration, Critical path blocker, Division overload, Disinformation coupling. Źródła: `gap_analysis_overdue`, `fact_readiness_declaration`, `activation_plan`. Odbiorcy: RCB coordinator, duty officer, opcjonalnie kanał Teams.  
**Oczekiwany rezultat:** alert jest generowany przy zadaniu po SLA lub blokadzie na ścieżce krytycznej.

## 12. Test end-to-end

**Cel:** sprawdzić, że działa pełna pętla.  
**Czynności:** wybierz `Z02/R/4`, wygeneruj plan, zmień status jednego zadania na `zablokowane`, odśwież analizę luk, sprawdź raport, zapytaj Data Agenta i wyzwól regułę Activator.  
**Oczekiwany rezultat:** ten sam status widać w aplikacji, raporcie, agencie i alertach.

## Lista kontrolna „czy działa”

- [ ] Workspace `OL_Siatka_Demo_WS` ma aktywną capacity.
- [ ] Lakehouse `OL_Siatka_Lakehouse` zawiera pliki raw.
- [ ] Tabela `dim_hazard` ma 20 rekordów.
- [ ] Tabela `fact_safety_grid` ma 1000 rekordów.
- [ ] Tabela `fact_readiness_declaration` ma 106 rekordów testowych.
- [ ] `activation_plan` dla `Z02/R/4` ma 44 zadań.
- [ ] `gap_analysis_summary` pokazuje 9 blokad.
- [ ] Raport filtruje po `hazard_code`, `phase` i `admin_division`.
- [ ] Miara `Readiness %` zwraca wartość, a nie blank.
- [ ] Fabric App zapisuje rekord write-back.
- [ ] Data Agent odpowiada na pytanie o `Z02` i moduł 4.
- [ ] Activator generuje testowe powiadomienie dla SLA.
- [ ] Ekran SPO-1 generuje listę uczestników.
- [ ] Plan B lokalny działa z plikami `datasets\derived`.

## Rozwiązywanie problemów

1. **Brak tabel po uploadzie.** Pliki są w Files, ale nie jako Tables. Uruchom notebook ładowania i zapisz DataFrame jako Delta table.
2. **Polskie znaki w danych wyglądają źle.** Sprawdź kodowanie UTF-8 przy uploadzie i odczycie CSV.
3. **Miary DAX zwracają blank.** Sprawdź relacje i bridge `bridge_grid_module`; listy modułów w `fact_safety_grid` są rozdzielone średnikami.
4. **Activation plan ma inną liczbę zadań.** Zweryfikuj parametry: musi być `Z02`, `R`, skala `4`, bez dodatkowych filtrów po roli.
5. **Data Agent miesza fazy R/O.** W instrukcji systemowej wymuś pytanie doprecyzowujące albo domyślny filtr `phase`.
6. **Write-back nie jest widoczny w raporcie.** Sprawdź, czy zapis trafia do tej samej tabeli/staging i czy model został odświeżony.
7. **Activator nie wysyła alertu.** Sprawdź, czy reguła obserwuje wynik po odświeżeniu `gap_analysis_overdue`, a nie stary plik.
8. **Brak dostępu dla przedstawiciela działu.** Sprawdź role Entra ID i filtr RLS po `admin_division`.
