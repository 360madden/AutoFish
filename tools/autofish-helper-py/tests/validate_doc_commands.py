from __future__ import annotations

from pathlib import Path
import re
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]

HELPER_COMMAND_RE = re.compile(r"autofish_helper\.py(?P<tail>[^`\r\n]*)")

DOC_GLOBS = (
    "README.md",
    "tools/autofish-helper-py/README.md",
    "docs/**/*.md",
)

SKIPPED_DOC_PARTS = {
    "research",
}

TOP_LEVEL_COMMANDS = {
    "target-snapshot",
    "session-plan",
    "signal-proof",
}

SESSION_PLAN_COMMANDS = {
    "create",
    "from-fan",
    "show",
    "explain",
    "preflight",
    "checklist",
    "stop-file",
    "gates",
    "runbook",
}

STOP_FILE_ACTIONS = {
    "status",
    "create",
    "clear",
}

SIGNAL_PROOF_COMMANDS = {
    "reticle",
    "one-cast",
    "bounded-session",
    "fishability-fan",
    "fishability-fan-runbook",
    "chromalink",
    "coordinate-crosscheck",
    "facing-delta",
    "log",
    "layout",
    "slash",
    "audio",
    "summarize",
    "decide",
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


def validate_invocation(tokens: list[str]) -> list[str]:
    errors: list[str] = []
    if not tokens:
        return ["missing helper command after autofish_helper.py"]

    for command in alternatives(tokens[0]):
        if command not in TOP_LEVEL_COMMANDS:
            errors.append(f"unknown top-level helper command '{command}'")
            continue
        if command == "target-snapshot":
            continue
        if command == "session-plan":
            if len(tokens) < 2:
                errors.append("session-plan command is missing a subcommand")
                continue
            for subcommand in alternatives(tokens[1]):
                if subcommand not in SESSION_PLAN_COMMANDS:
                    errors.append(f"unknown session-plan subcommand '{subcommand}'")
                    continue
                if subcommand == "stop-file" and len(tokens) >= 3:
                    for action in alternatives(tokens[2]):
                        if action not in STOP_FILE_ACTIONS:
                            errors.append(f"unknown session-plan stop-file action '{action}'")
            continue
        if command == "signal-proof":
            if len(tokens) < 2:
                errors.append("signal-proof command is missing a subcommand")
                continue
            for subcommand in alternatives(tokens[1]):
                if subcommand not in SIGNAL_PROOF_COMMANDS:
                    errors.append(f"unknown signal-proof subcommand '{subcommand}'")
    return errors


def validate_markdown_text(label: str, text: str) -> list[str]:
    failures: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in HELPER_COMMAND_RE.finditer(line):
            tokens = command_tokens(match.group("tail"))
            errors = validate_invocation(tokens)
            for error in errors:
                failures.append(f"{label}:{line_number}: {error}: {' '.join(tokens) or '<none>'}")
    return failures


def main() -> int:
    failures: list[str] = []
    for path in iter_doc_paths():
        relative_path = path.relative_to(REPO_ROOT)
        failures.extend(validate_markdown_text(str(relative_path), path.read_text(encoding="utf-8")))

    if failures:
        print("Documented AutoFish helper command validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("Documented AutoFish helper commands are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
