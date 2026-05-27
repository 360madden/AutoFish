"""AutoFish addon deployer (replaces deploy-addon.ps1).

Copies lua/AutoFish to the Rift Interface/Addons directory.

Usage:
    python scripts/deploy_addon.py
    python scripts/deploy_addon.py --dest "C:\\Users\\...\\Documents\\RIFT\\Interface\\Addons"
"""

import argparse
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
ADDON_SOURCE = REPO_ROOT / "lua" / "AutoFish"

DEFAULT_CANDIDATES = [
    Path.home() / "Documents" / "RIFT" / "Interface" / "Addons",
    Path.home() / "Documents" / "RIFT" / "Interface" / "AddOns",
    Path.home() / "OneDrive" / "Documents" / "RIFT" / "Interface" / "Addons",
    Path.home() / "OneDrive" / "Documents" / "RIFT" / "Interface" / "AddOns",
]


def find_addon_dirs() -> list[Path]:
    found: list[Path] = []
    for candidate in DEFAULT_CANDIDATES:
        resolved = candidate.resolve()
        if resolved.is_dir() and resolved not in found:
            found.append(resolved)
    return found


def deploy(dest_roots: list[Path]) -> None:
    if not ADDON_SOURCE.is_dir():
        print(f"ERROR: Addon source folder not found: {ADDON_SOURCE}")
        sys.exit(1)

    for root in dest_roots:
        target = root / "AutoFish"
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            ADDON_SOURCE, target,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("*.git*", "__pycache__"),
        )
        print(f"[OK] Deployed AutoFish addon to {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy AutoFish Lua addon to Rift addons directory")
    parser.add_argument(
        "--dest", action="append", dest="dest_roots",
        help="Rift Interface/Addons directory (repeatable)",
    )
    args = parser.parse_args()

    if args.dest_roots:
        dest_roots = [Path(d).resolve() for d in args.dest_roots]
    else:
        dest_roots = find_addon_dirs()

    if not dest_roots:
        print("ERROR: No Rift Interface/Addons directory found. Pass --dest explicitly.")
        print("Candidates checked:")
        for c in DEFAULT_CANDIDATES:
            print(f"  {c}")
        return 1

    deploy(dest_roots)
    return 0


if __name__ == "__main__":
    sys.exit(main())
