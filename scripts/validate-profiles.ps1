param(
    [string]$ProfilesDirectory = (Join-Path $PSScriptRoot '..\profiles')
)

$resolvedProfilesDirectory = (Resolve-Path -LiteralPath $ProfilesDirectory).Path
$files = Get-ChildItem -LiteralPath $resolvedProfilesDirectory -Filter '*.json' -File | Sort-Object Name

if ($files.Count -eq 0) {
    throw "No profile JSON files found in $resolvedProfilesDirectory"
}

$ids = @{}

foreach ($file in $files) {
    $profile = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json

    if ([string]::IsNullOrWhiteSpace($profile.id)) {
        throw "Profile '$($file.Name)' is missing a non-empty id."
    }

    if ($ids.ContainsKey($profile.id)) {
        throw "Duplicate profile id '$($profile.id)' found in '$($file.Name)' and '$($ids[$profile.id])'."
    }

    $ids[$profile.id] = $file.Name

    foreach ($requiredValue in @('displayName', 'zoneName', 'targetSkill')) {
        if ([string]::IsNullOrWhiteSpace($profile.$requiredValue)) {
            throw "Profile '$($file.Name)' is missing '$requiredValue'."
        }
    }

    if (-not $profile.enabledSkills -or $profile.enabledSkills.Count -lt 1) {
        throw "Profile '$($file.Name)' must define at least one enabled skill."
    }

    if ($profile.pacing.reactionFloorMs -gt $profile.pacing.reactionCeilingMs) {
        throw "Profile '$($file.Name)' has reactionFloorMs greater than reactionCeilingMs."
    }

    if ($profile.thresholds.maintenanceAtFreeSlotsOrBelow -lt 0 -or
        $profile.thresholds.rebaitAtOrBelow -lt 0 -or
        $profile.thresholds.maxRecoveryAttempts -lt 0) {
        throw "Profile '$($file.Name)' contains a negative threshold value."
    }
}

Write-Host "Validated $($files.Count) profile file(s) in $resolvedProfilesDirectory."
