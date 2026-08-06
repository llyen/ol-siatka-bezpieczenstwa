# Stan wdrozenia na Microsoft Fabric

Scenariusz: **Siatka bezpieczenstwa - koordynacja miedzyresortowa**
Workspace: `OL-ZK-Demo-Siatka` (`5965cbe7-b1f4-4c64-b397-5c78de66d1fc`)

## 1. Elementy w workspace

| Element | Typ | Id | Stan |
|---|---|---|---|
| `OL_SIA_Lakehouse` | Lakehouse | `56ca1277-c81f-4a76-9413-5e3fb880dea7` | wdrozony |
| `OL_SIA_Eventhouse` | Eventhouse / KQL DB | `a27ff4b5-c68b-4cf8-a4e2-4295a3e9b7ec` | wdrozony |
| `OL_SIA_Dashboard` | Real-Time Dashboard | `f55f4c59-92f2-459e-b696-6c8a3af51feb` | 5 stron, 24 kafelki |
| `OL_SIA_Activator` | Activator (Reflex) | `7da69e87-8620-46f1-857c-5d1fd0093a03` | 6 regul KQL |
| `pulpit-koordynacji` | Fabric App (AppBackend) | `2b1ed178-f1f6-4be4-a784-664e941c0e2d` | 5 ekranow, wdrozony |
| `pulpit-koordynacji` | SQL Database | `2fd3363a-6ff5-496b-bbda-036bfc87e54a` | 2 encje write-back |
| `OL_SIA_SemanticModel` | Semantic Model (Direct Lake) | `fdc12685-2bd8-468e-8154-409f64f391d8` | 38 miar, zweryfikowany |
| `OL_SIA_Raport` | Raport Power BI | `b0c69b84-1623-4658-b0be-6a80bd0128ef` | 5 stron, zweryfikowany |
| `agent_siatka_bezpieczenstwa` | Data Agent | `247ea3b8-bb8b-44b5-a6d0-d9e45bffe5ce` | 3 zrodla, zweryfikowany |
| Notatniki Spark | Notebook x7 | - | lancuch przechodzi |

Cluster Eventhouse: `https://trd-j90bphmup0kwg093yy.z3.kusto.fabric.microsoft.com`

## 2. Dane w Eventhouse

| Tabela | Wierszy | Zrodlo |
|---|---|---|
| `SafetyGrid` | 1000 | rejestr, `ingest` |
| `ReadinessDeclaration` | 106 | strumien, `replay.py` |
| `TaskActivation` | 79 | strumien, `replay.py` |
| `SpoChecklist` | 64 | rejestr |
| `dim_admin_division` | 25 | rejestr |
| `dim_contact_point` | 25 | rejestr |
| `dim_hazard` | 20 | rejestr |
| `dim_spo` | 16 | rejestr |
| `Interdependency` | 7 | rejestr |
| `dim_task_module` | 7 | rejestr |

Wszystkie licznosci zgadzaja sie z dokumentacja co do rekordu.

## 3. Funkcje curated

`kql/02_update_policies.kql` - 7 funkcji w folderze `Curated`. Sa wspolna warstwa dla
dashboardu, Activatora i Data Agenta, zeby kafelek i alert nigdy nie liczyly tego
samego inaczej.

`CurrentModuleActivation`, `CurrentReadiness`, `ActivationPlanZ02R`, `ReadinessGap`,
`DivisionLoad`, `CriticalPathBlockers`, `SpoStepsForFlood`.

Wartosci referencyjne potwierdzone na Fabric: plan **44 zadania** w 5 modulach,
luka gotowosci **28 zadan**, przeciazone dzialy wiodace **VIII i XIX po 5 zadan**.

## 4. Dashboard

24 kafelki na 5 stronach: `Obraz sytuacji`, `Gotowosc dzialow`, `Siatka i moduly`,
`Procedury SPO`, `Matryca ryzyka`. Publikacja przez `deploy/create_dashboard.ps1`,
schema_version 60.

Scenariusz nie ma ani jednej mapy - podzial administracyjny jest resortowy, a nie
terytorialny, wiec wspolrzedne nie nioslyby informacji. Ciezar wizualny przenosza
wykresy udzialowe i slupkowe.

Tylko kafelki 01-08 sa filtrowane oknem czasu. Strumien to zaledwie ~185 zdarzen na
11 dni sceny, a rejestry licza tysiace wierszy i nie zmieniaja sie - filtrowanie ich
czasem zostawiloby dashboard pusty przez wiekszosc cyklu.

