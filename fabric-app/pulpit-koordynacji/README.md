# Fabric App — Siatka Bezpieczeństwa: Pulpit Koordynacji

Aplikacja Microsoft Fabric App (Rayfin) dla scenariusza „Siatka bezpieczeństwa i plan aktywacji zadań”.
Pokazuje, jak siatka bezpieczeństwa KPZK przestaje być statycznym załącznikiem, a staje się
operacyjnym planem zadań z deklaracjami gotowości, wykrywaniem blokad i eskalacją do RZZK.

## Stan wdrożenia

| Element | Wartość |
| --- | --- |
| Workspace | `OL-ZK-Demo-Siatka` (`5965cbe7-b1f4-4c64-b397-5c78de66d1fc`) |
| Tenant | `7ada8cf4-c4be-488f-a844-6d37ee64849e` (CRM262738) |
| AppBackend (Rayfin item) | `2b1ed178-f1f6-4be4-a784-664e941c0e2d` |
| SQL Database | `pulpit-koordynacji` (`2fd3363a-6ff5-496b-bbda-036bfc87e54a`) |
| Adres aplikacji | https://keen-ore-908e20772e-westeurope.webapp.fabricapps.net |
| Portal | https://app.fabric.microsoft.com/groups/5965cbe7-b1f4-4c64-b397-5c78de66d1fc/appbackends/2b1ed178-f1f6-4be4-a784-664e941c0e2d |

Logowanie działa przez Fabric SSO, więc aplikację otwiera się **z poziomu portalu Fabric**.
Adres bezpośredni wyświetli ekran logowania, ale bez kontekstu portalu sesja się nie nawiąże.

## Architektura danych

Rayfin ma własną bazę SQL w Fabric i nie czyta Lakehouse ani Eventhouse. Podział jest więc taki:

- **Odczyt referencyjny** — `src/data/reference.json`, migawka Eventhouse generowana skryptem
  `tools/export_reference.ps1` (20 zagrożeń, 25 działów, 7 modułów, 16 procedur SPO, 25 kontaktów,
  64 kroki checklist, 1000 wierszy siatki oraz stan aktywacji i deklaracji). Vite wkompilowuje ją
  w paczkę, więc aplikacja startuje bez zapytań sieciowych.
- **Zapis zwrotny** — encje Rayfin `ReadinessWriteback` i `EscalationRequest`, dostępne przez
  GraphQL z autoryzacją Fabric SSO.

Plan aktywacji liczony jest po stronie klienta (`src/data/model.ts`) **tymi samymi regułami**
co funkcja `ActivationPlanZ02R()` w `kql/02_update_policies.kql`: odrzucamy działy o roli
wspierającej oraz wiersze bez modułu zadaniowego. Dla Z02/faza R daje to 44 zadania — zgodnie
z dashboardem i Activatorem. Regresję pilnuje test `src/__tests__/model.test.ts`.

Stan zadania powstaje z nałożenia trzech warstw: plan → migawka deklaracji z Eventhouse →
deklaracje zapisane w aplikacji. Wpis z aplikacji zawsze wygrywa, bo powstał później.

## Ekrany

1. **Zagrożenie** — 20 kafelków KPZK w kolorach macierzy ryzyka, z liczbą zadań, jakie wygeneruje
   plan dla wybranej fazy. Parametry zdarzenia (`event_id`, faza, skala) obowiązują globalnie.
2. **Lista zadań** — plan aktywacji z sześcioma filtrami, wyszukiwarką, eksportem CSV i czterema
   wskaźnikami. Kolumna „kolejność” to głębokość modułu w grafie współzależności.
3. **Karta działu** — zadania działu, kontakty, instytucje podległe, formularz deklaracji
   (`Potwierdź gotowość` / `Zapisz w toku` / `Zgłoś blokadę`) i historia wpisów.
4. **Pulpit RCB** — wskaźniki gotowości, blokady posortowane wg wpływu, obciążenie działów
   wiodących, zadania po SLA i wniosek o eskalację do RZZK zapisujący migawkę wskaźników.
5. **Kontakty i SPO-1** — checklista procedury z SLA, lista uczestników posiedzenia wyliczana
   z aktywnego planu, eksport CSV i gotowa treść wiadomości Teams.

## Uprawnienia

Obie encje: odczyt i zapis dla każdego zalogowanego (koordynator RCB i RZZK muszą widzieć całość),
natomiast modyfikacja i usunięcie tylko własnego wpisu — polityka `@claims.sub eq @item.source_user`
(odpowiednio `requested_by`). Dyżurny nie skasuje deklaracji innego resortu.

## Walidacje formularza

- blokada wymaga opisu przyczyny — bez tego koordynator nie wie, co odblokować,
- gotowość wymaga wskazania sił i środków,
- moduł zadaniowy musi mieć numer 1–7,
- limity długości: komentarz 500 znaków, siły i środki 300.

## Praca z projektem

```powershell
# odświeżenie danych referencyjnych z Eventhouse (wymaga az login)
.\tools\export_reference.ps1

npm install
npm run test          # 14 testów, w tym regresja 44 zadań
npm run lint
npm run build

npx rayfin login -t 7ada8cf4-c4be-488f-a844-6d37ee64849e
npx rayfin up -y          # build + wdrożenie statyczne
npx rayfin up db apply    # migracja schematu (--force przy zmianach destrukcyjnych)
npx rayfin up status
```

## Napotkane problemy i rozstrzygnięcia

| Problem | Przyczyna | Rozwiązanie |
| --- | --- | --- |
| `rayfin up` → 404 „The provided workspace was not found” | CLI był zalogowany w tenancie Microsoft, a workspace leży w tenancie demo CRM262738 | `npx rayfin login -t 7ada8cf4-…`; dodatkowo `rayfin up switch --workspace-id` zapisuje workspace do `rayfin/.env` |
| To samo 404 przy wstrzymanej pojemności | Pojemność `fcdemo` była w stanie `Paused` | `deploy\ensure_capacity.ps1` przed wdrożeniem |
| `check` nie istnieje w `RoleDeclarationOptions` | Dokumentacja wyprzedza pakiet 1.33.2 | w zainstalowanej wersji opcja nazywa się `policy` |
| `db apply` → „Drop table 'Todos' would result in data loss” | Pozostałość po szablonie `todoapp` | `npx rayfin up db apply --force` (tabela była pusta) |
| `CurrentModuleActivation()` odrzucał kolumnę `trigger` | Funkcja zwraca `trigger_reason` | poprawiony projekt kolumn w skrypcie eksportu |

## Do dokończenia

- Powiadomienia: eskalacja zapisuje wniosek, ale nie wysyła wiadomości — wymaga reguły Activatora
  albo Power Automate na tabeli `EscalationRequest`.
- Odświeżanie migawki referencyjnej jest ręczne. Docelowo skrypt eksportu powinien działać
  jako zadanie w pipeline, żeby aplikacja nadążała za odtwarzaniem scenariusza.

