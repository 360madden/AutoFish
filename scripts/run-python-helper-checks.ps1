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
    python -m py_compile tools/autofish-helper-py/tests/validate_doc_commands.py
    if ($LASTEXITCODE -ne 0) {
        throw 'Documented helper command validator compile failed.'
    }

    Write-Host 'Running Python helper smoke checks...'
    python tools/autofish-helper-py/tests/smoke_autofish_helper.py
    if ($LASTEXITCODE -ne 0) {
        throw 'Python helper smoke checks failed.'
    }

    Write-Host 'Validating documented helper commands...'
    python tools/autofish-helper-py/tests/validate_doc_commands.py
    if ($LASTEXITCODE -ne 0) {
        throw 'Documented helper command validation failed.'
    }

    Write-Host 'Checking helper command help surfaces...'
    python tools/autofish-helper-py/autofish_helper.py target-snapshot --help | Out-Null
    python tools/autofish-helper-py/autofish_helper.py target-snapshot --help | Select-String -Pattern 'require-readable' | Out-Null
    python tools/autofish-helper-py/autofish_helper.py session-plan --help | Out-Null
    python tools/autofish-helper-py/autofish_helper.py session-plan from-fan --help | Out-Null
    python tools/autofish-helper-py/autofish_helper.py session-plan explain --help | Out-Null
    python tools/autofish-helper-py/autofish_helper.py session-plan explain --help | Select-String -Pattern 'max-plan-age-minutes' | Out-Null
    python tools/autofish-helper-py/autofish_helper.py session-plan preflight --help | Out-Null
    python tools/autofish-helper-py/autofish_helper.py session-plan preflight --help | Select-String -Pattern 'ready-one-cast' | Out-Null
    python tools/autofish-helper-py/autofish_helper.py session-plan checklist --help | Out-Null
    python tools/autofish-helper-py/autofish_helper.py session-plan checklist --help | Select-String -Pattern 'proof-root' | Out-Null
    python tools/autofish-helper-py/autofish_helper.py session-plan stop-file --help | Out-Null
    python tools/autofish-helper-py/autofish_helper.py session-plan stop-file create --help | Out-Null
    python tools/autofish-helper-py/autofish_helper.py session-plan gates --help | Out-Null
    python tools/autofish-helper-py/autofish_helper.py session-plan gates --help | Select-String -Pattern 'stop-file-clear' | Out-Null
    python tools/autofish-helper-py/autofish_helper.py session-plan gates --help | Select-String -Pattern 'plan-fresh' | Out-Null
    python tools/autofish-helper-py/autofish_helper.py session-plan gates --help | Select-String -Pattern 'max-plan-age-minutes' | Out-Null
    python tools/autofish-helper-py/autofish_helper.py session-plan gates --help | Select-String -Pattern 'target-current' | Out-Null
    python tools/autofish-helper-py/autofish_helper.py session-plan gates --help | Select-String -Pattern 'target-foreground' | Out-Null
    python tools/autofish-helper-py/autofish_helper.py session-plan gates --help | Select-String -Pattern 'client-readable' | Out-Null
    python tools/autofish-helper-py/autofish_helper.py session-plan gates --help | Select-String -Pattern 'ready-one-cast' | Out-Null
    python tools/autofish-helper-py/autofish_helper.py session-plan gates --help | Select-String -Pattern 'confirmed-bounded-session' | Out-Null
    python tools/autofish-helper-py/autofish_helper.py signal-proof one-cast --help | Out-Null
    python tools/autofish-helper-py/autofish_helper.py signal-proof one-cast --help | Select-String -Pattern 'max-plan-age-minutes' | Out-Null
    python tools/autofish-helper-py/autofish_helper.py signal-proof one-cast --help | Select-String -Pattern 'allow-red-reticle-click' | Out-Null
    python tools/autofish-helper-py/autofish_helper.py signal-proof bounded-session --help | Out-Null
    python tools/autofish-helper-py/autofish_helper.py signal-proof bounded-session --help | Select-String -Pattern 'max-plan-age-minutes' | Out-Null
    python tools/autofish-helper-py/autofish_helper.py signal-proof bounded-session --help | Select-String -Pattern 'allow-red-reticle-click' | Out-Null
    python tools/autofish-helper-py/autofish_helper.py signal-proof fishability-fan --help | Out-Null
    python tools/autofish-helper-py/autofish_helper.py signal-proof fishability-fan-runbook --help | Out-Null
    python tools/autofish-helper-py/autofish_helper.py signal-proof decide --help | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Python helper help check failed.'
    }

    Write-Host 'Python helper checks passed.'
}
finally {
    Pop-Location
}
