param(
    [string]$ProfilesDirectory = (Join-Path $PSScriptRoot '..\profiles')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Add-ValidationError {
    param(
        [System.Collections.Generic.List[string]]$Errors,
        [string]$Message
    )

    $null = $Errors.Add($Message)
}

function Get-PropertyValue {
    param(
        [object]$Object,
        [string]$Name
    )

    if ($Object -is [System.Collections.IDictionary]) {
        if ($Object.Contains($Name)) {
            return ,$Object[$Name]
        }

        return $null
    }

    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $null
    }

    return ,$property.Value
}

function Test-AllowedProperties {
    param(
        [object]$Object,
        [string[]]$Allowed,
        [string]$Context,
        [System.Collections.Generic.List[string]]$Errors
    )

    $propertyNames = if ($Object -is [System.Collections.IDictionary]) { @($Object.Keys) } else { @($Object.PSObject.Properties.Name) }

    foreach ($property in $propertyNames) {
        if ($Allowed -notcontains $property) {
            Add-ValidationError -Errors $Errors -Message "$Context contains unexpected property '$property'."
        }
    }
}

function Test-RequiredStringProperty {
    param(
        [object]$Object,
        [string]$Name,
        [string]$FilePath,
        [System.Collections.Generic.List[string]]$Errors
    )

    $value = Get-PropertyValue -Object $Object -Name $Name
    if ($value -isnot [string] -or [string]::IsNullOrWhiteSpace($value)) {
        Add-ValidationError -Errors $Errors -Message "${FilePath}: property '$Name' must be a non-empty string."
    }
}

function Test-OptionalStringProperty {
    param(
        [object]$Object,
        [string]$Name,
        [string]$FilePath,
        [System.Collections.Generic.List[string]]$Errors
    )

    $value = Get-PropertyValue -Object $Object -Name $Name
    if ($null -ne $value -and $value -isnot [string]) {
        Add-ValidationError -Errors $Errors -Message "${FilePath}: property '$Name' must be a string or null."
    }
}

function Test-BoolProperty {
    param(
        [object]$Object,
        [string]$Name,
        [string]$FilePath,
        [System.Collections.Generic.List[string]]$Errors
    )

    $value = Get-PropertyValue -Object $Object -Name $Name
    if ($value -isnot [bool]) {
        Add-ValidationError -Errors $Errors -Message "${FilePath}: property '$Name' must be a boolean."
    }
}

function Test-IntegerProperty {
    param(
        [object]$Object,
        [string]$Name,
        [string]$FilePath,
        [int]$Minimum,
        [System.Collections.Generic.List[string]]$Errors
    )

    $value = Get-PropertyValue -Object $Object -Name $Name
    if ($null -eq $value) {
        Add-ValidationError -Errors $Errors -Message "${FilePath}: property '$Name' is required."
        return
    }

    try {
        $numericValue = [double]$value
    }
    catch {
        Add-ValidationError -Errors $Errors -Message "${FilePath}: property '$Name' must be numeric."
        return
    }

    if ([math]::Floor($numericValue) -ne $numericValue) {
        Add-ValidationError -Errors $Errors -Message "${FilePath}: property '$Name' must be an integer."
        return
    }

    if ($numericValue -lt $Minimum) {
        Add-ValidationError -Errors $Errors -Message "${FilePath}: property '$Name' must be greater than or equal to $Minimum."
    }
}

function Test-StringArrayProperty {
    param(
        [object]$Object,
        [string]$Name,
        [string]$FilePath,
        [int]$MinimumCount,
        [bool]$Required,
        [System.Collections.Generic.List[string]]$Errors
    )

    $value = Get-PropertyValue -Object $Object -Name $Name
    if ($null -eq $value) {
        if ($Required) {
            Add-ValidationError -Errors $Errors -Message "${FilePath}: property '$Name' is required."
        }

        return
    }

    if ($value -isnot [System.Array]) {
        Add-ValidationError -Errors $Errors -Message "${FilePath}: property '$Name' must be an array."
        return
    }

    if ($value.Count -lt $MinimumCount) {
        Add-ValidationError -Errors $Errors -Message "${FilePath}: property '$Name' must contain at least $MinimumCount item(s)."
        return
    }

    foreach ($item in $value) {
        if ($item -isnot [string] -or [string]::IsNullOrWhiteSpace($item)) {
            Add-ValidationError -Errors $Errors -Message "${FilePath}: property '$Name' must contain only non-empty strings."
            return
        }
    }
}

