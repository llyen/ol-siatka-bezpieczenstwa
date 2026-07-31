# Architektura rozwiązania

## Cel architektury

Architektura tego repozytorium ma pokazać decydentowi nie „kolejny dashboard”, lecz kompletny cyfrowy obieg siatki bezpieczeństwa: od danych referencyjnych KPZK, przez automatyczne wygenerowanie planu zadań, po potwierdzenie gotowości działu i eskalację do RZZK. Najważniejsza decyzja projektowa brzmi: **jednym źródłem prawdy jest Lakehouse**, a wszystkie warstwy — raport, aplikacja, agent i reguły — korzystają z tych samych tabel.

## 1. Źródła danych

Warstwa źródeł jest syntetyczna, ale zaprojektowana tak, aby przypominała realny rejestr operacyjny. Zawiera 20 zagrożeń KPZK, 25 działów administracji, 7 modułów zadaniowych, 16 procedur SPO oraz fakty zdarzeniowe dla scenariusza `POWODZ_WRZESIEN_2026`. Pliki `CSV` reprezentują dane referencyjne i macierz odpowiedzialności, a `JSONL` reprezentuje wpisy zdarzeniowe: deklaracje gotowości i aktywacje modułów w osi czasu.

W prawdziwym wdrożeniu źródłami nie byłyby tylko pliki. Część danych przychodziłaby z systemów RCB, obiegów dokumentów ministerstw, repozytoriów planów zarządzania kryzysowego, systemów dyżurnych, katalogów kontaktów, usług telemetrii, a także ręcznego write-back z aplikacji. Repozytorium pokazuje minimalny wspólny model, na którym można rozmawiać o integracji.

## 2. Lakehouse

Lakehouse jest warstwą konsolidacji. W demie pliki z `datasets\` są ładowane przez `notebooks\01_load_grid.py` do podglądu `datasets\derived\lakehouse_preview`. W Fabric ten sam krok należy zamienić na tabele Delta w `OL_Siatka_Lakehouse`. Tabele wymiarów pozostają względnie stabilne, a fakty zdarzeniowe mogą być dopisywane przez aplikację lub pipeline.

Uzasadnienie wyboru Lakehouse: jedna kopia danych obsługuje zarówno analitykę batch, jak i aplikację operacyjną. Nie trzeba utrzymywać oddzielnego magazynu dla raportu, oddzielnego API dla aplikacji i oddzielnej bazy dla agenta. To obniża ryzyko niespójności: jeśli dział `XIII Łączność` zgłasza blokadę, widzi ją aplikacja, Power BI, Data Agent i reguła Activator.

## 3. Analityka notebookowa

Notebooki są warstwą logiki operacyjnej. `02_activation_engine.py` przyjmuje parametry `hazard_code`, `phase`, `scale` i generuje plan. Dla `Z02`, `R`, skala `4` powstaje **44 zadań** w modułach `[1, 2, 4, 5, 7]`. Kolejność wynika z zależności modułów: najpierw monitoring, potem zabezpieczenie ludności i łączność, następnie wsparcie i ochrona informacji.

`03_gap_analysis.py` porównuje plan z deklaracjami gotowości. Wynik kontrolny to **28 zadań bez gotowości**, **28 po SLA**, **9 blokad** i przeciążenia w działach `VIII` oraz `XIX`. `04_graph_view.py` tworzy graf odpowiedzialności: **12 węzłów**, **20 krawędzi** i **9 potencjalnych pojedynczych punktów awarii organizacyjnej**.

## 4. Warstwa semantyczna

Semantic model w trybie Direct Lake jest kontraktem dla raportu, Data Agenta i aplikacji. Model gwiazdy upraszcza relacje: `dim_hazard`, `dim_admin_division`, `dim_task_module` i `dim_spo` opisują fakty. Miary DAX definiują wspólny język decyzyjny: `% gotowości`, `zadania po SLA`, `blokady`, `obciążenie działu`, `indeks przygotowania` i heat-map ryzyko × gotowość.

## 5. Prezentacja: Power BI i Fabric App

Power BI odpowiada na pytania decyzyjne: gdzie jest największe ryzyko, który dział jest przeciążony, jaki jest postęp aktywacji. Fabric App odpowiada na pytania operacyjne: co kliknąć, aby potwierdzić gotowość, zgłosić blokadę, wygenerować listę uczestników SPO-1 i uruchomić eskalację do RZZK. Rozdzielenie tych warstw jest celowe: raport jest do obserwacji i analizy, aplikacja do działania.

## 6. Akcja: write-back, Data Agent, Activator

Write-back zapisuje nowe deklaracje w strukturze zgodnej z `fact_readiness_declaration`. Data Agent udostępnia interfejs języka naturalnego: „kto odpowiada za łączność przy powodzi w odbudowie?” albo „co blokuje ścieżkę krytyczną?”. Activator automatyzuje progi: przekroczenie SLA, brak deklaracji, blokada na ścieżce krytycznej i przeciążenie działu.

## Co byłoby inaczej produkcyjnie

W produkcji konieczne byłyby: klasyfikacja informacji i etykiety wrażliwości, rozdzielenie tenantów/środowisk, Private Link i kontrola sieci, integracja z Entra ID i grupami resortowymi, audyt write-back, wersjonowanie planów, podpisywanie decyzji, integracja z EZD/obiegiem dokumentów, kontrola dostępu per dział oraz procedury ciągłości działania. Dane kontaktowe musiałyby pochodzić z zatwierdzonego katalogu dyżurnego, a każde zgłoszenie blokady musiałoby mieć status formalny, właściciela i historię zmian.

## Przepływ danych end-to-end

1. Generator tworzy dane referencyjne i zdarzeniowe.
2. Lakehouse publikuje tabele do modelu semantycznego.
3. Notebook aktywacji tworzy plan dla `Z02/R/4`.
4. Aplikacja pokazuje zadania i zapisuje deklaracje.
5. Notebook luk oraz Activator wykrywają przekroczenia i blokady.
6. Power BI i Data Agent prezentują wspólną, aktualną odpowiedź.
7. Koordynator RCB eskaluje do RZZK, używając listy uczestników SPO-1.
