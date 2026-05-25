param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(0, 10000)]
    [int]$ClientX,

    [Parameter(Mandatory = $true)]
    [ValidateRange(0, 10000)]
    [int]$ClientY,

    [Parameter(Mandatory = $true)]
    [int]$TargetProcessId,

    [Parameter(Mandatory = $true)]
    [string]$TargetWindowHandle,

    [ValidateRange(-1, 10000)]
    [int]$ActionClientX = -1,
    [ValidateRange(-1, 10000)]
    [int]$ActionClientY = -1,
    [string]$RiftReaderRoot = 'C:\RIFT MODDING\RiftReader',
    [string]$ProcessName = 'rift_x64',
    [string]$FishingKey = '8',
    [ValidateRange(1, 100)]
    [int]$MaxCasts = 1,
    [ValidateRange(1, 120)]
    [int]$CastWaitSeconds = 18,
    [ValidateRange(0, 5000)]
    [int]$PostKeyClickDelayMilliseconds = 500,
    [ValidateRange(20, 2000)]
    [int]$KeyHoldMilliseconds = 80,
    [switch]$SkipInitialClick,
    [switch]$SkipConfirmClick,
    [ValidateRange(0, 10)]
    [int]$PullClicks = 1,
    [ValidateRange(0, 5000)]
    [int]$PostPullDelayMilliseconds = 1200,
    [switch]$DryRun,
    [switch]$CaptureEachCast,
    [string]$EmergencyStopPath,
    [string]$OutputRoot
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $OutputRoot = Join-Path $repoRoot ".autofish-live\fishing-prototype-$stamp"
}
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($EmergencyStopPath)) {
    $EmergencyStopPath = Join-Path $OutputRoot 'STOP.txt'
}

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

public static class AutoFishPrototypeNative
{
    [StructLayout(LayoutKind.Sequential)]
    public struct POINT { public int X; public int Y; }

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct INPUT
    {
        public uint type;
        public InputUnion U;
    }

