from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
MAIN_LUA = REPO_ROOT / "lua" / "AutoFish" / "Main.lua"
LUA_README = REPO_ROOT / "lua" / "AutoFish" / "README.md"

DOCUMENTED_COMMANDS = (
    "status",
    "coords",
    "bags",
    "inventory",
    "invproof",
    "pole",
    "abilities",
    "api",
    "apicompact",
    "apis",
    "signals",
    "events",
    "proof",
    "observe",
    "trace",
    "snapshot",
    "help",
)

DISPATCH_PATTERNS = {
    "help": ('command == "help"',),
    "status": ('command == "status"',),
    "coords": ('command == "coords"',),
    "bags": ('command == "bags"',),
    "inventory": ('command == "inventory"',),
    "invproof": ('command == "invproof"',),
    "pole": ('command == "pole"',),
    "abilities": ('command == "abilities"',),
    "api": ('command == "api"',),
    "apicompact": ('command == "apicompact"',),
    "apis": ('command == "apis"',),
    "signals": ('command == "signals"',),
    "events": ('command == "events"',),
    "proof": ('command == "proof"',),
    "observe": ('command == "observe"',),
    "trace": ('command == "trace"',),
    "snapshot": ('command == "snapshot"',),
}

CALL_PATTERNS = {
    "proof": "AutoFishLive.PrintProofPack()",
}


def main() -> int:
    main_text = MAIN_LUA.read_text(encoding="utf-8")
    readme_text = LUA_README.read_text(encoding="utf-8")
    errors: list[str] = []

    for command in DOCUMENTED_COMMANDS:
        slash_text = f"/autofish {command}"
        if slash_text not in main_text:
            errors.append(f"Main.lua help output is missing {slash_text}")
        if slash_text not in readme_text:
            errors.append(f"lua/AutoFish/README.md is missing {slash_text}")

        patterns = DISPATCH_PATTERNS.get(command, ())
        if patterns and not any(pattern in main_text for pattern in patterns):
            errors.append(f"Main.lua slash dispatcher is missing command == \"{command}\"")

    for command, pattern in CALL_PATTERNS.items():
        if pattern not in main_text:
            errors.append(f"Main.lua slash dispatcher does not call expected handler for {command}: {pattern}")

    if errors:
        print("Lua slash command surface validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Lua slash command surface is documented and dispatchable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
