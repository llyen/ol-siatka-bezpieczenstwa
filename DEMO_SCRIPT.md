# Scenariusz demo 15–20 minut

## Cel pokazu

Pokaz ma przekonać decydenta, że siatka bezpieczeństwa może działać jak aplikacja operacyjna, a nie jak statyczna tabela. Prezentujemy scenariusz `POWODZ_WRZESIEN_2026`, zagrożenie `Z02 Powódź`, faza `R`, skala `4`. Wszystkie liczby pochodzą z uruchomionych skryptów: plan ma **44 zadań**, obejmuje moduły `[1, 2, 4, 5, 7]`, analiza luk wykrywa **28 zadań bez gotowości**, **28 po SLA**, **9 blokad**, a działy `VIII` i `XIX` mają po **5** zadań wiodących.

## Obsada ról

- **Narrator/prezenter** — prowadzi demo, przełącza ekrany, pilnuje czasu i tłumaczy wartość biznesową.
- **Minister** — zadaje pytania decyzyjne: kto odpowiada, co jest zablokowane, czy trzeba zwołać RZZK.
- **Dyrektor RCB** — interpretuje wynik aplikacji, podejmuje decyzję o eskalacji i uruchomieniu SPO-1.
- **Przedstawiciel działu administracji** — symuluje dyżurnego ministerstwa, potwierdza gotowość albo zgłasza blokadę.
- **Obserwator techniczny** — opcjonalnie pokazuje Lakehouse, notebook i pliki `datasets\derived\` jako dowód, że dane są policzone.

## Checklista przed demo

1. Uruchom `python generate_datasets.py` i sprawdź `datasets\derived\dataset_counts.json`.
2. Uruchom `python notebooks\02_activation_engine.py Z02 R 4`.
3. Uruchom `python notebooks\03_gap_analysis.py` i otwórz `gap_analysis_summary.json`.
4. Uruchom `python notebooks\04_graph_view.py` i miej pod ręką `responsibility_graph.json`.
5. W Fabric odśwież Lakehouse `OL_Siatka_Lakehouse`.
6. Odśwież semantic model i raport Power BI.
7. Otwórz Fabric App na ekranie 1 z domyślnym `Z02 Powódź`.
8. Otwórz ekran koordynatora RCB z KPI.
9. Przygotuj zakładkę Data Agent z pytaniami testowymi.
10. Przygotuj plan B: lokalny folder `datasets\derived\`, README i screenshoty zastępcze.

## Akt I — Zdarzenie i pytanie „kto za co odpowiada” (0:00–4:00)

**Kwestia narratora:** „Zaczynamy od sytuacji, którą każdy zespół kryzysowy zna: mamy powódź, wiele resortów, presję czasu i pytanie ministra. Siatka bezpieczeństwa istnieje, ale w praktyce jest tabelą. Dzisiaj pokażemy, jak ta tabela staje się aplikacją, która odpowiada w sekundach.”

**Kwestia ministra:** „Nie chcę teraz przeglądać PDF-a. Proszę mi powiedzieć, kto odpowiada za powódź, które zadania są krytyczne i czy któryś resort już sygnalizuje problem.”

**Co kliknąć:** w aplikacji otwórz **Ekran 1 — Wybór zagrożenia**. Kliknij kafelek `Z02 Powódź`, wybierz fazę `R`, skalę `4`, event `POWODZ_WRZESIEN_2026`. Pokaż, że kafelek ma kolor ryzyka zgodny z `dim_hazard[color]`.

**Co widz zobaczy:** 20 kafelków zagrożeń KPZK, filtrowanie kategorii i wybór fazy. Po wskazaniu powodzi aplikacja pokazuje, że to zdarzenie naturalne o wysokim wyniku ryzyka. Prezenter podkreśla, że lista 20 zagrożeń jest kanoniczna, a nie „wymyślona dla dashboardu”.

**Liczby do wypowiedzenia:** „W słowniku mamy 20 zagrożeń, 25 działów administracji, 7 modułów i kompletną macierz 1000 komórek.”

## Akt II — Wygenerowanie planu zadań (4:00–7:30)

**Kwestia narratora:** „Teraz nie szukamy ręcznie komórek w Excelu. Aplikacja bierze zagrożenie, fazę i skalę zdarzenia, przechodzi przez siatkę bezpieczeństwa, rozbija listę modułów i układa je według zależności. To jest moment, w którym statyczna siatka staje się planem operacyjnym.”

**Co kliknąć:** kliknij `Generate activation plan`, przejdź do **Ekranu 2 — Lista zadań**. Włącz filtr `tylko wiodący`, potem wyłącz go i pokaż `współpracujący`. Posortuj po `dependency_order`.

**Co widz zobaczy:** tabelę z działem, ministrem, modułem, rolą, krytycznością i SLA. Zadania są uporządkowane według zależności: moduł 1 przed modułem 2 i 4. Widać, że w powodzi nie ma jednego właściciela: gospodarka wodna, sprawy wewnętrzne, energia, zdrowie, transport, łączność i obrona narodowa są widoczne w jednym planie.

**Liczby do wypowiedzenia:** „Dla `Z02/R/4` powstały **44 zadania**. Aktywne moduły to `[1, 2, 4, 5, 7]`. Kolejność zależności to `{'1': 1, '2': 2, '4': 3, '5': 4, '7': 5}` — najpierw monitoring, potem zabezpieczenie ludności i łączność, a następnie wsparcie i ochrona informacji.”

**Kwestia dyrektora RCB:** „To jest dokładnie ten widok, którego brakuje w statycznym dokumencie. Nie tylko widzę, kto jest wiodący, ale również co powinno wydarzyć się najpierw i gdzie termin jest najkrótszy.”

## Akt III — Deklaracje gotowości działów (7:30–10:30)

**Kwestia przedstawiciela działu:** „Jako dyżurny działu widzę tylko swoje zadania. Nie edytuję całej siatki bezpieczeństwa, tylko składam deklarację do przypisanego modułu. Jeśli jestem gotowy, podaję siły i środki; jeśli nie, zgłaszam blokadę z komentarzem.”

**Co kliknąć:** przejdź do **Ekranu 3 — Karta działu administracji**. Wybierz dział `XIX Sprawy wewnętrzne`, kliknij `Potwierdź gotowość` dla modułu 2, wpisz „PSP i Policja w gotowości, dyżury 24/7”. Następnie wybierz `XIII Łączność`, kliknij `Zgłoś blokadę` dla modułu 4 i pokaż walidację komentarza.

**Co widz zobaczy:** formularz write-back ze statusem, komentarzem i siłami/środkami. Status zapisuje się w strukturze `fact_readiness_declaration`: timestamp, event, dział, moduł, status, komentarz, forces_and_assets. Widz rozumie, że aplikacja nie jest tylko raportem — ona zbiera potwierdzenia.

**Liczby do wypowiedzenia:** „W danych testowych mamy **106 deklaracji gotowości**. Statusy obejmują `nie rozpoczęto`, `w toku`, `gotowe` i `zablokowane`.”

## Akt IV — Wykrycie blokady na ścieżce krytycznej (10:30–14:00)

**Kwestia narratora:** „Teraz pokazujemy najważniejszą różnicę między tabelą a systemem operacyjnym. Tabela przechowuje odpowiedzialność. System wykrywa, że odpowiedzialność nie została dowieziona w czasie albo że blokada leży na ścieżce krytycznej.”

**Co kliknąć:** przejdź do **Ekranu 4 — Pulpit koordynatora RCB**. Ustaw filtr `zablokowane`, następnie `po SLA`. Pokaż KPI: gotowość, blokady, po SLA, przeciążone działy. Otwórz drill-through do `gap_analysis_overdue.csv`.

**Co widz zobaczy:** lista blokad, w tym blokady związane z energią, łącznością i transportem. Widzi też przeciążenia: `VIII Gospodarka wodna` i `XIX Sprawy wewnętrzne` są wiodące po 5 razy. Pulpit pokazuje, że problem nie jest lokalnym brakiem wpisu, tylko ryzykiem koordynacyjnym.

**Liczby do wypowiedzenia:** „Analiza z godziny `2026-09-17T12:00:00+02:00` wykrywa **28 zadań bez gotowości**, **28 po SLA**, **9 blokad**. Graf odpowiedzialności ma **12 węzłów** i **20 krawędzi**, a algorytm wskazuje **9 potencjalnych pojedynczych punktów awarii organizacyjnej**.”

**Kwestia ministra:** „To już nie jest lista telefonów. To jest informacja decyzyjna: które blokady realnie opóźnią działania i gdzie potrzebna jest decyzja wyższego szczebla.”

## Akt V — Eskalacja do RZZK i SPO-1 (14:00–18:00)

**Kwestia dyrektora RCB:** „Mamy kilka resortów, blokady na krytycznych modułach i przeciążone działy wiodące. Zgodnie z logiką zarządzania kryzysowego przygotowujemy eskalację do RZZK i uruchamiamy SPO-1.”

**Co kliknąć:** na **Ekranie 4** kliknij `Eskaluj do RZZK`. Przejdź do **Ekranu 5 — Kontakty i SPO-1**. Wybierz `SPO-1`, kliknij `Generate participant list`. Pokaż kontakty dyżurne i kroki checklisty.

**Co widz zobaczy:** lista uczestników posiedzenia RZZK z działów wiodących i współpracujących, książka kontaktów dyżurnych oraz checklistę SPO-1. W danych jest **25 kontaktów dyżurnych** i **64 kroków checklist SPO** dla **16 procedur**.

**Kwestia narratora:** „To jest zamknięcie pętli: od pytania ministra, przez plan zadań i deklaracje działów, do formalnej eskalacji i checklisty SPO. Każdy krok zostawia ślad w danych.”

## Wow moments

1. **PDF zamieniony w plan w 10 sekund.** Decydent widzi, że nie przepisujemy tabeli do ładnego dashboardu, tylko generujemy listę zadań, właścicieli i SLA. To działa, bo odpowiada na pytanie operacyjne, nie na pytanie analityczne.
2. **Write-back z resortu.** Przedstawiciel działu nie wysyła maila ani arkusza; klika status i wpisuje siły/środki. To działa, bo pokazuje mierzalność gotowości i eliminuje chaos meldunkowy.
3. **Ścieżka krytyczna i blokady.** System wskazuje, że blokada łączności lub transportu wpływa na odbudowę i koordynację. To działa, bo decydent rozumie zależności, a nie tylko liczbę czerwonych pól.
4. **SPO-1 jako akcja, nie dokument.** Lista uczestników RZZK powstaje z aktywnego planu. To działa, bo łączy formalną procedurę z rzeczywistym zdarzeniem.
5. **Data Agent dla pytań ad hoc.** Minister może zapytać językiem naturalnym. To działa, bo redukuje zależność od analityka w czasie posiedzenia.

## Wartość biznesowa

- **Czas:** odpowiedź na pytanie „kto za co odpowiada” spada z godzin uzgodnień do sekund generowania planu.
- **Ryzyko:** system pokazuje brak gotowości, SLA i blokady zanim staną się tematem dopiero na odprawie.
- **Koszt:** mniej ręcznego scalania arkuszy i meldunków; jeden Lakehouse zasila raport, aplikację i agenta.
- **Zgodność z ustawą o ZK:** demo wspiera logikę poziomów reagowania i eskalacji do RZZK, szczególnie gdy zaangażowanych jest kilku ministrów.
- **Rozliczalność:** każdy status ma czas, dział, moduł i komentarz; łatwiej odtworzyć przebieg decyzji.

## Plan B

Jeżeli **Fabric App nie działa**, pokaż `datasets\derived\activation_plan_Z02_R.csv` w Excelu lub Power BI Desktop i przejdź przez te same filtry. Jeżeli **brak sieci**, użyj lokalnych plików `README.md`, `DEMO_SCRIPT.md`, `gap_analysis_summary.json` i `responsibility_graph.json`. Jeżeli **dane się nie odświeżają**, uruchom lokalnie `python generate_datasets.py`, `python notebooks\02_activation_engine.py Z02 R 4`, `python notebooks\03_gap_analysis.py` i pokaż timestamp analizy. Jeżeli **Data Agent nie odpowiada**, użyj zapytań z `kql\data_agent_queries.kql` jako demonstracji tych samych odpowiedzi. Jeżeli **raport Power BI nie ładuje się**, pokaż screenshoty zastępcze lub `report\REPORT_SPEC.md`, podkreślając, które wizualizacje są zasilane którymi tabelami.

## Najczęstsze pytania decydenta i odpowiedzi

1. **Skąd są dane?** Z generatora syntetycznego opartego o kanoniczne listy KPZK i konwencje programu. W produkcji źródłem byłyby zatwierdzone rejestry i systemy resortowe.
2. **Czy to są prawdziwe numery telefonów?** Nie. `dim_contact_point` zawiera dane fikcyjne oznaczone jako syntetyczne.
3. **Czy system zastępuje decyzję RZZK?** Nie. System przygotowuje informację, listę uczestników i rekomendację, ale decyzja pozostaje po stronie uprawnionych organów.
4. **Jak chronione byłyby dane?** Produkcyjnie przez Entra ID, role per dział, audyt, etykiety wrażliwości, Private Link i polityki retencji.
5. **Czy można zintegrować istniejące systemy?** Tak. Lakehouse może przyjmować dane z pipeline, API, plików, skrótów OneLake i systemów obiegu dokumentów.
6. **Ile trwa wdrożenie MVP?** Demo pokazuje zakres MVP: słowniki, plan aktywacji, statusy i raport. Realny pilotaż zależy od integracji, ale można go etapować od jednego zagrożenia.
7. **Jaki jest koszt?** Koszt zależy od Fabric capacity, wolumenów i liczby użytkowników. Wartość polega na współdzieleniu jednej platformy dla danych, raportu, aplikacji i automatyzacji.
8. **Co jeśli ministerstwo nie potwierdzi gotowości?** Reguła Activator wykrywa brak deklaracji po progu czasu i wysyła przypomnienie oraz alert do RCB.
9. **Czy model uwzględnia fazę odbudowy?** Tak. `fact_safety_grid` ma fazy `R` i `O`; odbudowa wzmacnia role infrastruktury, transportu i budownictwa.
10. **Czy można dodać województwa i drill-down?** Tak. Obecne demo jest krajowe, ale model można rozszerzyć o wymiary terytorialne i statusy wojewódzkie.
