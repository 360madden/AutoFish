param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(0, 10000)]
    [int]$ClientX,

    [Parameter(Mandatory = $true)]
    [ValidateRange(0, 10000)]
    [int]$ClientY,

    [string]$RiftReaderRoot = 'C:\RIFT MODDING\RiftReader',
    [string]$ProcessName = 'rift_x64',
    [int]$TargetProcessId = 0,
    [string]$TargetWindowHandle,
    [string]$FishingKey = '8',
    [int]$KeyHoldMilliseconds = 60,
    [int]$PostClickDelayMilliseconds = 500,
    [switch]$SkipInitialClick,
    [switch]$SkipSecondClick,
    [switch]$DryRun,
    [string]$OutputRoot
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $OutputRoot = Join-Path $repoRoot ".autofish-live\fishable-point-$stamp"
}
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null

$preflightScript = Join-Path $PSScriptRoot 'run-live-preflight.ps1'
$keyScript = Join-Path $RiftReaderRoot 'scripts\post-rift-key.ps1'

foreach ($path in @($preflightScript, $keyScript)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required helper was not found: $path"
    }
}

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class AutoFishProbeNative
{
    [StructLayout(LayoutKind.Sequential)]
    public struct POINT { public int X; public int Y; }

    [DllImport("user32.dll", SetLastError = true)]
    public static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool ClientToScreen(IntPtr hWnd, ref POINT lpPoint);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool SetCursorPos(int X, int Y);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool IsWindow(IntPtr hWnd);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool GetClientRect(IntPtr hWnd, out RECT lpRect);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }
}
"@

function ConvertTo-WindowHandle {
    param([string]$HandleText)

    if ([string]::IsNullOrWhiteSpace($HandleText)) {
        return [IntPtr]::Zero
    }

    if ($HandleText.StartsWith('0x', [System.StringComparison]::OrdinalIgnoreCase)) {
        $raw = [UInt64]::Parse($HandleText.Substring(2), [System.Globalization.NumberStyles]::AllowHexSpecifier, [System.Globalization.CultureInfo]::InvariantCulture)
        return [IntPtr]([Int64]$raw)
    }

    return [IntPtr]([Int64]::Parse($HandleText, [System.Globalization.CultureInfo]::InvariantCulture))
}

function Invoke-Preflight {
    param([string]$Name)

    $path = Join-Path $OutputRoot $Name
    $args = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', $preflightScript,
        '-RiftReaderRoot', $RiftReaderRoot,
        '-ProcessName', $ProcessName,
        '-Focus',
        '-Capture',
        '-OutputRoot', $path
    )
    if ($TargetProcessId -gt 0) {
        $args += @('-ExpectedProcessId', $TargetProcessId)
    }
    if (-not [string]::IsNullOrWhiteSpace($TargetWindowHandle)) {
        $args += @('-ExpectedWindowHandle', $TargetWindowHandle)
    }

    $json = & pwsh @args
    if ($LASTEXITCODE -ne 0) {
        throw "Preflight '$Name' failed."
    }

    $jsonPath = Join-Path $OutputRoot "$Name.json"
    $json | Set-Content -Path $jsonPath -Encoding UTF8
    return ($json | ConvertFrom-Json -Depth 16)
}

function Invoke-ClientClick {
    param(
        [IntPtr]$WindowHandle,
        [int]$X,
        [int]$Y,
        [string]$Name,
        [switch]$DryRun
    )

    if (-not [AutoFishProbeNative]::IsWindow($WindowHandle)) {
        throw ("Target HWND 0x{0:X} is not a valid window." -f $WindowHandle.ToInt64())
    }

    $foreground = [AutoFishProbeNative]::GetForegroundWindow()
    if ($foreground -ne $WindowHandle) {
        throw ("Foreground mismatch before click '{0}': fg=0x{1:X}, expected=0x{2:X}." -f $Name, $foreground.ToInt64(), $WindowHandle.ToInt64())
    }

    $ownerPid = 0
    [void][AutoFishProbeNative]::GetWindowThreadProcessId($WindowHandle, [ref]$ownerPid)
    if ($TargetProcessId -gt 0 -and $ownerPid -ne $TargetProcessId) {
        throw ("Target HWND belongs to PID {0}, not expected PID {1}." -f $ownerPid, $TargetProcessId)
    }

    $clientRect = New-Object AutoFishProbeNative+RECT
    if (-not [AutoFishProbeNative]::GetClientRect($WindowHandle, [ref]$clientRect)) {
        throw 'GetClientRect failed.'
    }

    if ($X -lt 0 -or $Y -lt 0 -or $X -ge $clientRect.Right -or $Y -ge $clientRect.Bottom) {
        throw ("Client point ({0},{1}) is outside client rect {2}x{3}." -f $X, $Y, $clientRect.Right, $clientRect.Bottom)
    }

    $point = New-Object AutoFishProbeNative+POINT
    $point.X = $X
    $point.Y = $Y
    if (-not [AutoFishProbeNative]::ClientToScreen($WindowHandle, [ref]$point)) {
        throw 'ClientToScreen failed.'
    }

    if (-not $DryRun) {
        [void][AutoFishProbeNative]::SetCursorPos($point.X, $point.Y)
        Start-Sleep -Milliseconds 80
        [AutoFishProbeNative]::mouse_event(0x0002, [uint32]0, [uint32]0, [uint32]0, [UIntPtr]::Zero)
        Start-Sleep -Milliseconds 80
        [AutoFishProbeNative]::mouse_event(0x0004, [uint32]0, [uint32]0, [uint32]0, [UIntPtr]::Zero)
    }

    return [ordered]@{
        name = $Name
        dryRun = [bool]$DryRun
        clientX = $X
        clientY = $Y
        screenX = $point.X
        screenY = $point.Y
        hwnd = ('0x{0:X}' -f $WindowHandle.ToInt64())
        ownerProcessId = $ownerPid
    }
}

