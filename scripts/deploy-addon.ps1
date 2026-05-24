param(
    [string[]]$DestinationRoots
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$addonSource = Join-Path $repoRoot 'lua\AutoFish'

if (-not (Test-Path -LiteralPath $addonSource)) {
    throw "Addon source folder not found: $addonSource"
}

if ($null -eq $DestinationRoots -or $DestinationRoots.Count -eq 0) {
    $candidates = @(
        (Join-Path $env:USERPROFILE 'Documents\RIFT\Interface\Addons'),
        (Join-Path $env:USERPROFILE 'Documents\RIFT\Interface\AddOns'),
        (Join-Path $env:USERPROFILE 'OneDrive\Documents\RIFT\Interface\Addons'),
        (Join-Path $env:USERPROFILE 'OneDrive\Documents\RIFT\Interface\AddOns')
    )

    $DestinationRoots = @()
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            $resolved = (Resolve-Path -LiteralPath $candidate).Path
            if ($DestinationRoots -notcontains $resolved) {
                $DestinationRoots += $resolved
            }
        }
    }
}

if ($DestinationRoots.Count -eq 0) {
    throw 'No Rift Interface\Addons directory was found. Pass -DestinationRoots explicitly.'
}

foreach ($root in $DestinationRoots) {
    $resolvedRoot = (Resolve-Path -LiteralPath $root).Path
    $target = Join-Path $resolvedRoot 'AutoFish'

    if (-not (Test-Path -LiteralPath $target)) {
        $null = New-Item -ItemType Directory -Path $target -Force
    }

    Get-ChildItem -LiteralPath $addonSource -Force | Copy-Item -Destination $target -Recurse -Force
    Write-Host "[OK] Deployed AutoFish addon to $target"
}
