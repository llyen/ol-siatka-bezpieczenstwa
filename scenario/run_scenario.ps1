<#
.SYNOPSIS
    Uruchamia scenariusz "POWODZ WRZESIEN" od zera i zasila Eventhouse w czasie rzeczywistym.

.DESCRIPTION
    Skrypt jest idempotentny: kazde uruchomienie z domyslnym resetem czysci tabele
    strumieniowe, laduje tlo scenariusza ingestia wsadowa i odtwarza okno live
    strumieniowo. Znaczniki czasu sa przypinane do biezacego zegara, wiec dashboard
    pokazuje swieze dane niezaleznie od pory uruchomienia.

    Scena: koordynacja miedzyresortowa przy zagrozeniu Z02 Powodz, faza R,
    os czasu D-1...D+10 (14-25.09.2026). D-1 (14.09) to tlo: dwa pierwsze
    modulu aktywowane wieczorem. Okno live zaczyna sie 15.09 o polnocy i
    obejmuje caly przebieg: naplyw 106 deklaracji gotowosci w D0 i D+1,
    aktywacje kolejnych modulow i ich wygaszanie po D+5.

.PARAMETER Preset
    demo       - caly przebieg D0...D+10 w ok. 24 min - domyslny
    szybki     - ten sam zakres w ok. 6 min; smoke-test, nie do prezentacji
    kulminacja - pierwsze 48 h (naplyw deklaracji gotowosci) w ok. 24 min;
                 najgestszy fragment sceny, 106 deklaracji i 16 aktywacji
    wolny      - caly przebieg w ok. 48 min, do prezentacji w tle
    ciagly     - scenariusz zapetla sie bez konca; dashboard jest na zywo o kazdej porze

.PARAMETER Background
    Uruchamia odtwarzanie jako proces w tle, PID w scenario\_ciagly.pid,
    log w scenario\_ciagly.log. Wlasciwe dla trybu ciaglego.

.PARAMETER Stop
    Zatrzymuje proces zapisany w scenario\_ciagly.pid.

.PARAMETER NoReset
    Nie czysci tabel i nie laduje tla; dokleja okno live do istniejacych danych.

.PARAMETER ResetOnly
    Tylko czysci tabele strumieniowe i konczy prace.

.PARAMETER TimeMode
    wall   - domyslny: scena skompresowana tempem i przypieta do biezacego zegara.
             Tylko ten tryb daje efekt czasu rzeczywistego w oknie "ostatnie 15 minut".
    source - oryginalne znaczniki scenariusza (styczen 2026)
    now    - staly offset tak, by scena zaczynala sie w chwili uruchomienia

.EXAMPLE
    .\scenario\run_scenario.ps1
.EXAMPLE
    .\scenario\run_scenario.ps1 -Preset ciagly -Background
.EXAMPLE
    .\scenario\run_scenario.ps1 -ResetOnly
#>
[CmdletBinding()]
param(
    [ValidateSet('demo', 'szybki', 'kulminacja', 'wolny', 'ciagly')]
    [string]$Preset = 'demo',
    [switch]$NoReset,
    [switch]$ResetOnly,
    [ValidateSet('wall', 'source', 'now')]
    [string]$TimeMode = 'wall',
    [double]$Speed,
    [string]$Streams,
    [switch]$Background,
    [switch]$Stop
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $PSScriptRoot '_ciagly.pid'
$logFile = Join-Path $PSScriptRoot '_ciagly.log'
$errFile = Join-Path $PSScriptRoot '_ciagly.err.log'
$workspaceId = '5965cbe7-b1f4-4c64-b397-5c78de66d1fc'

function Stop-Replay {
    if (-not (Test-Path $pidFile)) { Write-Host 'Brak zapisanego procesu odtwarzania.'; return }
    $existing = Get-Content $pidFile
    $proc = Get-Process -Id $existing -ErrorAction SilentlyContinue
    if ($proc) { Stop-Process -Id $existing -Force; Write-Host "Zatrzymano odtwarzanie (PID $existing)." }
    else { Write-Host "Proces $existing juz nie dziala." }
    Remove-Item $pidFile -Force
}

if ($Stop) { Stop-Replay; return }

# Scena jest odwrotnoscia blackoutu: bardzo dluga (11 dni) i bardzo rzadka
# (185 zdarzen lacznie). Dlatego tempo jest o rzad wielkosci wyzsze - inaczej
# odtworzenie calego przebiegu trwaloby dobe zegara. Przy 660x doba scenariusza
# mija w ok. 2,2 min, a caly przebieg D0...D+10 w ok. 24 min.
$presets = @{
    demo       = @{ Speed = 660;  LiveHours = 264; From = $null }
    szybki     = @{ Speed = 2640; LiveHours = 264; From = $null }
    kulminacja = @{ Speed = 120;  LiveHours = 48;  From = '2026-09-15T00:00:00+02:00' }
    wolny      = @{ Speed = 330;  LiveHours = 264; From = $null }
    ciagly     = @{ Speed = 660;  LiveHours = 264; From = $null; Loop = $true }
}
$selected = $presets[$Preset]
if ($PSBoundParameters.ContainsKey('Speed')) { $selected.Speed = $Speed }

Write-Host '=== Scenariusz: POWODZ WRZESIEN - koordynacja miedzyresortowa' -ForegroundColor Cyan
Write-Host "  wariant:   $Preset"
Write-Host "  tempo:     $($selected.Speed)x czasu rzeczywistego"
Write-Host "  okno live: $($selected.LiveHours) h scenariusza"
Write-Host "  znaczniki: $TimeMode"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw 'Brak python w PATH.' }

$argv = @('-u', (Join-Path $PSScriptRoot 'replay.py'), '--speed', $selected.Speed,
          '--live-hours', $selected.LiveHours, '--time-mode', $TimeMode)
if (-not $NoReset) { $argv += @('--reset', '--bulk') }
if ($ResetOnly) { $argv += @('--reset', '--reset-only') }
if ($selected.From) { $argv += @('--from', $selected.From) }
if ($selected.Loop) { $argv += '--loop' }
if ($Streams) { $argv += @('--streams', $Streams) }

Push-Location $repo
try {
    if ($Background) {
        Stop-Replay
        $proc = Start-Process -FilePath $python.Source -ArgumentList $argv -PassThru `
            -RedirectStandardOutput $logFile -RedirectStandardError $errFile -WindowStyle Hidden
        $proc.Id | Set-Content $pidFile
        Write-Host "Odtwarzanie w tle, PID $($proc.Id). Log: $logFile" -ForegroundColor Green
        Write-Host 'Zatrzymanie: .\scenario\run_scenario.ps1 -Stop'
    }
    else {
        & $python.Source @argv
        if ($LASTEXITCODE -ne 0) { throw "replay.py zakonczyl sie kodem $LASTEXITCODE" }
    }
}
finally {
    Pop-Location
}

if (-not $ResetOnly -and -not $Background) {
    Write-Host ''
    Write-Host "Dashboard: https://app.fabric.microsoft.com/groups/$workspaceId" -ForegroundColor Green
    Write-Host 'Wskazowka: wlacz auto-odswiezanie na dashboardzie, aby widziec naplyw zdarzen.'
}