$summary = [ordered]@{
    generatedAtUtc = [DateTimeOffset]::UtcNow.ToString('O')
    safety = [ordered]@{
        sendsMovement = $false
        sendsLoop = $false
        sendsFishingKeyOnce = -not [bool]$DryRun
        clickCount = 0
    }
    request = [ordered]@{
        clientX = $ClientX
        clientY = $ClientY
        fishingKey = $FishingKey
        skipInitialClick = [bool]$SkipInitialClick
        skipSecondClick = [bool]$SkipSecondClick
        dryRun = [bool]$DryRun
    }
    preflight = $null
    actions = @()
    captures = @()
}

$summary.preflight = Invoke-Preflight -Name 'preflight'
$target = $summary.preflight.target
$resolvedPid = [int]$target.ProcessId
$resolvedHwndText = [string]$target.WindowHandleHex
$resolvedHwnd = ConvertTo-WindowHandle -HandleText $resolvedHwndText

if ($TargetProcessId -gt 0 -and $resolvedPid -ne $TargetProcessId) {
    throw "Preflight selected PID $resolvedPid, not expected PID $TargetProcessId."
}

if (-not [string]::IsNullOrWhiteSpace($TargetWindowHandle)) {
    $expectedHwnd = ConvertTo-WindowHandle -HandleText $TargetWindowHandle
    if ($resolvedHwnd -ne $expectedHwnd) {
        throw ("Preflight selected HWND 0x{0:X}, not expected 0x{1:X}." -f $resolvedHwnd.ToInt64(), $expectedHwnd.ToInt64())
    }
}

if (-not $SkipInitialClick) {
    $summary.actions += Invoke-ClientClick -WindowHandle $resolvedHwnd -X $ClientX -Y $ClientY -Name 'initial-click' -DryRun:$DryRun
    if (-not $DryRun) {
        $summary.safety.clickCount++
    }
    Start-Sleep -Milliseconds 200
}

if ($DryRun) {
    $summary.actions += [ordered]@{
        name = 'fishing-key'
        dryRun = $true
        key = $FishingKey
    }
}
else {
    $keyArgs = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', $keyScript,
        '-Key', $FishingKey,
        '-HoldMilliseconds', $KeyHoldMilliseconds,
        '-TargetProcessName', $ProcessName,
        '-TargetProcessId', $resolvedPid,
        '-TargetWindowHandle', $resolvedHwndText,
        '-TargetTitleContains', 'RIFT',
        '-RequireTargetForeground'
    )
    $keyOutput = & pwsh @keyArgs
    if ($LASTEXITCODE -ne 0) {
        throw 'Fishing key post failed.'
    }
    $keyOutputPath = Join-Path $OutputRoot 'fishing-key.txt'
    $keyOutput | Set-Content -Path $keyOutputPath -Encoding UTF8
    $summary.actions += [ordered]@{
        name = 'fishing-key'
        dryRun = $false
        key = $FishingKey
        outputPath = $keyOutputPath
    }
}

Start-Sleep -Milliseconds $PostClickDelayMilliseconds

if (-not $SkipSecondClick) {
    $summary.actions += Invoke-ClientClick -WindowHandle $resolvedHwnd -X $ClientX -Y $ClientY -Name 'second-click' -DryRun:$DryRun
    if (-not $DryRun) {
        $summary.safety.clickCount++
    }
}

Start-Sleep -Seconds 1
$summary.captures += Invoke-Preflight -Name 'after-1s'
Start-Sleep -Seconds 3
$summary.captures += Invoke-Preflight -Name 'after-4s'

$summaryPath = Join-Path $OutputRoot 'fishable-point-probe-summary.json'
$summary | ConvertTo-Json -Depth 20 | Set-Content -Path $summaryPath -Encoding UTF8
$summary | ConvertTo-Json -Depth 20