Kafelek 07 „Kto jeszcze nie odpowiedzial" bywa pusty pod koniec cyklu i jest to
poprawne: oznacza, ze wszystkie dzialy z siatki zlozyly deklaracje.

## 5. Reguly Activatora

`deploy/create_activator.ps1` wdraza 6 funkcji `alert_*` wg `activator/RULES.md`.
Wszystkie zwracaja ten sam kontrakt kolumn (`alert_rule`, `alert_severity`, `alert_ts`,
`alert_key`, `current_value`, `threshold_value`, `spo`, `message`).

| Regula | Trafienia | Uwaga |
|---|---|---|
| `alert_sla_exceeded` | 28 | zgodne z wartoscia referencyjna z RULES.md |
| `alert_missing_readiness` | ~34 | zalezy od fazy cyklu odtwarzania |
| `alert_critical_path_blocker` | ~13 | narasta w trakcie cyklu |
| `alert_division_overload` | 2 | VIII i XIX, zgodnie z dokumentacja |
| `alert_disinformation_coupling` | 1 | w danych nie ma Z20, wiec dziala galaz ostrzegawcza |
| `alert_rzzk_escalation` | 1 | 3 z 3 przeslanek spelnione |

Powiadomienia (e-mail, Teams) dokancza sie w UI Activatora - publiczne API Fabric nie
wystawia jeszcze definicji regul powiadomien.

## 6. Symulacja czasu rzeczywistego

`scenario/run_scenario.ps1` - presety `demo`, `szybki`, `kulminacja`, `wolny`, `ciagly`.

Tempo wynosi **660x**, a nie 60x jak w pozostalych scenariuszach. Powod: scena jest
odwrotnoscia blackoutu - bardzo dluga (11 dni) i bardzo rzadka (185 zdarzen lacznie).
Przy 60x odtworzenie calego przebiegu trwaloby ponad cztery godziny zegara. Przy 660x
doba scenariusza mija w ok. 2,2 min, a caly przebieg D0...D+10 w ok. 22 min.

Znaczniki czasu sa przypinane do chwili uruchomienia, wiec dashboard pokazuje dane
na zywo niezaleznie od pory startu.

## 7. Napotkane problemy i rozstrzygniecia

**Plan aktywacji: 59 czy 44 zadania.** Zapytanie na kanonicznej siatce dawalo 59 zadan,
a dokumentacja mowila o 44. Przyczyna: brakowaly dwa filtry merytoryczne. Dzialy o roli
`wspierajacy` nie generuja zadan operacyjnych, a pusta lista modulow oznacza deklaracje
obecnosci bez konkretnego zadania. Po dodaniu obu warunkow `ActivationPlanZ02R()` zwraca
44 zadania, zgodnie z notatnikiem i README.

**`toint(split(...))` w KQL nie dziala.** `split` zwraca tablice dynamiczna, a `toint`
nie przyjmuje tablicy. Objawia sie jako `General_BadRequest` bez wskazania miejsca.
Poprawny wzorzec to `mv-expand modul = split(...) to typeof(string)`, a dopiero potem
`toint(modul)`.

**Notatnik `03_gap_analysis` mnozyl wiersze planu.** Deklaracja gotowosci jest zdarzeniem,
nie stanem - dzial zglasza sie kilka razy dla tego samego modulu. Bez redukcji do ostatniej
deklaracji LEFT JOIN rozdmuchiwal 44 wiersze planu do 71 i luka gotowosci wychodzila
wieksza niz sam plan. Po dodaniu okna `row_number` po `(admin_division, task_module_id)`
notatnik zwraca 28 zadan, zgodnie z wartoscia referencyjna.

**Strumienie leza w `Files/streams`, nie `Files/datasets`.** Notatnik `01b_load_streams`
szukal ich w zlym katalogu i konczyl sie `PATH_NOT_FOUND`.

**Progi czasowe regul nie moga uzywac `now()`.** Odtwarzanie wysyla zdarzenia paczkami,
wiec czolo strumienia potrafi wyprzedzic zegar hosta o kilkanascie minut. Przy `now()`
okno lapalo wylacznie zdarzenia z przyszlosci, roznica czasu wychodzila ujemna i regula
nigdy nie miala trafien. Rozwiazanie: zegar sceny liczony jako `max(timestamp)` strumienia.

**Progi SLA licza sie w czasie sceny, nie zegara.** Przy tempie 660x prog „6 godzin bez
deklaracji" to 33 sekundy zegara. Reguly przeliczaja odstepy przez mnoznik tempa, dzieki
czemu prog 14 h z `SpoChecklist` znaczy to samo niezaleznie od predkosci odtwarzania.

