<#
.SYNOPSIS
    Wdrozenie demo "Siatka bezpieczenstwa - pulpit koordynacji" do Microsoft Fabric.

.DESCRIPTION
    Tworzy i konfiguruje elementy Fabric potrzebne do uruchomienia demo:
      - Lakehouse (wymiary, rejestry i wyniki analiz)
      - Eventhouse / baza KQL (strumienie telemetrii)
      - tabele, mapowania JSON i funkcje pomocnicze w bazie KQL
      - wgranie plikow danych do OneLake
      - zaladowanie strumieni JSONL i wymiarow do Eventhouse

    Uwierzytelnienie: Azure CLI (`az login`). Skrypt pobiera tokeny dla
    api.fabric.microsoft.com (Fabric REST), storage.azure.com (OneLake)
    oraz kusto.kusto.windows.net (Eventhouse).

.PARAMETER Step
    Ktory etap wykonac: all | items | kql | upload | ingest | verify

.EXAMPLE
    .\deploy\deploy_fabric.ps1 -WorkspaceName OL-ZK-Demo-Siatka -CapacityName fcdemo
#>
[CmdletBinding()]
param(
    [string]$WorkspaceName = 'OL-ZK-Demo-Siatka',
    [string]$CapacityName  = '',
    [ValidateSet('all', 'items', 'kql', 'upload', 'ingest', 'verify')]
    [string]$Step = 'all'
)

$ErrorActionPreference = 'Stop'
$RepoRoot       = Split-Path -Parent $PSScriptRoot
$LakehouseName  = 'OL_SIA_Lakehouse'
$EventhouseName = 'OL_SIA_Eventhouse'
$FabricApi      = 'https://api.fabric.microsoft.com/v1'