    [StructLayout(LayoutKind.Explicit)]
    public struct InputUnion
    {
        [FieldOffset(0)] public MOUSEINPUT mi;
        [FieldOffset(0)] public KEYBDINPUT ki;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct MOUSEINPUT
    {
        public int dx;
        public int dy;
        public uint mouseData;
        public uint dwFlags;
        public uint time;
        public IntPtr dwExtraInfo;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct KEYBDINPUT
    {
        public ushort wVk;
        public ushort wScan;
        public uint dwFlags;
        public uint time;
        public IntPtr dwExtraInfo;
    }

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

    [DllImport("user32.dll", SetLastError = true)]
    public static extern short VkKeyScan(char ch);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);
}
"@

function ConvertTo-WindowHandle {
    param([string]$HandleText)

    if ($HandleText.StartsWith('0x', [System.StringComparison]::OrdinalIgnoreCase)) {
        $raw = [UInt64]::Parse($HandleText.Substring(2), [System.Globalization.NumberStyles]::AllowHexSpecifier, [System.Globalization.CultureInfo]::InvariantCulture)
        return [IntPtr]([Int64]$raw)
    }

    return [IntPtr]([Int64]::Parse($HandleText, [System.Globalization.CultureInfo]::InvariantCulture))
}

function ConvertTo-VirtualKey {
    param([string]$Key)

    switch -Regex ($Key) {
        '^(?i:space)$' { return [uint16]0x20 }
        '^(?i:enter|return)$' { return [uint16]0x0D }
        '^(?i:esc|escape)$' { return [uint16]0x1B }
        default {
            if ($Key.Length -ne 1) {
                throw "Unsupported key '$Key'. Use one character, Space, Enter, or Escape."
            }

            $scan = [AutoFishPrototypeNative]::VkKeyScan($Key[0])
            if ($scan -eq -1) {
                throw "Unable to map key '$Key' to a virtual key."
            }

            return [uint16]($scan -band 0xFF)
        }
    }
}

function Invoke-Preflight {
    param([string]$Name)

    $path = Join-Path $OutputRoot $Name
    $json = & pwsh -NoProfile -ExecutionPolicy Bypass -File $preflightScript `
        -RiftReaderRoot $RiftReaderRoot `
        -ProcessName $ProcessName `
        -ExpectedProcessId $TargetProcessId `
        -ExpectedWindowHandle $TargetWindowHandle `
        -Focus `
        -Capture `
        -OutputRoot $path

    if ($LASTEXITCODE -ne 0) {
        throw "Preflight '$Name' failed."
    }

    $jsonPath = Join-Path $OutputRoot "$Name.json"
    $json | Set-Content -Path $jsonPath -Encoding UTF8
    return ($json | ConvertFrom-Json -Depth 16)
}

function Test-EmergencyStop {
    if (Test-Path -LiteralPath $EmergencyStopPath) {
        throw "Emergency stop file exists: $EmergencyStopPath"
    }
}

function Assert-TargetReady {
    param([IntPtr]$WindowHandle)

    if (-not [AutoFishPrototypeNative]::IsWindow($WindowHandle)) {
        throw ("Target HWND 0x{0:X} is not a valid window." -f $WindowHandle.ToInt64())
    }

    $ownerPid = 0
    [void][AutoFishPrototypeNative]::GetWindowThreadProcessId($WindowHandle, [ref]$ownerPid)
    if ($ownerPid -ne $TargetProcessId) {
        throw ("Target HWND belongs to PID {0}, not expected PID {1}." -f $ownerPid, $TargetProcessId)
    }

    $foreground = [AutoFishPrototypeNative]::GetForegroundWindow()
    if ($foreground -ne $WindowHandle) {
        throw ("Foreground mismatch: fg=0x{0:X}, expected=0x{1:X}." -f $foreground.ToInt64(), $WindowHandle.ToInt64())
    }

    $clientRect = New-Object AutoFishPrototypeNative+RECT
    if (-not [AutoFishPrototypeNative]::GetClientRect($WindowHandle, [ref]$clientRect)) {
        throw 'GetClientRect failed.'
    }

    if ($ClientX -lt 0 -or $ClientY -lt 0 -or $ClientX -ge $clientRect.Right -or $ClientY -ge $clientRect.Bottom) {
        throw ("Client point ({0},{1}) is outside client rect {2}x{3}." -f $ClientX, $ClientY, $clientRect.Right, $clientRect.Bottom)
    }

    return [ordered]@{
        ownerProcessId = $ownerPid
        clientWidth = $clientRect.Right
        clientHeight = $clientRect.Bottom
    }
}

function Get-ScreenPoint {
    param(
        [IntPtr]$WindowHandle,
        [int]$X,
        [int]$Y
    )

    $point = New-Object AutoFishPrototypeNative+POINT
    $point.X = $X
    $point.Y = $Y
    if (-not [AutoFishPrototypeNative]::ClientToScreen($WindowHandle, [ref]$point)) {
        throw 'ClientToScreen failed.'
    }

    return $point
}

function Invoke-ClientClick {
    param(
        [IntPtr]$WindowHandle,
        [int]$X,
        [int]$Y,
        [string]$Name
    )

    Test-EmergencyStop
    $target = Assert-TargetReady -WindowHandle $WindowHandle
    $point = Get-ScreenPoint -WindowHandle $WindowHandle -X $X -Y $Y

    if (-not $DryRun) {
        [void][AutoFishPrototypeNative]::SetCursorPos($point.X, $point.Y)
        Start-Sleep -Milliseconds 80
        [AutoFishPrototypeNative]::mouse_event(0x0002, [uint32]0, [uint32]0, [uint32]0, [UIntPtr]::Zero)
        Start-Sleep -Milliseconds 80
        [AutoFishPrototypeNative]::mouse_event(0x0004, [uint32]0, [uint32]0, [uint32]0, [UIntPtr]::Zero)
    }

    return [ordered]@{
        name = $Name
        dryRun = [bool]$DryRun
        clientX = $X
        clientY = $Y
        screenX = $point.X
        screenY = $point.Y
        ownerProcessId = $target.ownerProcessId
    }
}

function Invoke-KeyPress {
    param(
        [IntPtr]$WindowHandle,
        [string]$Key,
        [string]$Name
    )

    Test-EmergencyStop
    [void](Assert-TargetReady -WindowHandle $WindowHandle)
    $vk = ConvertTo-VirtualKey -Key $Key

    if (-not $DryRun) {
        $keyOutput = & pwsh -NoProfile -ExecutionPolicy Bypass -File $keyScript `
            -Key $Key `
            -HoldMilliseconds $KeyHoldMilliseconds `
            -TargetProcessName $ProcessName `
            -TargetProcessId $TargetProcessId `
            -TargetWindowHandle $TargetWindowHandle `
            -TargetTitleContains RIFT `
            -RequireTargetForeground

        if ($LASTEXITCODE -ne 0) {
            throw "RiftReader key helper failed for key '$Key'."
        }
    }

