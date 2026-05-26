from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
HELPER_PATH = REPO_ROOT / "tools" / "autofish-helper-py" / "autofish_helper.py"

HELPER_COMMAND_RE = re.compile(r"autofish_helper\.py(?P<tail>[^`\r\n]*)")

DOC_GLOBS = (
    "README.md",
    "tools/autofish-helper-py/README.md",
    "docs/**/*.md",
)

SKIPPED_DOC_PARTS = {
    "research",
}


def iter_doc_paths() -> list[Path]:
    seen: set[Path] = set()
    paths: list[Path] = []
    for pattern in DOC_GLOBS:
        for path in REPO_ROOT.glob(pattern):
            if not path.is_file():
                continue
            relative_parts = path.relative_to(REPO_ROOT).parts
            if any(part in SKIPPED_DOC_PARTS for part in relative_parts):
                continue
            if path in seen:
                continue
            seen.add(path)
            paths.append(path)
    return sorted(paths)


def clean_token(token: str) -> str:
    return token.strip().strip("`'\".,;:()[]{}")


def command_tokens(tail: str) -> list[str]:
    tokens: list[str] = []
    for raw_token in tail.split():
        token = clean_token(raw_token)
        if not token:
            continue
        if token == "\\":
            break
        if token == "`":
            break
        if token.startswith("--"):
            break
        if token.startswith("<") or token.startswith("$"):
            break
        tokens.append(token)
        if len(tokens) >= 3:
            break
    return tokens


def alternatives(token: str) -> list[str]:
    return [part for part in token.split("|") if part]


def load_helper_module() -> Any:
    spec = importlib.util.spec_from_file_location("autofish_helper_for_doc_validation", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load helper module from {HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parser_subcommands(parser: Any) -> dict[str, Any]:
    for action in getattr(parser, "_actions", []):
        choices = getattr(action, "choices", None)
        if isinstance(choices, dict) and choices and all(hasattr(choice, "_actions") for choice in choices.values()):
            return choices
    return {}


def build_command_surface(helper_module: Any | None = None) -> dict[str, dict[str, Any]]:
    helper = helper_module or load_helper_module()
    top_level = parser_subcommands(helper.build_parser())
    surface: dict[str, dict[str, Any]] = {command: {} for command in top_level}

    session_plan = top_level.get("session-plan")
    if session_plan is not None:
        session_commands = parser_subcommands(session_plan)
        surface["session-plan"] = {command: {} for command in session_commands}
        stop_file = session_commands.get("stop-file")
        if stop_file is not None:
            surface["session-plan"]["stop-file"] = {action: {} for action in parser_subcommands(stop_file)}

    signal_proof = top_level.get("signal-proof")
    if signal_proof is not None:
        surface["signal-proof"] = {command: {} for command in parser_subcommands(signal_proof)}

    return surface


def validate_invocation(tokens: list[str], command_surface: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if not tokens:
        return ["missing helper command after autofish_helper.py"]

    for command in alternatives(tokens[0]):
        if command not in command_surface:
            errors.append(f"unknown top-level helper command '{command}'")
            continue
        if command == "target-snapshot":
            continue
        if command == "session-plan":
            if len(tokens) < 2:
                errors.append("session-plan command is missing a subcommand")
                continue
            for subcommand in alternatives(tokens[1]):
                if subcommand not in command_surface["session-plan"]:
                    errors.append(f"unknown session-plan subcommand '{subcommand}'")
                    continue
                if subcommand == "stop-file" and len(tokens) >= 3:
                    for action in alternatives(tokens[2]):
                        if action not in command_surface["session-plan"]["stop-file"]:
                            errors.append(f"unknown session-plan stop-file action '{action}'")
            continue
        if command == "signal-proof":
            if len(tokens) < 2:
                errors.append("signal-proof command is missing a subcommand")
                continue
            for subcommand in alternatives(tokens[1]):
                if subcommand not in command_surface["signal-proof"]:
                    errors.append(f"unknown signal-proof subcommand '{subcommand}'")
    return errors


def validate_markdown_text(
    label: str,
    text: str,
    command_surface: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    surface = command_surface or build_command_surface()
    failures: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in HELPER_COMMAND_RE.finditer(line):
            tokens = command_tokens(match.group("tail"))
            errors = validate_invocation(tokens, surface)
            for error in errors:
                failures.append(f"{label}:{line_number}: {error}: {' '.join(tokens) or '<none>'}")
    return failures


def main() -> int:
    command_surface = build_command_surface()
    failures: list[str] = []
    for path in iter_doc_paths():
        relative_path = path.relative_to(REPO_ROOT)
        failures.extend(validate_markdown_text(str(relative_path), path.read_text(encoding="utf-8"), command_surface))

    if failures:
        print("Documented AutoFish helper command validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("Documented AutoFish helper commands are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
