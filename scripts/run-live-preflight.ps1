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
$windowHelper = Join-Path $RiftReaderRoot 'tools\rift-game-mcp\helpers\window-tools.ps1'

foreach ($path in @($discoverScript, $windowHelper)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required RiftReader helper was not found: $path"
    }
}

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public static class AutoFishPreflightNative
{
    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool IsWindow(IntPtr hWnd);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool IsIconic(IntPtr hWnd);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll", SetLastError = true)]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
}
"@

function ConvertTo-WindowHandle {
    param([Parameter(Mandatory = $true)][string]$HandleText)

    if ($HandleText.StartsWith('0x', [System.StringComparison]::OrdinalIgnoreCase)) {
        $raw = [UInt64]::Parse($HandleText.Substring(2), [System.Globalization.NumberStyles]::AllowHexSpecifier, [System.Globalization.CultureInfo]::InvariantCulture)
        return [IntPtr]([Int64]$raw)
    }

    return [IntPtr]([Int64]::Parse($HandleText, [System.Globalization.CultureInfo]::InvariantCulture))
}

function Get-ForegroundSummary {
    $foreground = [AutoFishPreflightNative]::GetForegroundWindow()
    $foregroundPid = [uint32]0
    if ($foreground -ne [IntPtr]::Zero) {
        [void][AutoFishPreflightNative]::GetWindowThreadProcessId($foreground, [ref]$foregroundPid)
    }

    return [ordered]@{
        foregroundWindowHandle = $foreground.ToInt64()
        foregroundWindowHandleHex = if ($foreground -ne [IntPtr]::Zero) { "0x{0:X}" -f $foreground.ToInt64() } else { $null }
        foregroundProcessId = if ($foregroundPid -gt 0) { [int]$foregroundPid } else { $null }
    }
}

function Invoke-FocusPreservingWindow {
    param(
        [Parameter(Mandatory = $true)][string]$WindowHandleHex,
        [Parameter(Mandatory = $true)][int]$ProcessId
    )

    $handle = ConvertTo-WindowHandle -HandleText $WindowHandleHex
    if (-not [AutoFishPreflightNative]::IsWindow($handle)) {
        throw "Target window handle '$WindowHandleHex' is not a valid window."
    }

    $ownerPid = [uint32]0
    [void][AutoFishPreflightNative]::GetWindowThreadProcessId($handle, [ref]$ownerPid)
    if ([int]$ownerPid -ne $ProcessId) {
        throw "Target window handle '$WindowHandleHex' belongs to PID $ownerPid, not expected PID $ProcessId."
    }

    $before = Get-ForegroundSummary
    $wasMinimized = [AutoFishPreflightNative]::IsIconic($handle)
    $restoreSent = $false
    if ($wasMinimized) {
        [void][AutoFishPreflightNative]::ShowWindow($handle, 9) # SW_RESTORE only when minimized.
        $restoreSent = $true
        Start-Sleep -Milliseconds 100
    }

    $setForegroundOk = [AutoFishPreflightNative]::SetForegroundWindow($handle)
    Start-Sleep -Milliseconds 250
    $after = Get-ForegroundSummary
    $foregroundMatches = ($after.foregroundWindowHandle -eq $handle.ToInt64()) -and ($after.foregroundProcessId -eq $ProcessId)
    if (-not $foregroundMatches) {
        throw ("Focus-preserving foreground failed: foreground=0x{0:X}, expected={1}." -f [int64]$after.foregroundWindowHandle, $WindowHandleHex)
    }

    return [ordered]@{
        status = 'passed-focus-preserving'
        classification = 'exact-hwnd-foreground-preserve-size'
        ok = $true
        readyForReadOnlyProof = $true
        readyForVisualGate = $true
        readyForLiveInput = $true
        movementSent = $false
        inputSent = $false
        screenshotKeySent = $false
        reloaduiSent = $false
        attemptedAtUtc = [DateTimeOffset]::UtcNow.ToString('O')
        target = [ordered]@{
            processId = $ProcessId
            windowHandleHex = $WindowHandleHex
        }
        beforeForeground = $before
        afterForeground = $after
        wasMinimized = [bool]$wasMinimized
        restoreSent = $restoreSent
        setForegroundOk = [bool]$setForegroundOk
        preservesRestoredOrMaximizedSize = $true
        policyNotes = @(
            'Focus only calls SW_RESTORE if the target is minimized.',
            'Non-minimized and maximized Rift windows are brought foreground without restoring to the small saved window size.'
        )
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
    $focusOutput = Invoke-FocusPreservingWindow -WindowHandleHex $targetHwnd -ProcessId $targetPid
    $focusPath = Join-Path $OutputRoot 'g0-focus-preserving.json'
    $focusOutput | ConvertTo-Json -Depth 16 | Set-Content -Path $focusPath -Encoding UTF8
    $summary.focus = [ordered]@{
        path = $focusPath
        output = $focusOutput
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
    $captureOutput = $captureText | ConvertFrom-Json -Depth 12
    $clientRect = $captureOutput.window.clientRect
    $preferredWidth = 960
    $preferredHeight = 540
    $belowPreferred = $clientRect.width -lt $preferredWidth -or $clientRect.height -lt $preferredHeight
    $summary.capture = [ordered]@{
        jsonPath = $captureJsonPath
        screenshotPath = $capturePath
        output = $captureOutput
        readability = [ordered]@{
            preferredMinimumClientWidth = $preferredWidth
            preferredMinimumClientHeight = $preferredHeight
            belowPreferredMinimum = $belowPreferred
            warning = if ($belowPreferred) { 'Client is below preferred proof-capture size; enlarge Rift before evidence runs if readable screenshots matter.' } else { $null }
        }
    }
}

$summaryPath = Join-Path $OutputRoot 'g0-preflight-summary.json'
$summary | ConvertTo-Json -Depth 16 | Set-Content -Path $summaryPath -Encoding UTF8
$summary | ConvertTo-Json -Depth 16
