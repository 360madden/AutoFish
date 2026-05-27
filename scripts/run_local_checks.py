"""AutoFish local checks (replaces run-local-checks.ps1).

Usage:
    python scripts/run_local_checks.py              # Full: .NET + Python + Lua
    python scripts/run_local_checks.py --skip-lua   # Skip Lua checks
"""

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


def run(cmd: list[str], label: str, cwd: str | None = None, env: dict | None = None) -> None:
    print(f"\n=== {label} ===")
    result = subprocess.run(
        cmd,
        cwd=cwd or str(REPO_ROOT),
        env=env,
        shell=False,
    )
    if result.returncode != 0:
        print(f"FAILED: {label} (exit code {result.returncode})")
        sys.exit(1)
    print(f"OK: {label}")


def check_command(name: str, hint: str) -> None:
    import shutil
    if shutil.which(name) is None:
        print(f"FAILED: Required command '{name}' was not found on PATH. {hint}")
        sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all AutoFish local checks")
    parser.add_argument("--skip-lua", action="store_true", help="Skip Lua syntax and smoke checks")
    args = parser.parse_args()

    print("=== AutoFish local checks ===")

    # .NET build
    run(["dotnet", "build", "AutoFish.sln", "--configuration", "Release"], ".NET build")

    # Profile validation (C#)
    run(
        [
            "dotnet", "run",
            "--project", str(REPO_ROOT / "src" / "AutoFish.App" / "AutoFish.App.csproj"),
            "--configuration", "Release", "--no-build",
            "--", "--validate-profiles",
        ],
        "Profile validation (C#)",
    )

    # Python checks
    python_checks = REPO_ROOT / "scripts" / "run_python_checks.py"
    run([PYTHON, str(python_checks)], "Python helper checks")

    if args.skip_lua:
        print("\n=== Skipping Lua checks (--skip-lua) ===")
        print("All requested local checks passed.")
        return 0

    # Lua checks
    check_command("luac", "Install Lua/luac or rerun with --skip-lua.")
    check_command("lua", "Install Lua/lua or rerun with --skip-lua.")

    lua_path = ";".join([
        str(REPO_ROOT / "lua" / "?.lua"),
        str(REPO_ROOT / "lua" / "?" / "init.lua"),
        str(REPO_ROOT / "lua" / "?" / "?.lua"),
        "",
    ])
    lua_env = {**__import__("os").environ, "LUA_PATH": lua_path}

    run(
        ["luac", "-p", str(REPO_ROOT / "lua" / "AutoFish" / "AutoFishAddon.lua")],
        "Lua syntax check",
    )

    run(
        ["lua", str(REPO_ROOT / "scripts" / "lua-smoke-tests.lua")],
        "Lua smoke tests",
        env=lua_env,
    )

    print("\n=== All local checks passed ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
