# Datasets


> ⚠️ Wszystkie pliki w katalogu `datasets\` są syntetyczne, wygenerowane deterministycznie (`seed=42`) i służą wyłącznie do demo. Nie zawierają danych operacyjnych żadnej instytucji ani prawdziwych danych kontaktowych.

## Spis plików

| Plik | Rekordy | Opis |
|---|---:|---|
| `dim_hazard.csv` | 20 | Słownik 20 zagrożeń KPZK Z01–Z20 z kategorią, prawdopodobieństwem, skutkami, wynikiem ryzyka i kolorem matrycy. Ziarno: `hazard_code`. |
| `dim_admin_division.csv` | 25 | Słownik 25 działów administracji rządowej I–XXV wraz z ministerstwem i syntetyczną listą instytucji podległych. Ziarno: `admin_division`. |
| `dim_task_module.csv` | 7 | Słownik 7 modułów zadaniowych używanych w siatce bezpieczeństwa i aplikacji. Ziarno: `task_module_id`. |
| `fact_safety_grid.csv` | 1000 | Kanoniczna macierz dział administracji × zagrożenie × faza R/O z listą modułów, rolą i krytycznością. Ziarno: `hazard_code + admin_division + phase`. |
| `dim_spo.csv` | 16 | Słownik 16 Standardowych Procedur Operacyjnych z powiązaniem z zagrożeniami. Ziarno: `spo_code`. |
| `fact_spo_checklist.csv` | 64 | Checklisty wykonawcze dla SPO: opis kroku, dział odpowiedzialny, SLA i wymagany dokument. Ziarno: `spo_code + step_number`. |
| `dim_contact_point.csv` | 25 | Syntetyczna książka dyżurnych punktów kontaktowych dla każdego działu administracji. Ziarno: `admin_division`. |
| `fact_readiness_declaration.jsonl` | 106 | Zdarzeniowe deklaracje gotowości działów dla scenariusza POWÓDŹ WRZESIEŃ. Ziarno: `timestamp + event_id + admin_division + task_module_id`. |
| `fact_task_activation.jsonl` | 79 | Oś aktywacji modułów zadaniowych D-1…D+10 dla zagrożenia Z02 Powódź. Ziarno: `timestamp + event_id + day_offset + task_module_id`. |
| `fact_interdependency.csv` | 7 | Zależności między modułami używane do sortowania topologicznego i wykrywania blokad. Ziarno: `task_module_id + depends_on_task_module_id`. |


## Pliki pochodne

- `derived\dataset_counts.json` — rzeczywiste liczby rekordów.
- `derived\activation_plan_Z02_R.csv` i `.json` — plan aktywacji dla `Z02/R/4`, **44 zadań**.
- `derived\gap_analysis_summary.json` — wynik analizy: **28 not ready**, **28 overdue**, **9 blocked**.
- `derived\gap_analysis_overdue.csv` — szczegóły zadań po SLA.
- `derived\responsibility_graph.json` — graf odpowiedzialności: **12 nodes**, **20 edges**.
- `derived\realtime_dry_run.jsonl` — wynik lokalnego `simulate_realtime.py --dry-run`.
