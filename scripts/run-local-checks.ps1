param()

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $repoRoot

try {
    Write-Host 'Building .NET solution...'
    dotnet build AutoFish.sln --configuration Release

    Write-Host 'Validating profiles...'
    & (Join-Path $PSScriptRoot 'validate-profiles.ps1')

    Write-Host 'Running Lua syntax + smoke checks...'
    $env:LUA_PATH = '.\lua\?.lua;.\lua\?\init.lua;.\lua\?\?.lua;' + $env:LUA_PATH
    luac -p lua/AutoFish/AutoFishAddon.lua
    lua -e "package.path='lua/?.lua;lua/?/init.lua;lua/?/?.lua;' .. package.path; local Addon = require('AutoFish.AutoFishAddon'); local addon = Addon.new({ baitCapacity = 15, inventoryCapacity = 10, rebaitAtOrBelow = 3, maintenanceAtFreeSlotsOrBelow = 1 }, {}); local decision, vm = addon:onObservation({characterName='Tester', inGame=true, nearWater=true, inCombat=false, inventoryFull=false, baitAvailable=true, biteDetected=false, lootReady=false, lineCast=false, canCast=true}); assert(decision.action == 'cast_line'); assert(vm.mode == 'casting'); print('lua smoke ok')"

    Write-Host 'All local checks passed.'
}
finally {
    Pop-Location
}
