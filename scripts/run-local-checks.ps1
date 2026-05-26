param(
    [switch]$SkipLuaChecks
)

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

    function Assert-CommandAvailable {
        param(
            [Parameter(Mandatory)]
            [string]$Name,
            [Parameter(Mandatory)]
            [string]$InstallHint
        )

        if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
            throw "Required command '$Name' was not found on PATH. $InstallHint"
        }
    }

    Write-Host 'Building .NET solution...'
    Invoke-CheckedCommand -Command { dotnet build AutoFish.sln --configuration Release } -FailureMessage 'dotnet build failed.'

    Write-Host 'Validating helper-side profile loading...'
    Invoke-CheckedCommand -Command { dotnet run --project src/AutoFish.App/AutoFish.App.csproj --configuration Release --no-build -- --validate-profiles } -FailureMessage 'Helper-side profile loading validation failed.'

    Write-Host 'Validating profiles...'
    & (Join-Path $PSScriptRoot 'validate-profiles.ps1')

    Write-Host 'Running Python helper checks...'
    & (Join-Path $PSScriptRoot 'run-python-helper-checks.ps1')

    if ($SkipLuaChecks) {
        Write-Host 'Skipping Lua syntax + smoke checks because -SkipLuaChecks was supplied.'
        Write-Host 'All requested local checks passed.'
        return
    }

    Write-Host 'Running Lua syntax + smoke checks...'
    Assert-CommandAvailable -Name 'luac' -InstallHint "Install Lua/luac or rerun with -SkipLuaChecks only when intentionally validating non-Lua helper changes."
    Assert-CommandAvailable -Name 'lua' -InstallHint "Install Lua/lua or rerun with -SkipLuaChecks only when intentionally validating non-Lua helper changes."
    $env:LUA_PATH = '.\lua\?.lua;.\lua\?\init.lua;.\lua\?\?.lua;' + $env:LUA_PATH
    Invoke-CheckedCommand -Command { luac -p lua/AutoFish/AutoFishAddon.lua } -FailureMessage 'Lua syntax validation failed.'
    Invoke-CheckedCommand -Command { lua scripts/lua-smoke-tests.lua } -FailureMessage 'Lua smoke tests failed.'

    Write-Host 'All local checks passed.'
}
finally {
    Pop-Location
}
