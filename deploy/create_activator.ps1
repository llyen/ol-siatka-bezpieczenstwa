<#
.SYNOPSIS
    Tworzy Activator scenariusza „Siatka bezpieczenstwa" i wdraza reguly alertowe jako funkcje KQL.

.DESCRIPTION
    Skrypt jest idempotentny:
      - wyszukuje albo tworzy element Reflex/Activator OL_SIA_Activator,
      - tworzy/aktualizuje funkcje KQL alert_* w Eventhouse wg activator\RULES.md,
      - weryfikuje liczbe trafien i wypisuje przykladowe rekordy.

    Wszystkie funkcje zwracaja ten sam zestaw kolumn kontraktowych
    (alert_rule, alert_severity, alert_ts, alert_key, current_value, threshold_value,
    spo, message), dzieki czemu Activator albo KQL alert moze je obsluzyc jednym
    szablonem powiadomienia, niezaleznie od reguly.

    Uwaga o czasie: scenariusz odtwarza sie w tempie 660x, wiec doba akcji trwa
    ok. 2,2 minuty zegara. Prog "6 godzin bez deklaracji" z RULES.md to zaledwie
    33 sekundy zegara - dlatego reguly czasowe patrza na okna minutowe, a nie
    godzinowe. Progi merytoryczne (4 zadania wiodace, sciezka krytyczna 1-4)
    pozostaja bez zmian, bo nie zaleza od tempa odtwarzania.

    Powiadomienia Activatora dokancza sie w UI - publiczne API Fabric nie wystawia
    jeszcze definicji regul powiadomien.

.EXAMPLE
    .\deploy\create_activator.ps1 -WorkspaceName OL-ZK-Demo-Siatka
#>
[CmdletBinding()]
param(
    [string]$WorkspaceName = 'OL-ZK-Demo-Siatka',
    [string]$ActivatorName = 'OL_SIA_Activator',
    [string]$WorkspaceId = '5965cbe7-b1f4-4c64-b397-5c78de66d1fc',
    [string]$ClusterUri = 'https://trd-j90bphmup0kwg093yy.z3.kusto.fabric.microsoft.com',
    [string]$KqlDatabaseName = 'OL_SIA_Eventhouse'
)

$ErrorActionPreference = 'Stop'
$FabricApi = 'https://api.fabric.microsoft.com/v1'

function Write-Step($msg) { Write-Host "`n=== $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Info($msg) { Write-Host "  $msg" -ForegroundColor Gray }
function Write-Warn($msg) { Write-Host "  [UWAGA] $msg" -ForegroundColor Yellow }

function Get-Token([string]$resource) {
    az account get-access-token --resource $resource --query accessToken -o tsv
}

function Get-FabricHeaders {
    @{ Authorization = "Bearer $(Get-Token 'https://api.fabric.microsoft.com')"; 'Content-Type' = 'application/json' }
}

function Get-KustoHeaders {
    @{ Authorization = "Bearer $(Get-Token 'https://kusto.kusto.windows.net')"; 'Content-Type' = 'application/json' }
}

function Resolve-Workspace {
    $ws = (Invoke-RestMethod -Uri "$FabricApi/workspaces" -Headers (Get-FabricHeaders)).value |
          Where-Object displayName -eq $WorkspaceName | Select-Object -First 1
    if ($ws) { return $ws.id }
    if ($WorkspaceId) {
        Write-Warn "Nie znaleziono workspace '$WorkspaceName' po nazwie; uzywam id $WorkspaceId."
        return $WorkspaceId
    }
    throw "Nie znaleziono workspace '$WorkspaceName'."
}

function Invoke-FabricWebRequest([string]$method, [string]$uri, $body = $null) {
    $json = if ($null -ne $body) { $body | ConvertTo-Json -Depth 100 } else { $null }
    $response = Invoke-WebRequest -Method $method -Uri $uri -Headers (Get-FabricHeaders) -Body $json -ContentType 'application/json' -SkipHttpErrorCheck
    if ($response.StatusCode -eq 202) {
        $operationUrl = $response.Headers.Location | Select-Object -First 1
        if ($operationUrl) {
            do {
                Start-Sleep -Seconds 5
                $operation = Invoke-RestMethod -Method Get -Uri $operationUrl -Headers (Get-FabricHeaders)
                Write-Info "operacja Fabric: $($operation.status)"
            } while ($operation.status -in 'NotStarted', 'Running')
            if ($operation.status -notin 'Succeeded', 'Completed') {
                throw "Operacja Fabric nie powiodla sie: $($operation | ConvertTo-Json -Depth 20)"
            }
        }
    }
    if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 300) {
        throw "Fabric REST $method $uri zwrocil $($response.StatusCode): $($response.Content)"
    }
    return $response
}

