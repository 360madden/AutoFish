param()

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $repoRoot

try {
    Write-Host 'Compiling Python helper...'
    python -m py_compile tools/autofish-helper-py/autofish_helper.py
    if ($LASTEXITCODE -ne 0) {
        throw 'Python helper compile failed.'
    }

    Write-Host 'Running Python helper smoke checks...'
    python tools/autofish-helper-py/tests/smoke_autofish_helper.py
    if ($LASTEXITCODE -ne 0) {
        throw 'Python helper smoke checks failed.'
    }

    Write-Host 'Checking helper command help surfaces...'
    python tools/autofish-helper-py/autofish_helper.py session-plan --help | Out-Null
    python tools/autofish-helper-py/autofish_helper.py signal-proof one-cast --help | Out-Null
    python tools/autofish-helper-py/autofish_helper.py signal-proof bounded-session --help | Out-Null
    python tools/autofish-helper-py/autofish_helper.py signal-proof fishability-fan --help | Out-Null
    python tools/autofish-helper-py/autofish_helper.py signal-proof fishability-fan-runbook --help | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Python helper help check failed.'
    }

    Write-Host 'Python helper checks passed.'
}
finally {
    Pop-Location
}