function Validate-Profile {
    param(
        [object]$Profile,
        [string]$FilePath,
        [System.Collections.Generic.List[string]]$Errors
    )

    $topLevelAllowed = @(
        'id',
        'displayName',
        'zoneName',
        'targetSkill',
        'enabledSkills',
        'baitName',
        'notes',
        'pacing',
        'thresholds',
        'guardrails'
    )

    $pacingAllowed = @('reactionFloorMs', 'reactionCeilingMs', 'biteTimeoutMs', 'lootTimeoutMs')
    $thresholdAllowed = @('rebaitAtOrBelow', 'maintenanceAtFreeSlotsOrBelow', 'maxRecoveryAttempts')
    $guardrailAllowed = @('pauseOnCombat', 'pauseOnBridgeLoss', 'recoverOnDrift')

    Test-AllowedProperties -Object $Profile -Allowed $topLevelAllowed -Context $FilePath -Errors $Errors

    Test-RequiredStringProperty -Object $Profile -Name 'id' -FilePath $FilePath -Errors $Errors
    Test-RequiredStringProperty -Object $Profile -Name 'displayName' -FilePath $FilePath -Errors $Errors
    Test-RequiredStringProperty -Object $Profile -Name 'zoneName' -FilePath $FilePath -Errors $Errors
    Test-RequiredStringProperty -Object $Profile -Name 'targetSkill' -FilePath $FilePath -Errors $Errors

    $profileId = Get-PropertyValue -Object $Profile -Name 'id'
    if ($profileId -is [string] -and $profileId -notmatch '^[a-z0-9-]+$') {
        Add-ValidationError -Errors $Errors -Message "${FilePath}: property 'id' must match ^[a-z0-9-]+$."
    }

    Test-StringArrayProperty -Object $Profile -Name 'enabledSkills' -FilePath $FilePath -MinimumCount 1 -Required $true -Errors $Errors
    Test-StringArrayProperty -Object $Profile -Name 'notes' -FilePath $FilePath -MinimumCount 0 -Required $false -Errors $Errors
    Test-OptionalStringProperty -Object $Profile -Name 'baitName' -FilePath $FilePath -Errors $Errors

    $pacing = Get-PropertyValue -Object $Profile -Name 'pacing'
    if ($null -eq $pacing -or ($pacing -isnot [psobject] -and $pacing -isnot [System.Collections.IDictionary])) {
        Add-ValidationError -Errors $Errors -Message "${FilePath}: property 'pacing' must be an object."
    }
    else {
        Test-AllowedProperties -Object $pacing -Allowed $pacingAllowed -Context "${FilePath}.pacing" -Errors $Errors
        foreach ($property in $pacingAllowed) {
            Test-IntegerProperty -Object $pacing -Name $property -FilePath "${FilePath}.pacing" -Minimum 0 -Errors $Errors
        }

        $floor = Get-PropertyValue -Object $pacing -Name 'reactionFloorMs'
        $ceiling = Get-PropertyValue -Object $pacing -Name 'reactionCeilingMs'
        if ($null -ne $floor -and $null -ne $ceiling) {
            try {
                if ([double]$ceiling -lt [double]$floor) {
                    Add-ValidationError -Errors $Errors -Message "${FilePath}.pacing: reactionCeilingMs must be greater than or equal to reactionFloorMs."
                }
            }
            catch {
                # Individual integer validation already reports non-numeric values.
            }
        }
    }

    $thresholds = Get-PropertyValue -Object $Profile -Name 'thresholds'
    if ($null -eq $thresholds -or ($thresholds -isnot [psobject] -and $thresholds -isnot [System.Collections.IDictionary])) {
        Add-ValidationError -Errors $Errors -Message "${FilePath}: property 'thresholds' must be an object."
    }
    else {
        Test-AllowedProperties -Object $thresholds -Allowed $thresholdAllowed -Context "${FilePath}.thresholds" -Errors $Errors
        foreach ($property in $thresholdAllowed) {
            Test-IntegerProperty -Object $thresholds -Name $property -FilePath "${FilePath}.thresholds" -Minimum 0 -Errors $Errors
        }
    }

    $guardrails = Get-PropertyValue -Object $Profile -Name 'guardrails'
    if ($null -eq $guardrails -or ($guardrails -isnot [psobject] -and $guardrails -isnot [System.Collections.IDictionary])) {
        Add-ValidationError -Errors $Errors -Message "${FilePath}: property 'guardrails' must be an object."
    }
    else {
        Test-AllowedProperties -Object $guardrails -Allowed $guardrailAllowed -Context "${FilePath}.guardrails" -Errors $Errors
        foreach ($property in $guardrailAllowed) {
            Test-BoolProperty -Object $guardrails -Name $property -FilePath "${FilePath}.guardrails" -Errors $Errors
        }
    }
}

if (-not (Test-Path -LiteralPath $ProfilesDirectory)) {
    throw "Profiles directory not found: $ProfilesDirectory"
}

$resolvedProfilesDirectory = (Resolve-Path -LiteralPath $ProfilesDirectory).Path
$files = @(Get-ChildItem -LiteralPath $resolvedProfilesDirectory -Filter '*.json' -File | Sort-Object Name)

if ($files.Count -eq 0) {
    throw "No profile JSON files found in $resolvedProfilesDirectory"
}

$errors = [System.Collections.Generic.List[string]]::new()
$ids = @{}

foreach ($file in $files) {
    try {
        $profile = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json -Depth 32 -AsHashtable
    }
    catch {
        Add-ValidationError -Errors $errors -Message "$($file.FullName): unable to parse JSON. $($_.Exception.Message)"
        continue
    }

    if ($null -eq $profile) {
        Add-ValidationError -Errors $errors -Message "$($file.FullName): profile JSON was empty."
        continue
    }

    Validate-Profile -Profile $profile -FilePath $file.FullName -Errors $errors

    $profileId = Get-PropertyValue -Object $profile -Name 'id'
    if ($profileId -is [string] -and -not [string]::IsNullOrWhiteSpace($profileId)) {
        if ($ids.ContainsKey($profileId)) {
            Add-ValidationError -Errors $errors -Message "$($file.FullName): duplicate profile id '$profileId' already used by '$($ids[$profileId])'."
        }
        else {
            $ids[$profileId] = $file.FullName
        }
    }
}

if ($errors.Count -gt 0) {
    foreach ($errorMessage in $errors) {
        Write-Error $errorMessage
    }

    exit 1
}

Write-Host "Validated $($files.Count) profile file(s) in $resolvedProfilesDirectory."