function Get-OrCreateActivator([string]$workspaceId) {
    $item = (Invoke-RestMethod -Uri "$FabricApi/workspaces/$workspaceId/items" -Headers (Get-FabricHeaders)).value |
            Where-Object { $_.displayName -eq $ActivatorName -and $_.type -eq 'Reflex' } |
            Select-Object -First 1
    if ($item) { Write-Ok "Activator juz istnieje: $($item.id)"; return $item }

    $response = Invoke-FabricWebRequest -method Post -uri "$FabricApi/workspaces/$workspaceId/reflexes" -body @{
        displayName = $ActivatorName
        description = 'Reguly alertowe scenariusza blackout i ludnosc wrazliwa wg activator\RULES.md'
    }
    $created = $response.Content | ConvertFrom-Json
    Write-Ok "utworzono Activator: $($created.id)"
    return $created
}

function Invoke-KustoMgmt([string]$command) {
    $body = @{ db = $KqlDatabaseName; csl = $command } | ConvertTo-Json -Depth 20
    Invoke-RestMethod -Method Post -Uri "$ClusterUri/v1/rest/mgmt" -Headers (Get-KustoHeaders) -Body $body | Out-Null
}

function Invoke-KustoQuery([string]$query) {
    $body = @{ db = $KqlDatabaseName; csl = $query } | ConvertTo-Json -Depth 20
    $response = Invoke-RestMethod -Method Post -Uri "$ClusterUri/v2/rest/query" -Headers (Get-KustoHeaders) -Body $body
    $response | Where-Object TableKind -eq 'PrimaryResult'
}