    return [ordered]@{
        name = $Name
        dryRun = [bool]$DryRun
        key = $Key
        virtualKey = $vk
        holdMilliseconds = $KeyHoldMilliseconds
        helper = $(if ($DryRun) { $null } else { 'post-rift-key.ps1' })
    }
}

$summary = [ordered]@{
    generatedAtUtc = [DateTimeOffset]::UtcNow.ToString('O')
    mode = 'prototype'
    safety = [ordered]@{
        sendsMovement = $false
        sendsLoop = $MaxCasts -gt 1
        maxCasts = $MaxCasts
        dryRun = [bool]$DryRun
        emergencyStopPath = $EmergencyStopPath
    }
    request = [ordered]@{
        clientX = $ClientX
        clientY = $ClientY
        actionClientX = $ActionClientX
        actionClientY = $ActionClientY
        fishingKey = $FishingKey
        castWaitSeconds = $CastWaitSeconds
        keyHoldMilliseconds = $KeyHoldMilliseconds
        pullClicks = $PullClicks
        skipInitialClick = [bool]$SkipInitialClick
        skipConfirmClick = [bool]$SkipConfirmClick
    }
    preflight = $null
    casts = @()
    finalCapture = $null
}

$summary.preflight = Invoke-Preflight -Name 'preflight'
$target = $summary.preflight.target
$resolvedPid = [int]$target.ProcessId
$resolvedHwndText = [string]$target.WindowHandleHex
$resolvedHwnd = ConvertTo-WindowHandle -HandleText $resolvedHwndText

if ($resolvedPid -ne $TargetProcessId) {
    throw "Preflight selected PID $resolvedPid, not expected PID $TargetProcessId."
}

$expectedHwnd = ConvertTo-WindowHandle -HandleText $TargetWindowHandle
if ($resolvedHwnd -ne $expectedHwnd) {
    throw ("Preflight selected HWND 0x{0:X}, not expected 0x{1:X}." -f $resolvedHwnd.ToInt64(), $expectedHwnd.ToInt64())
}

for ($castNumber = 1; $castNumber -le $MaxCasts; $castNumber++) {
    Test-EmergencyStop

    $cast = [ordered]@{
        castNumber = $castNumber
        startedAtUtc = [DateTimeOffset]::UtcNow.ToString('O')
        actions = @()
        capture = $null
    }

    if (-not $SkipInitialClick) {
        $cast.actions += Invoke-ClientClick -WindowHandle $resolvedHwnd -X $ClientX -Y $ClientY -Name 'select-fishable-point'
        Start-Sleep -Milliseconds 200
    }

    if ($ActionClientX -ge 0 -and $ActionClientY -ge 0) {
        $cast.actions += Invoke-ClientClick -WindowHandle $resolvedHwnd -X $ActionClientX -Y $ActionClientY -Name 'click-action-slot'
    }
    else {
        $cast.actions += Invoke-KeyPress -WindowHandle $resolvedHwnd -Key $FishingKey -Name 'press-fishing-key'
    }
    Start-Sleep -Milliseconds $PostKeyClickDelayMilliseconds

    if (-not $SkipConfirmClick) {
        $cast.actions += Invoke-ClientClick -WindowHandle $resolvedHwnd -X $ClientX -Y $ClientY -Name 'confirm-cast-point'
    }

    if (-not $DryRun) {
        Start-Sleep -Seconds $CastWaitSeconds
    }

    for ($pull = 1; $pull -le $PullClicks; $pull++) {
        $cast.actions += Invoke-ClientClick -WindowHandle $resolvedHwnd -X $ClientX -Y $ClientY -Name "pull-or-loot-$pull"
        if (-not $DryRun -and $PostPullDelayMilliseconds -gt 0) {
            Start-Sleep -Milliseconds $PostPullDelayMilliseconds
        }
    }

    $cast.completedAtUtc = [DateTimeOffset]::UtcNow.ToString('O')

    if ($CaptureEachCast) {
        $cast.capture = Invoke-Preflight -Name ('after-cast-{0:000}' -f $castNumber)
    }

    $summary.casts += $cast
}

$summary.finalCapture = Invoke-Preflight -Name 'final'
$summaryPath = Join-Path $OutputRoot 'fishing-prototype-summary.json'
$summary | ConvertTo-Json -Depth 24 | Set-Content -Path $summaryPath -Encoding UTF8
$summary | ConvertTo-Json -Depth 24