function Write-Step($msg) { Write-Host "`n=== $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Info($msg) { Write-Host "  $msg" -ForegroundColor Gray }
function Write-Warn($msg) { Write-Host "  [UWAGA] $msg" -ForegroundColor Yellow }

function Get-Token($resource) {
    az account get-access-token --resource $resource --query accessToken -o tsv
}

function Get-FabricHeaders {
    @{ Authorization = "Bearer $(Get-Token 'https://api.fabric.microsoft.com')"; 'Content-Type' = 'application/json' }
}

function Resolve-Workspace {
    $h = Get-FabricHeaders
    $ws = (Invoke-RestMethod -Uri "$FabricApi/workspaces" -Headers $h).value |
          Where-Object displayName -eq $WorkspaceName | Select-Object -First 1
    if ($ws) { return $ws }

    if (-not $CapacityName) { throw "Workspace '$WorkspaceName' nie istnieje. Podaj -CapacityName, aby go utworzyc." }
    $cap = (Invoke-RestMethod -Uri "$FabricApi/capacities" -Headers $h).value |
           Where-Object displayName -eq $CapacityName | Select-Object -First 1
    if (-not $cap) { throw "Nie znaleziono pojemnosci '$CapacityName'." }

    $body = @{ displayName = $WorkspaceName; capacityId = $cap.id } | ConvertTo-Json
    Invoke-RestMethod -Uri "$FabricApi/workspaces" -Headers $h -Method Post -Body $body
}

function New-FabricItem($workspaceId, $type, $name) {
    $h = Get-FabricHeaders
    $existing = (Invoke-RestMethod -Uri "$FabricApi/workspaces/$workspaceId/items" -Headers $h).value |
                Where-Object { $_.displayName -eq $name -and $_.type -eq $type } | Select-Object -First 1
    if ($existing) { Write-Info "$type '$name' juz istnieje"; return $existing }

    $body = @{ displayName = $name; type = $type } | ConvertTo-Json
    $r = Invoke-WebRequest -Uri "$FabricApi/workspaces/$workspaceId/items" -Headers $h -Method Post -Body $body
    if ($r.StatusCode -eq 202) {
        $op = $r.Headers.Location | Select-Object -First 1
        do {
            Start-Sleep 5
            $st = Invoke-RestMethod -Uri $op -Headers (Get-FabricHeaders)
        } while ($st.status -in 'Running', 'NotStarted')
    }
    $created = (Invoke-RestMethod -Uri "$FabricApi/workspaces/$workspaceId/items" -Headers (Get-FabricHeaders)).value |
               Where-Object { $_.displayName -eq $name -and $_.type -eq $type } | Select-Object -First 1
    Write-Ok "utworzono $type '$name'"
    return $created
}

function Invoke-KustoMgmt($clusterUri, $database, $command) {
    $h = @{ Authorization = "Bearer $(Get-Token 'https://kusto.kusto.windows.net')"; 'Content-Type' = 'application/json' }
    $body = @{ db = $database; csl = $command } | ConvertTo-Json -Depth 3
    Invoke-RestMethod -Uri "$clusterUri/v1/rest/mgmt" -Headers $h -Method Post -Body $body
}

function Invoke-KustoQuery($clusterUri, $database, $query) {
    $h = @{ Authorization = "Bearer $(Get-Token 'https://kusto.kusto.windows.net')"; 'Content-Type' = 'application/json' }
    $body = @{ db = $database; csl = $query } | ConvertTo-Json -Depth 3
    Invoke-RestMethod -Uri "$clusterUri/v1/rest/query" -Headers $h -Method Post -Body $body
}

# Dzieli plik .kql na pojedyncze komendy sterujace (kazda zaczyna sie od kropki).
# Komendy .create-or-alter function maja ciało w nawiasach klamrowych, wiec licznik
# nawiasow decyduje o tym, czy kolejna kropka jest nowa komenda, czy trescia funkcji.
function Split-KqlCommands($path) {
    $commands = @()
    $current = ''
    $depth = 0
    foreach ($line in (Get-Content $path -Encoding UTF8)) {
        if ($line -match '^\s*//' -or $line.Trim() -eq '') { continue }
        if ($line -match '^\s*\.' -and $current.Trim() -and $depth -le 0) { $commands += $current; $current = $line }
        else { if ($current) { $current += "`n$line" } else { $current = $line } }
        $depth += ([regex]::Matches($line, '\{')).Count - ([regex]::Matches($line, '\}')).Count
    }
    if ($current.Trim()) { $commands += $current }
    return $commands
}

function Send-ToOneLake($workspaceId, $lakehouseId, $localPath, $relativePath) {
    $token = Get-Token 'https://storage.azure.com'
    $h = @{ Authorization = "Bearer $token"; 'x-ms-version' = '2021-06-08' }
    $url = "https://onelake.dfs.fabric.microsoft.com/$workspaceId/$lakehouseId/Files/$relativePath"

    Invoke-RestMethod -Uri "${url}?resource=file" -Headers $h -Method Put | Out-Null

    # Duze pliki wysylamy porcjami - pojedynczy append ma limit po stronie uslugi.
    # telecom_coverage.jsonl ma ok. 76 MB, wiec bez dzielenia wysylka by sie nie powiodla.
    $chunkSize = 8MB
    $stream = [System.IO.File]::OpenRead($localPath)
    try {
        $buffer = New-Object byte[] $chunkSize
        $position = 0L
        $hAppend = $h.Clone(); $hAppend['Content-Type'] = 'application/octet-stream'
        while (($read = $stream.Read($buffer, 0, $chunkSize)) -gt 0) {
            $chunk = New-Object byte[] $read
            [Array]::Copy($buffer, 0, $chunk, 0, $read)
            Invoke-RestMethod -Uri "${url}?action=append&position=$position" -Headers $hAppend -Method Patch -Body $chunk | Out-Null
            $position += $read
        }
        Invoke-RestMethod -Uri "${url}?action=flush&position=$position" -Headers $h -Method Patch | Out-Null
    } finally { $stream.Dispose() }
    Write-Ok "$relativePath ($([math]::Round($position / 1MB, 1)) MB)"
}

# =========================================================================
Write-Step "Workspace: $WorkspaceName"
$ws = Resolve-Workspace
Write-Ok "workspace id = $($ws.id)"

Write-Step 'Elementy workspace'
$lakehouse  = New-FabricItem $ws.id 'Lakehouse'  $LakehouseName
$eventhouse = New-FabricItem $ws.id 'Eventhouse' $EventhouseName

$h = Get-FabricHeaders
$ehDetail   = Invoke-RestMethod -Uri "$FabricApi/workspaces/$($ws.id)/eventhouses/$($eventhouse.id)" -Headers $h
$clusterUri = $ehDetail.properties.queryServiceUri
$kqlDbName  = ((Invoke-RestMethod -Uri "$FabricApi/workspaces/$($ws.id)/kqlDatabases" -Headers $h).value |
               Where-Object id -eq $ehDetail.properties.databasesItemIds[0]).displayName
Write-Info "cluster  = $clusterUri"
Write-Info "baza KQL = $kqlDbName"

if ($Step -in 'all', 'upload') {
    Write-Step 'Wgrywanie plikow do OneLake'
    Get-ChildItem "$RepoRoot\datasets" -Filter *.csv | ForEach-Object {
        Send-ToOneLake $ws.id $lakehouse.id $_.FullName "datasets/$($_.Name)"
    }
    Get-ChildItem "$RepoRoot\datasets" -Filter *.jsonl | ForEach-Object {
        Send-ToOneLake $ws.id $lakehouse.id $_.FullName "streams/$($_.Name)"
    }
}

if ($Step -in 'all', 'kql') {
    Write-Step 'Tabele, mapowania i funkcje w Eventhouse'
    # 02_update_policies.kql musi byc wykonany po 01, bo funkcje odwoluja sie do tabel.
    foreach ($file in @('01_create_tables.kql', '02_update_policies.kql')) {
        $path = Join-Path $RepoRoot "kql\$file"
        if (-not (Test-Path $path)) { continue }
        foreach ($cmd in Split-KqlCommands $path) {
            $head = $cmd.Split("`n")[0]
            $head = $head.Substring(0, [Math]::Min(85, $head.Length))
            try { Invoke-KustoMgmt $clusterUri $kqlDbName $cmd | Out-Null; Write-Ok $head }
            catch { Write-Warn "$head :: $($_.Exception.Message)" }
        }
    }
}

if ($Step -in 'all', 'ingest') {
    Write-Step 'Ladowanie strumieni do Eventhouse'
    # klucz = tabela KQL, wartosc = plik JSONL i referencja mapowania
    $map = [ordered]@{
        'ReadinessDeclaration' = @{ file = 'fact_readiness_declaration'; mapping = 'readiness_declaration_mapping' }
        'TaskActivation'       = @{ file = 'fact_task_activation';       mapping = 'task_activation_mapping' }
    }
    foreach ($table in $map.Keys) {
        $url = "https://onelake.dfs.fabric.microsoft.com/$($ws.id)/$($lakehouse.id)/Files/streams/$($map[$table].file).jsonl"
        try {
            Invoke-KustoMgmt $clusterUri $kqlDbName ".clear table $table data" | Out-Null
            $cmd = ".ingest into table $table ('$url;impersonate') with (format='multijson', ingestionMappingReference='$($map[$table].mapping)')"
            Invoke-KustoMgmt $clusterUri $kqlDbName $cmd | Out-Null
            Write-Ok "zaladowano $table"
        }
        catch { Write-Warn "$table :: $($_.Exception.Message)" }
    }

    # Rejestry musza byc rowniez w Eventhouse: kafelki dashboardu, funkcje curated
    # i reguly alertowe nie moga siegac do tabel Delta w Lakehouse.
    # SafetyGrid, SpoChecklist i Interdependency maja nazwy inne niz pliki, bo tak
    # nazywaja je funkcje w kql/02_update_policies.kql.
    Write-Step 'Ladowanie rejestrow do Eventhouse'
    $dims = [ordered]@{
        'dim_hazard'         = @{ file = 'dim_hazard';         schema = 'hazard_code:string, hazard_name:string, category:string, probability:int, probability_label:string, impact:int, impact_label:string, risk_score:int, risk_level:string, color:string' }
        'dim_admin_division' = @{ file = 'dim_admin_division'; schema = 'admin_division:string, admin_name:string, ministry:string, subordinate_institutions:string' }
        'dim_task_module'    = @{ file = 'dim_task_module';    schema = 'task_module_id:int, task_module_name:string, description:string' }
        'dim_spo'            = @{ file = 'dim_spo';            schema = 'spo_code:string, spo_name:string, related_hazards:string' }
        'dim_contact_point'  = @{ file = 'dim_contact_point';  schema = 'admin_division:string, role:string, unit:string, duty_phone:string, email:string, deputy:string' }
        'SafetyGrid'         = @{ file = 'fact_safety_grid';   schema = 'hazard_code:string, admin_division:string, phase:string, task_modules:string, role:string, criticality:string' }
        'SpoChecklist'       = @{ file = 'fact_spo_checklist'; schema = 'spo_code:string, step_number:int, step_description:string, responsible_admin_division:string, sla_hours:int, required_document:string' }
        'Interdependency'    = @{ file = 'fact_interdependency'; schema = 'task_module_id:int, depends_on_task_module_id:int, dependency_reason:string' }
    }
    foreach ($table in $dims.Keys) {
        $url = "https://onelake.dfs.fabric.microsoft.com/$($ws.id)/$($lakehouse.id)/Files/datasets/$($dims[$table].file).csv"
        try {
            Invoke-KustoMgmt $clusterUri $kqlDbName ".create-merge table $table ($($dims[$table].schema))" | Out-Null
            Invoke-KustoMgmt $clusterUri $kqlDbName ".clear table $table data" | Out-Null
            Invoke-KustoMgmt $clusterUri $kqlDbName ".ingest into table $table ('$url;impersonate') with (format='csv', ignoreFirstRecord=true)" | Out-Null
            Write-Ok "zaladowano $table"
        }
        catch { Write-Warn "$table :: $($_.Exception.Message)" }
    }
}

if ($Step -in 'all', 'verify') {
    Write-Step 'Weryfikacja'
    $q = 'union withsource=T * | summarize Rekordy = count() by Tabela = T | order by Tabela asc'
    $res  = Invoke-KustoQuery $clusterUri $kqlDbName $q
    $cols = $res.Tables[0].Columns.ColumnName
    $res.Tables[0].Rows | ForEach-Object {
        $row = $_; $o = [ordered]@{}
        for ($i = 0; $i -lt $cols.Count; $i++) { $o[$cols[$i]] = $row[$i] }
        [PSCustomObject]$o
    } | Format-Table -AutoSize
}

Write-Host "`nGotowe. Workspace: https://app.fabric.microsoft.com/groups/$($ws.id)" -ForegroundColor Cyan