# Progi sa zgodne z activator\RULES.md. Kazda funkcja zwraca kolumny kontraktowe,
# zeby powiadomienie i lista alertow mialy jeden format niezaleznie od reguly.
$FunctionCommands = @'
.create-or-alter function with (folder='Activator/Siatka', docstring='Regula 1 RULES.md - zadanie z planu Z02/R nie jest gotowe mimo uplywu SLA procedury. SLA liczone jest w czasie SCENY, nie zegara: odstep miedzy aktywacja modulu a ostatnia deklaracja mnozymy przez tempo odtwarzania 660x. Dzieki temu prog 14 h z SpoChecklist znaczy to samo niezaleznie od tego, jak szybko odtwarzamy scenariusz.') alert_sla_exceeded() {
let tempo = 660.0;
let sla = SpoStepsForFlood()
    | summarize sla_hours = min(sla_hours) by admin_division = responsible_admin_division;
let aktywacja = TaskActivation
    | summarize aktywowano = min(timestamp) by task_module_id;
ActivationPlanZ02R()
| join kind=inner (CurrentReadiness() | project admin_division, task_module_id, status, comment, zadeklarowano = timestamp) on admin_division, task_module_id
| where status != 'gotowe'
| join kind=inner aktywacja on task_module_id
| join kind=leftouter sla on admin_division
| extend sla_hours = coalesce(todouble(sla_hours), 12.0)
| extend uplynelo_h = round(todouble(datetime_diff('second', zadeklarowano, aktywowano)) * tempo / 3600.0, 1)
| extend po_sla_h = round(uplynelo_h - sla_hours, 1)
| where po_sla_h > 0
| extend alert_rule='alert_sla_exceeded', alert_severity=iff(status == 'zablokowane' or po_sla_h > sla_hours, 'critical', 'warning'), alert_ts=zadeklarowano, alert_key=strcat(admin_division, '/', tostring(task_module_id)), current_value=po_sla_h, threshold_value=sla_hours, spo='SPO-12', message=strcat('PO SLA - modul ', task_module_name, ' w dziale ', admin_name, ' (', ministry, ') ma status "', status, '" po ', tostring(uplynelo_h), ' h od aktywacji, przy SLA ', tostring(sla_hours), ' h. Przekroczenie o ', tostring(po_sla_h), ' h. Rola: ', role, '.')
| project alert_rule, alert_severity, alert_ts, alert_key, current_value, threshold_value, spo, message, admin_division, admin_name, ministry, task_module_id, task_module_name, role, criticality, status, comment, uplynelo_h, sla_hours, po_sla_h
| order by current_value desc
| take 50
}
---NEXT---
.create-or-alter function with (folder='Activator/Siatka', docstring='Regula 2 RULES.md - modul zostal aktywowany, a dzial z siatki milczy. Regula patrzy na okno 2 minut zegara (ok. 22 h sceny), a nie na cala tabele: przy odtwarzaniu ciaglym tabela kumuluje kolejne cykle, wiec leftanti na calosci bylby zawsze pusty i regula nigdy by nie zadzialala.') alert_missing_readiness() {
let tempo = 660.0;
let okno = 2m;
// Zegar sceny, a nie now(). Odtwarzanie wysyla zdarzenia paczkami, wiec czolo
// strumienia potrafi wyprzedzic zegar hosta o kilkanascie minut. Przy now() okno
// lapalo wylacznie zdarzenia z przyszlosci, roznica czasu wychodzila ujemna
// i regula nigdy nie miala trafien.
let teraz = toscalar(TaskActivation | summarize max(timestamp));
let aktywacja = TaskActivation
    | where timestamp between (teraz - okno .. teraz)
    | summarize aktywowano = min(timestamp) by task_module_id;
let zlozone = ReadinessDeclaration
    | where timestamp between (teraz - okno .. teraz)
    | distinct admin_division, task_module_id;
ActivationPlanZ02R()
| join kind=inner aktywacja on task_module_id
| join kind=leftanti zlozone on admin_division, task_module_id
| extend milczenie_h = round(todouble(datetime_diff('second', teraz, aktywowano)) * tempo / 3600.0, 1)
| where milczenie_h >= 6
| extend alert_rule='alert_missing_readiness', alert_severity=iff(role == 'wiodący' or role == 'wiodacy', 'critical', 'warning'), alert_ts=teraz, alert_key=strcat(admin_division, '/', tostring(task_module_id)), current_value=milczenie_h, threshold_value=6.0, spo='SPO-12', message=strcat('BRAK DEKLARACJI - dzial ', admin_name, ' (', ministry, ') nie zlozyl deklaracji dla modulu ', task_module_name, ' mimo aktywacji ', tostring(milczenie_h), ' h temu. Rola w siatce: ', role, ', krytycznosc: ', criticality, '.')
| project alert_rule, alert_severity, alert_ts, alert_key, current_value, threshold_value, spo, message, admin_division, admin_name, ministry, task_module_id, task_module_name, role, criticality, aktywowano, milczenie_h
| order by alert_severity asc, current_value desc
| take 50
}
---NEXT---
.create-or-alter function with (folder='Activator/Siatka', docstring='Regula 3 RULES.md - blokada zgloszona na module sciezki krytycznej (1 rozpoznanie, 2 dystrybucja pomocy, 3 ewakuacja, 4 zabezpieczenie infrastruktury). Do komunikatu doklejam moduly zalezne z Interdependency, zeby decydent od razu widzial zasieg skutkow blokady.') alert_critical_path_blocker() {
let skutki = Interdependency
    | lookup kind=leftouter (dim_task_module | project depends_on_task_module_id = task_module_id, zalezny_od_nazwa = task_module_name) on depends_on_task_module_id
    | summarize blokuje = strcat_array(make_set(zalezny_od_nazwa), ', ') by task_module_id = depends_on_task_module_id;
CriticalPathBlockers()
| join kind=leftouter skutki on task_module_id
| extend blokuje = coalesce(blokuje, 'brak modulow zaleznych')
| extend alert_rule='alert_critical_path_blocker', alert_severity='critical', alert_ts=timestamp, alert_key=strcat(admin_division, '/', tostring(task_module_id)), current_value=todouble(task_module_id), threshold_value=4.0, spo='SPO-1;SPO-12', message=strcat('BLOKADA NA SCIEZCE KRYTYCZNEJ - ', admin_name, ' (', ministry, ') zglasza blokade modulu ', task_module_name, ': ', comment, '. Sily i srodki: ', forces_and_assets, '. Wstrzymuje: ', blokuje, '. Rozwazyc eskalacje do RZZK.')
| project alert_rule, alert_severity, alert_ts, alert_key, current_value, threshold_value, spo, message, admin_division, admin_name, ministry, task_module_id, task_module_name, comment, forces_and_assets, blokuje
| order by alert_ts desc
}
---NEXT---
.create-or-alter function with (folder='Activator/Siatka', docstring='Regula 4 RULES.md - dzial jest wiodacy w co najmniej 4 zadaniach planu Z02/R. Prog pochodzi z RULES.md; w danych demo spelniaja go dzialy VIII Gospodarka wodna i XIX Sprawy wewnetrzne, po 5 zadan wiodacych.') alert_division_overload() {
let gotowosc = CurrentReadiness()
    | summarize domkniete = countif(status == 'gotowe'), zablokowane = countif(status == 'zablokowane') by admin_division;
ActivationPlanZ02R()
| summarize zadania = count(), wiodace = countif(role == 'wiodący' or role == 'wiodacy'), moduly = strcat_array(make_set(task_module_name), ', ') by admin_division, admin_name, ministry
| where wiodace >= 4
| join kind=leftouter gotowosc on admin_division
| extend domkniete = coalesce(domkniete, 0), zablokowane = coalesce(zablokowane, 0)
| extend alert_rule='alert_division_overload', alert_severity=iff(zablokowane > 0, 'critical', 'warning'), alert_ts=now(), alert_key=admin_division, current_value=todouble(wiodace), threshold_value=4.0, spo='SPO-1', message=strcat('PRZECIAZENIE DZIALU WIODACEGO - ', admin_name, ' (', ministry, ') jest wiodacy w ', tostring(wiodace), ' z ', tostring(zadania), ' przypisanych zadan. Moduly: ', moduly, '. Domknietych deklaracji ', tostring(domkniete), ', zablokowanych ', tostring(zablokowane), '. Rozwazyc wsparcie lub redystrybucje zadan.')
| project alert_rule, alert_severity, alert_ts, alert_key, current_value, threshold_value, spo, message, admin_division, admin_name, ministry, zadania, wiodace, moduly, domkniete, zablokowane
| order by current_value desc
}
---NEXT---
.create-or-alter function with (folder='Activator/Siatka', docstring='Regula 5 RULES.md - sprzezenie powodzi z dezinformacja. Za uruchomiony uznajemy modul o statusie aktywny albo wygaszanie: wygaszanie oznacza, ze modul wciaz pracuje, tylko schodzi z obciazenia. Gdyby liczyc sam status aktywny, regula gasla po pierwszej fali wygaszen i przestawala pokazywac stan sceny.') alert_disinformation_coupling() {
let uruchomione = CurrentModuleActivation()
    | where activation_status in ('aktywny', 'wygaszanie');
let powodz = toscalar(uruchomione | summarize countif(hazard_code == 'Z02'));
let dezinfo = toscalar(uruchomione | summarize countif(hazard_code == 'Z20'));
let modul7 = toscalar(ActivationPlanZ02R() | summarize countif(task_module_id == 7));
uruchomione
| summarize zagrozenia = strcat_array(make_set(hazard_code), ', '), moduly = count(), ostatnia = max(timestamp)
| extend powodz_aktywna = powodz, dezinfo_aktywna = dezinfo, dzialy_modul7 = modul7
| where powodz_aktywna > 0
| extend sprzezenie = dezinfo_aktywna > 0
| extend alert_rule='alert_disinformation_coupling', alert_severity=iff(sprzezenie, 'critical', 'warning'), alert_ts=ostatnia, alert_key='Z02+Z20', current_value=todouble(dezinfo_aktywna), threshold_value=1.0, spo='SPO-3;SPO-16', message=iff(sprzezenie, strcat('SPRZEZENIE POWODZ + DEZINFORMACJA - uruchomione zagrozenia: ', zagrozenia, ', ', tostring(moduly), ' modulow. Wymagane wzmocnienie modulu 7 Ochrona informacji; w siatce przypisano do niego ', tostring(dzialy_modul7), ' dzialow. Uruchomic komunikacje publiczna i monitoring narracji.'), strcat('POWODZ BEZ SPRZEZENIA INFORMACYJNEGO - uruchomione zagrozenia: ', zagrozenia, ', ', tostring(moduly), ' modulow. Modul 7 w gotowosci prewencyjnej, ', tostring(dzialy_modul7), ' dzialow w siatce. Monitorowac przestrzen informacyjna pod katem narracji o powodzi.'))
| project alert_rule, alert_severity, alert_ts, alert_key, current_value, threshold_value, spo, message, zagrozenia, moduly, powodz_aktywna, dezinfo_aktywna, dzialy_modul7
}
---NEXT---
.create-or-alter function with (folder='Activator/Siatka', docstring='Regula 6 RULES.md - zdarzenie spelnia warunki kandydackie do eskalacji na poziom RZZK: co najmniej jedna blokada, albo przeciazony dzial wiodacy, albo 5 i wiecej zadan po SLA. Zwraca jeden wiersz podsumowania, bo to material na decyzje, nie na liste zadan.') alert_rzzk_escalation() {
let blokady = toscalar(CriticalPathBlockers() | summarize count());
let po_sla = toscalar(alert_sla_exceeded() | summarize count());
let przeciazone = toscalar(alert_division_overload() | summarize count());
let brak_dekl = toscalar(alert_missing_readiness() | summarize count());
let luka = toscalar(ReadinessGap() | summarize count());
print blokady = blokady, po_sla = po_sla, przeciazone = przeciazone, brak_dekl = brak_dekl, luka = luka
| extend przeslanki = tolong(blokady >= 1) + tolong(przeciazone >= 1) + tolong(po_sla >= 5)
| where przeslanki >= 1
| extend alert_rule='alert_rzzk_escalation', alert_severity=iff(przeslanki >= 2, 'critical', 'warning'), alert_ts=now(), alert_key='RZZK', current_value=todouble(przeslanki), threshold_value=1.0, spo='SPO-1', message=strcat('KANDYDAT DO ESKALACJI RZZK - spelnione ', tostring(przeslanki), ' z 3 przeslanek: blokady na sciezce krytycznej ', tostring(blokady), ', przeciazone dzialy wiodace ', tostring(przeciazone), ', zadania po SLA ', tostring(po_sla), '. Luka gotowosci ogolem ', tostring(luka), ' zadan, bez deklaracji ', tostring(brak_dekl), '. Rekomendowana procedura SPO-1: zwolac posiedzenie, wygenerowac liste uczestnikow i pakiet decyzyjny.')
| project alert_rule, alert_severity, alert_ts, alert_key, current_value, threshold_value, spo, message, blokady, po_sla, przeciazone, brak_dekl, luka
}
'@ -split '---NEXT---'