**Ostatni status modulu to `wygaszanie`, nie `aktywny`.** Reguly i kafelki liczace tylko
status `aktywny` gasly po pierwszej fali wygaszen. Za uruchomiony uznajemy modul o statusie
`aktywny` albo `wygaszanie` - wygaszanie oznacza, ze modul wciaz pracuje, tylko schodzi
z obciazenia.

**Tabela kumuluje sie miedzy cyklami.** W trybie `ciagly` odtwarzanie nie czysci danych,
wiec `leftanti` na calej tabeli jest zawsze pusty. Reguly wykrywajace brak zdarzenia musza
pracowac na oknie, a nie na calosci.

**Eventhouse sporadycznie zwraca HTTP 520** na `.create-or-alter table ... ingestion json
mapping`. Przy powtorzeniu przechodzi - krok `kql` warto uruchamiac dwa razy.

**Polityka retencji przyjmuje wylacznie zapis JSON.** Skladnia `softdelete = 30d
recoverability = enabled` daje 400.

## 8. Kolejnosc wdrozenia

```powershell
.\deploy\ensure_capacity.ps1
.\deploy\deploy_fabric.ps1 -Step items
.\deploy\deploy_fabric.ps1 -Step upload
.\deploy\deploy_fabric.ps1 -Step kql
.\deploy\deploy_fabric.ps1 -Step ingest
.\deploy\deploy_fabric.ps1 -Step kql      # ponownie - funkcje curated potrzebuja rejestrow
.\deploy\deploy_fabric.ps1 -Step verify
.\deploy\import_notebooks.ps1 -WorkspaceName OL-ZK-Demo-Siatka
.\deploy\run_notebooks.ps1   -WorkspaceName OL-ZK-Demo-Siatka
.\deploy\create_dashboard.ps1
.\deploy\create_activator.ps1
.\scenario\run_scenario.ps1 -Preset ciagly -Background
```

Kolejnosc jest istotna: funkcje curated odwoluja sie do rejestrow powstajacych dopiero
w kroku `ingest`, wiec pierwszy przebieg kroku `kql` zawsze zwroci 400 dla czesci funkcji.
To nie jest blad.

Diagnostyka notatnikow: `.\deploy\debug_notebook.ps1 -Notebook <nazwa>` - Fabric Jobs API
zwraca tylko „System cancelled the Spark session", pelny traceback widac wylacznie tak.

## 9. Co zostalo

- [x] Fabric App `pulpit-koordynacji` - wdrozona, opis w `fabric-app/pulpit-koordynacji/README.md`
- [x] Model semantyczny i raport Power BI - wdrozone i zweryfikowane
- [x] Data Agent `agent_siatka_bezpieczenstwa` - `deploy/create_data_agent.py`; instrukcja
      systemowa skladana z `ai/DATA_AGENT.md`, wiec zmiana specyfikacji wymaga ponownego
      uruchomienia skryptu. Zrodla: Lakehouse (13 tabel), Eventhouse (10 tabel), model
      semantyczny (16 tabel). Publikacja agenta - w interfejsie, API tego nie udostepnia.
- [ ] Powiadomienia Activatora (e-mail / Teams) - do dokonczenia w UI
- [ ] Powiadomienie o eskalacji z aplikacji - regula na tabeli `EscalationRequest`
- [ ] Automatyczne odswiezanie `src/data/reference.json` (dzis recznie, `tools/export_reference.ps1`)

## 10. Fabric App - warunki uruchomienia

Dwa blokery pojawily sie przy pierwszym `rayfin up` i oba daja ten sam, mylacy komunikat
`404 The provided workspace was not found`:

1. **Rayfin CLI zalogowany w innym tenancie.** Workspace demo lezy w tenancie
   `7ada8cf4-c4be-488f-a844-6d37ee64849e` (CRM262738), a domyslne logowanie szlo na tenant
   Microsoft. Poprawka: `npx rayfin login -t 7ada8cf4-c4be-488f-a844-6d37ee64849e`.
2. **Wstrzymana pojemnosc.** `fcdemo` w stanie `Paused` sprawia, ze workspace jest niewidoczny
   dla API. Przed kazdym wdrozeniem uruchamiac `deploy\ensure_capacity.ps1`.

Region ma znaczenie: Fabric App (preview) nie jest dostepny m.in. w `Poland Central`,
`North Europe` i `UK South`. `West Europe`, gdzie stoi pojemnosc demo, jest wspierany.
