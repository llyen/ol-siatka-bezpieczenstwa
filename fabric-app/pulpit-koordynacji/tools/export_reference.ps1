# Eksport danych referencyjnych z Eventhouse do statycznego JSON aplikacji.
#
# Rayfin ma wlasna baze SQL i nie czyta Lakehouse ani Eventhouse bezposrednio.
# Dane slownikowe scenariusza sa male (okolo 1150 wierszy) i nie zmieniaja sie w trakcie
# demonstracji, wiec zamiast budowac warstwe posrednia eksportujemy je raz do pliku,
# ktory Vite wkompilowuje w paczke. Przez Rayfin/GraphQL idzie wylacznie zapis zwrotny:
# deklaracje gotowosci i eskalacje.
#
# Migawka stanu operacyjnego (aktywacje modulow i ostatnie deklaracje) tez trafia do pliku
# jako punkt wyjscia. Aplikacja naklada na nia deklaracje zapisane przez uzytkownika, wiec
# demonstracja dziala takze wtedy, gdy odtwarzanie scenariusza jest zatrzymane.
[CmdletBinding()]
param(
    [string]$ClusterUri = 'https://trd-j90bphmup0kwg093yy.z3.kusto.fabric.microsoft.com',
    [string]$Database = 'OL_SIA_Eventhouse',
    [string]$OutFile = (Join-Path $PSScriptRoot '..\src\data\reference.json')
)

$ErrorActionPreference = 'Stop'

$token = az account get-access-token --resource 'https://kusto.kusto.windows.net' --query accessToken -o tsv
if (-not $token) { throw 'Brak tokenu Kusto. Zaloguj sie przez az login.' }
$headers = @{ Authorization = "Bearer $token"; 'Content-Type' = 'application/json' }

function Invoke-KustoQuery([string]$query) {
    $body = @{ db = $Database; csl = $query } | ConvertTo-Json -Depth 20
    $response = Invoke-RestMethod -Method Post -Uri "$ClusterUri/v1/rest/query" -Headers $headers -Body $body
    $table = $response.Tables[0]
    $columns = $table.Columns | ForEach-Object { $_.ColumnName }
    $rows = @()
    foreach ($row in $table.Rows) {
        $item = [ordered]@{}
        for ($i = 0; $i -lt $columns.Count; $i++) { $item[$columns[$i]] = $row[$i] }
        $rows += [pscustomobject]$item
    }
    , $rows
}

# Kolejnosc zapytan odpowiada kolejnosci ekranow aplikacji.
$queries = [ordered]@{
    hazards         = 'dim_hazard | order by risk_score desc, hazard_code asc'
    divisions       = 'dim_admin_division | order by admin_division asc'
    modules         = 'dim_task_module | order by task_module_id asc'
    spo             = 'dim_spo | order by spo_code asc'
    contacts        = 'dim_contact_point | order by admin_division asc'
    checklist       = 'SpoChecklist | order by spo_code asc, step_number asc'
    interdependency = 'Interdependency | order by task_module_id asc'
    # Siatka trafia do aplikacji w postaci surowej, zeby plan dalo sie wygenerowac
    # dla dowolnego zagrozenia i fazy po stronie klienta, tymi samymi regulami
    # co ActivationPlanZ02R w KQL.
    grid            = 'SafetyGrid | order by hazard_code asc, admin_division asc, phase asc'
    activation      = 'CurrentModuleActivation() | project task_module_id, activation_status, leading_admin_division, trigger_reason, day_offset, timestamp'
    readiness       = 'CurrentReadiness() | project admin_division, task_module_id, status, comment, forces_and_assets, timestamp'
}

$payload = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString('o')
    source      = "$ClusterUri/$Database"
}

foreach ($key in $queries.Keys) {
    Write-Host "  pobieram $key..." -ForegroundColor Gray
    $rows = Invoke-KustoQuery $queries[$key]
    $payload[$key] = $rows
    Write-Host "  [OK] $key : $($rows.Count) wierszy" -ForegroundColor Green
}

$dir = Split-Path -Parent $OutFile
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
$payload | ConvertTo-Json -Depth 20 | Set-Content -Path $OutFile -Encoding UTF8

$resolved = (Resolve-Path $OutFile).Path
Write-Host "`nZapisano $resolved ($([math]::Round((Get-Item $resolved).Length / 1KB, 1)) KB)" -ForegroundColor Cyan
