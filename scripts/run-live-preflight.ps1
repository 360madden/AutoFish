param(
    [string]$RiftReaderRoot = 'C:\RIFT MODDING\RiftReader',
    [string]$ProcessName = 'rift_x64',
    [int]$ExpectedProcessId = 0,
    [string]$ExpectedWindowHandle,
    [switch]$Focus,
    [switch]$Capture,
    [string]$OutputRoot
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $OutputRoot = Join-Path $repoRoot ".autofish-live\preflight-$stamp"
}
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null

$discoverScript = Join-Path $RiftReaderRoot 'scripts\get-rift-window-targets.ps1'
$targetControl = Join-Path $RiftReaderRoot 'scripts\riftreader-target-control.cmd'
$windowHelper = Join-Path $RiftReaderRoot 'tools\rift-game-mcp\helpers\window-tools.ps1'

foreach ($path in @($discoverScript, $targetControl, $windowHelper)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required RiftReader helper was not found: $path"
    }
}

$discoverArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $discoverScript, '-ProcessName', $ProcessName, '-Json')
if ($ExpectedProcessId -gt 0) {
    $discoverArgs += @('-ExpectedMovementProcessId', $ExpectedProcessId)
}
if (-not [string]::IsNullOrWhiteSpace($ExpectedWindowHandle)) {
    $discoverArgs += @('-ExpectedMovementWindowHandle', $ExpectedWindowHandle)
}

$discoveryText = & pwsh @discoverArgs
if ($LASTEXITCODE -ne 0) {
    throw 'Rift target discovery failed.'
}
$discoveryPath = Join-Path $OutputRoot 'g0-target-discovery.json'
$discoveryText | Set-Content -Path $discoveryPath -Encoding UTF8
$discovery = $discoveryText | ConvertFrom-Json -Depth 12

if (-not $discovery.ok) {
    throw "Discovery failed: $($discovery.errors -join '; ')"
}
if ([int]$discovery.count -ne 1 -and ($ExpectedProcessId -le 0 -or [string]::IsNullOrWhiteSpace($ExpectedWindowHandle))) {
    throw "Expected exactly one Rift target or explicit expected PID/HWND; found $($discovery.count)."
}

$target = $discovery.movement
if ($null -eq $target) {
    throw 'No movement/current target was selected by discovery.'
}
$targetPid = [int]$target.ProcessId
$targetHwnd = [string]$target.WindowHandleHex

$summary = [ordered]@{
    generatedAtUtc = [DateTimeOffset]::UtcNow.ToString('O')
    status = 'target-discovered'
    target = $target
    discoveryPath = $discoveryPath
    focus = $null
    capture = $null
    safety = [ordered]@{
        movementSent = $false
        hotbarSent = $false
        slashCommandSent = $false
        focusRequested = [bool]$Focus
        captureRequested = [bool]$Capture
    }
}

if ($Focus) {
    $focusText = & $targetControl --pid $targetPid --hwnd $targetHwnd --process-name $ProcessName --title-contains RIFT --json
    if ($LASTEXITCODE -ne 0) {
        throw 'Target-control focus/preflight failed.'
    }
    $focusPath = Join-Path $OutputRoot 'g0-target-control.json'
    $focusText | Set-Content -Path $focusPath -Encoding UTF8
    $summary.focus = [ordered]@{
        path = $focusPath
        output = ($focusText | ConvertFrom-Json -Depth 12)
    }
}

if ($Capture) {
    $capturePath = Join-Path $OutputRoot 'g0-baseline.png'
    $captureText = & pwsh -NoProfile -ExecutionPolicy Bypass -File $windowHelper -Operation capture -ProcessName $ProcessName -ProcessId $targetPid -WindowHandle $targetHwnd -OutputPath $capturePath
    if ($LASTEXITCODE -ne 0) {
        throw 'Target capture failed.'
    }
    $captureJsonPath = Join-Path $OutputRoot 'g0-baseline-capture.json'
    $captureText | Set-Content -Path $captureJsonPath -Encoding UTF8
    $summary.capture = [ordered]@{
        jsonPath = $captureJsonPath
        screenshotPath = $capturePath
        output = ($captureText | ConvertFrom-Json -Depth 12)
    }
}

$summaryPath = Join-Path $OutputRoot 'g0-preflight-summary.json'
$summary | ConvertTo-Json -Depth 16 | Set-Content -Path $summaryPath -Encoding UTF8
$summary | ConvertTo-Json -Depth 16
