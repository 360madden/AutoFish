"""AutoFish Python helper checks (replaces run-python-helper-checks.ps1).

Usage:
    python scripts/run_python_checks.py
"""

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
HELPER = REPO_ROOT / "tools" / "autofish-helper-py" / "autofish_helper.py"
SMOKE = REPO_ROOT / "tools" / "autofish-helper-py" / "tests" / "smoke_autofish_helper.py"
DOC_VALIDATE = REPO_ROOT / "tools" / "autofish-helper-py" / "tests" / "validate_doc_commands.py"
LUA_VALIDATE = REPO_ROOT / "tools" / "autofish-helper-py" / "tests" / "validate_lua_slash_commands.py"

PYTHON = sys.executable


def run(cmd: list[str], label: str) -> None:
    print(f"  {label}...")
    result = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FAILED ({label}):\n{result.stderr}\n{result.stdout}")
        sys.exit(1)


def check_help(args: list[str], grep: str | None = None, label: str | None = None) -> None:
    cmd = [PYTHON, str(HELPER)] + args + ["--help"]
    result = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FAILED (help {label or ' '.join(args)}):\n{result.stderr}")
        sys.exit(1)
    if grep and grep not in result.stdout:
        print(f"FAILED (help {label or ' '.join(args)} missing '{grep}'):\n{result.stdout[:500]}")
        sys.exit(1)


def main() -> int:
    print("=== AutoFish Python helper checks ===\n")
    errors = 0

    # Compile
    print("Compiling Python helper...")
    for path in [HELPER, DOC_VALIDATE, LUA_VALIDATE]:
        result = subprocess.run(
            [PYTHON, "-m", "py_compile", str(path)],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"  FAILED compile {path.name}: {result.stderr}")
            errors += 1
    if errors:
        print(f"\n{errors} compile error(s).")
        return 1
    print("  OK")

    # Smoke
    print("\nRunning smoke checks...")
    run([PYTHON, str(SMOKE)], "smoke_autofish_helper.py")

    # Doc validation
    print("\nValidating documented commands...")
    run([PYTHON, str(DOC_VALIDATE)], "validate_doc_commands.py")

    # Lua slash validation
    print("\nValidating Lua slash commands...")
    run([PYTHON, str(LUA_VALIDATE)], "validate_lua_slash_commands.py")

    # Help surfaces
    print("\nChecking help surfaces...")

    help_checks: list[tuple[list[str], str | None, str]] = [
        (["target-snapshot"], "require-readable", "target-snapshot"),
        (["doctor"], "session-plan", "doctor session-plan"),
        (["doctor"], "proof-root", "doctor proof-root"),
        (["doctor"], "fail-on", "doctor fail-on"),
        (["doctor"], "next-action-only", "doctor next-action-only"),
        (["doctor"], "refresh-summary", "doctor refresh-summary"),
        (["session-plan"], None, "session-plan"),
        (["session-plan", "from-fan"], "require-usable-facing", "from-fan"),
        (["session-plan", "explain"], "max-plan-age-minutes", "explain"),
        (["session-plan", "preflight"], "ready-one-cast", "preflight"),
        (["session-plan", "checklist"], "proof-root", "checklist"),
        (["session-plan", "doctor"], "proof-root", "session-plan doctor proof-root"),
        (["session-plan", "doctor"], "output-root", "session-plan doctor output-root"),
        (["session-plan", "stop-file"], None, "stop-file"),
        (["session-plan", "stop-file", "create"], None, "stop-file create"),
        (["session-plan", "gates"], "stop-file-clear", "gates stop-file-clear"),
        (["session-plan", "gates"], "plan-fresh", "gates plan-fresh"),
        (["session-plan", "gates"], "max-plan-age-minutes", "gates max-plan-age-minutes"),
        (["session-plan", "gates"], "target-current", "gates target-current"),
        (["session-plan", "gates"], "target-foreground", "gates target-foreground"),
        (["session-plan", "gates"], "client-readable", "gates client-readable"),
        (["session-plan", "gates"], "ready-one-cast", "gates ready-one-cast"),
        (["session-plan", "gates"], "confirmed-bounded-session", "gates confirmed-bounded-session"),
        (["signal-proof", "one-cast"], "max-plan-age-minutes", "one-cast max-plan-age-minutes"),
        (["signal-proof", "one-cast"], "allow-red-reticle-click", "one-cast allow-red-reticle-click"),
        (["signal-proof", "bounded-session"], "max-plan-age-minutes", "bounded-session"),
        (["signal-proof", "bounded-session"], "allow-red-reticle-click", "bounded-session red-reticle"),
        (["signal-proof", "fishability-fan"], "facing-manifest", "fishability-fan"),
        (["signal-proof", "fishability-fan-runbook"], None, "fishability-fan-runbook"),
        (["signal-proof", "chromalink"], None, "chromalink"),
        (["signal-proof", "coordinate-crosscheck"], None, "coordinate-crosscheck"),
        (["signal-proof", "facing-delta"], None, "facing-delta"),
        (["signal-proof", "facing-from-coords"], "before-line", "facing-from-coords"),
        (["signal-proof", "slash"], "default-proof-pack", "slash"),
        (["signal-proof", "doctor"], "decision-register", "signal-proof doctor"),
        (["signal-proof", "decide"], None, "signal-proof decide"),
    ]

    for args, grep, label in help_checks:
        check_help(args, grep, label)
    print("  OK")

    print("\n=== Python helper checks passed ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
