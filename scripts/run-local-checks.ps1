param()

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $repoRoot

try {
    function Invoke-CheckedCommand {
        param(
            [Parameter(Mandatory)]
            [scriptblock]$Command,
            [Parameter(Mandatory)]
            [string]$FailureMessage
        )

        & $Command
        if ($LASTEXITCODE -ne 0) {
            throw $FailureMessage
        }
    }

    Write-Host 'Building .NET solution...'
    Invoke-CheckedCommand -Command { dotnet build AutoFish.sln --configuration Release } -FailureMessage 'dotnet build failed.'

    Write-Host 'Validating helper-side profile loading...'
    Invoke-CheckedCommand -Command { dotnet run --project src/AutoFish.App/AutoFish.App.csproj --configuration Release --no-build -- --validate-profiles } -FailureMessage 'Helper-side profile loading validation failed.'

    Write-Host 'Validating profiles...'
    & (Join-Path $PSScriptRoot 'validate-profiles.ps1')

    Write-Host 'Running Lua syntax + smoke checks...'
    $env:LUA_PATH = '.\lua\?.lua;.\lua\?\init.lua;.\lua\?\?.lua;' + $env:LUA_PATH
    Invoke-CheckedCommand -Command { luac -p lua/AutoFish/AutoFishAddon.lua } -FailureMessage 'Lua syntax validation failed.'
    Invoke-CheckedCommand -Command { lua scripts/lua-smoke-tests.lua } -FailureMessage 'Lua smoke tests failed.'

    Write-Host 'All local checks passed.'
}
finally {
    Pop-Location
}