Write-Step "Workspace: $WorkspaceName"
$ResolvedWorkspaceId = Resolve-Workspace
Write-Ok "workspace id = $ResolvedWorkspaceId"

Write-Step 'Activator'
$Activator = Get-OrCreateActivator -workspaceId $ResolvedWorkspaceId
Write-Info "element Reflex: $($Activator.id)"

Write-Step 'Funkcje KQL alertow'
foreach ($command in $FunctionCommands) {
    Invoke-KustoMgmt $command.Trim()
}
Write-Ok "utworzono/zaktualizowano $($FunctionCommands.Count) funkcji"

Write-Step 'Weryfikacja trafien'
$functions = @(
    'alert_sla_exceeded',
    'alert_missing_readiness',
    'alert_critical_path_blocker',
    'alert_division_overload',
    'alert_disinformation_coupling',
    'alert_rzzk_escalation'
)
foreach ($functionName in $functions) {
    $metrics = Invoke-KustoQuery "$functionName() | summarize trafienia=count(), klucze=dcount(alert_key), krytyczne=countif(alert_severity == 'critical')"
    $sample = Invoke-KustoQuery "$functionName() | top 1 by current_value desc | project message"
    Write-Host "`n$functionName" -ForegroundColor Yellow
    Write-Host "  liczby : $($metrics.Rows[0] | ConvertTo-Json -Compress)"
    Write-Host "  przyklad: $($sample.Rows[0] | ConvertTo-Json -Compress)"
}

Write-Ok 'Gotowe. Reguly KQL dzialaja; powiadomienia Activator dokoncz w UI wg activator\RULES.md.'
