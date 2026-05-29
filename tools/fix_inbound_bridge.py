"""Apply clipboard-based inbound command bridge to autofish_helper.py.

Changes:
1. Add _write_clipboard_text() after _foreground_send_ctrl_c
2. Add _foreground_send_ctrl_v() after _write_clipboard_text
3. Rewrite run_write_addon_command() to use clipboard transport
4. Remove _inject_inbound_command() function
5. Update subparser to require --pid/--hwnd instead of --saved-vars-path
"""

import re


def main():
    path = "tools/autofish-helper-py/autofish_helper.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    edits = []

    # ----- Edit 1: Add _write_clipboard_text() after _foreground_send_ctrl_c -----
    # Find the end of _foreground_send_ctrl_c (the line return and blank line before run_write_addon_command)
    foreground_ctrl_c_end = content.find(
        "    time.sleep(0.1)\n\n\ndef run_write_addon_command"
    )
    if foreground_ctrl_c_end == -1:
        print("ERROR: Could not find _foreground_send_ctrl_c end")
        return 1

    clipboard_write_func = '''    time.sleep(0.1)


def _write_clipboard_text(text: str) -> bool:
    """Write text to the Windows clipboard using ctypes (stdlib).

    Opens the clipboard, empties it, sets the text as CF_UNICODETEXT,
    and closes it. Returns True on success, False on failure.
    """
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    GMEM_MOVEABLE = 0x0002
    CF_UNICODETEXT = 13

    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        # Allocate global memory for the UTF-16 text
        wide = (text + "\\x00").encode("utf-16-le")
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(wide))
        if not handle:
            return False
        locked = kernel32.GlobalLock(handle)
        if locked:
            ctypes.memmove(locked, wide, len(wide))
            kernel32.GlobalUnlock(handle)
        user32.SetClipboardData(CF_UNICODETEXT, handle)
        return True
    finally:
        user32.CloseClipboard()


def _foreground_send_ctrl_v(hwnd: int) -> None:
    """Bring the Rift window to foreground and send Ctrl+V to paste.

    The Python helper writes structured JSON to the clipboard, then calls
    this function to paste into the addon's hidden EditBox. The Lua addon
    reads the paste in its next OnUpdateEnd cycle.
    """
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.2)
    KEYEVENTF_KEYUP = 0x0002
    # Ctrl down
    user32.keybd_event(VK_CONTROL, 0, 0, None)
    time.sleep(0.05)
    # V down
    user32.keybd_event(0x56, 0, 0, None)
    time.sleep(0.05)
    # V up
    user32.keybd_event(0x56, 0, KEYEVENTF_KEYUP, None)
    # Ctrl up
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, None)
    time.sleep(0.05)


def run_write_addon_command'''
    old = content[foreground_ctrl_c_end:]
    new = old.replace("    time.sleep(0.1)\n\n\ndef run_write_addon_command", clipboard_write_func, 1)
    content = content[:foreground_ctrl_c_end] + new

    if "clipboard_write_func" not in str(globals()):
        edits.append("Edit 1: Added _write_clipboard_text() and _foreground_send_ctrl_v()")

    # ----- Edit 2: Rewrite run_write_addon_command() to use clipboard transport -----
    # Find the function body between run_write_addon_command and _inject_inbound_command
    # We want to replace lines from "def run_write_addon_command" to the line before "def _inject_inbound_command"
    pattern = r'(def run_write_addon_command\(args: argparse\.Namespace\) -> int:.*?)(?=def _inject_inbound_command)'
    replacement = '''def run_write_addon_command(args: argparse.Namespace) -> int:
    """Write-addon-command CLI handler: sends a structured command to the
    in-game AutoFish addon via clipboard + Ctrl+V paste.

    The command is serialized as JSON, written to the Windows clipboard,
    and pasted into the addon's hidden EditBox. The Lua addon reads and
    processes it on the next OnUpdateEnd cycle.

    Supported command types: start, pause, resume, stop, sync_profile,
    request_snapshot.
    """
    VALID_TYPES = {"start", "pause", "resume", "stop", "sync_profile", "request_snapshot"}
    ct = args.command_type.lower()
    if ct not in VALID_TYPES:
        raise ValueError(
            f"Unknown command_type {args.command_type!r}. "
            f"Valid: {', '.join(sorted(VALID_TYPES))}"
        )

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    command: dict[str, Any] = {"commandType": ct, "issuedAtUtc": now_utc}
    if args.profile_id:
        command["profileId"] = args.profile_id
    if args.notes:
        command["notes"] = args.notes

    result: dict[str, Any] = {"command": command}
    dry_run = bool(args.dry_run)
    json_payload = json.dumps(command)

    if dry_run:
        result["clipboardWrite"] = "(dry-run, not written)"
        result["ctrlVPaste"] = "(dry-run, not sent)"
        result["dryRun"] = True
        print(json.dumps(result, indent=2))
        return 0

    # Write JSON command to clipboard
    clipboard_ok = _write_clipboard_text(json_payload)
    if not clipboard_ok:
        raise RuntimeError("Failed to write command JSON to Windows clipboard")
    result["clipboardWrite"] = "ok"

    # Paste into Rift via Ctrl+V
    pid = int(args.pid)
    hwnd = parse_hwnd(args.hwnd)
    target = validate_target(hwnd, pid, require_foreground=False)
    if target.get("isMinimized"):
        raise RuntimeError("Target is minimized; restore Rift before sending addon commands")
    _foreground_send_ctrl_v(hwnd)
    result["ctrlVPaste"] = {"hwnd": hwnd_hex(hwnd), "pid": pid}

    # Write JSON audit file
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    cmd_file = out_dir / f"{ct}-{ts}.json"
    cmd_file.write_text(json_payload, encoding="utf-8")
    result["commandFile"] = str(cmd_file.resolve())

    result["dryRun"] = False
    print(json.dumps(result, indent=2))
    return 0


'''

    content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)
    edits.append("Edit 2: Rewrote run_write_addon_command() with clipboard transport")

    # ----- Edit 3: Remove _inject_inbound_command function -----
    # Find from "def _inject_inbound_command" to the next function definition or blank line before read_addon_bridge
    pattern = r'def _inject_inbound_command\(sv_text: str, command: dict\[str, Any]\) -> tuple\[str, int\]:.*?(?=def read_addon_bridge)'
    content = re.sub(pattern, '', content, count=1, flags=re.DOTALL)
    edits.append("Edit 3: Removed _inject_inbound_command()")

    # Clean up any extra blank lines left by removal
    content = re.sub(r'\n{3,}', '\n\n', content)

    # ----- Edit 4: Update subparser to require --pid and --hwnd, remove --saved-vars-path -----
    old_subparser = '''    # --- write-addon-command ---
    write_addon_cmd_parser = subparsers.add_parser(
        "write-addon-command",
        help="Write a structured command to the in-game AutoFish addon via SavedVariables injection",
    )
    write_addon_cmd_parser.add_argument(
        "--command-type",
        required=True,
        help="Command type: start, pause, resume, stop, sync_profile, request_snapshot",
    )
    write_addon_cmd_parser.add_argument(
        "--profile-id",
        default=None,
        help="Profile ID for sync_profile command",
    )
    write_addon_cmd_parser.add_argument(
        "--notes",
        default=None,
        help="Optional human notes attached to the command",
    )
    write_addon_cmd_parser.add_argument(
        "--output-dir",
        default=".autofish-live/addon-commands",
        help="Directory for command audit files (default: .autofish-live/addon-commands)",
    )
    write_addon_cmd_parser.add_argument(
        "--saved-vars-path",
        default=None,
        help="Path to AutoFish.lua SavedVariables file for direct injection",
    )
    write_addon_cmd_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the command that would be written without modifying any files",
    )
    write_addon_cmd_parser.set_defaults(func=run_write_addon_command)'''

    new_subparser = '''    # --- write-addon-command ---
    write_addon_cmd_parser = subparsers.add_parser(
        "write-addon-command",
        help="Send a structured command to the in-game AutoFish addon via clipboard + Ctrl+V paste",
    )
    write_addon_cmd_parser.add_argument(
        "--pid",
        type=int,
        required=True,
        help="Rift process ID for Ctrl+V paste into the bridge EditBox",
    )
    write_addon_cmd_parser.add_argument(
        "--hwnd",
        required=True,
        help="Rift window handle, decimal or 0x hex, for Ctrl+V paste into the bridge EditBox",
    )
    write_addon_cmd_parser.add_argument(
        "--command-type",
        required=True,
        help="Command type: start, pause, resume, stop, sync_profile, request_snapshot",
    )
    write_addon_cmd_parser.add_argument(
        "--profile-id",
        default=None,
        help="Profile ID for sync_profile command",
    )
    write_addon_cmd_parser.add_argument(
        "--notes",
        default=None,
        help="Optional human notes attached to the command",
    )
    write_addon_cmd_parser.add_argument(
        "--output-dir",
        default=".autofish-live/addon-commands",
        help="Directory for command audit files (default: .autofish-live/addon-commands)",
    )
    write_addon_cmd_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the command that would be sent without modifying any files or sending keyboard input",
    )
    write_addon_cmd_parser.set_defaults(func=run_write_addon_command)'''

    if old_subparser in content:
        content = content.replace(old_subparser, new_subparser)
        edits.append("Edit 4: Updated subparser with --pid/--hwnd, removed --saved-vars-path")
    else:
        print("ERROR: Could not find old subparser text")
        return 1

    # Write the result
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    print("Applied edits:")
    for e in edits:
        print(f"  - {e}")

    # Verify syntax
    try:
        compile(content, path, "exec")
        print("Syntax OK")
        return 0
    except SyntaxError as e:
        print(f"Syntax error at line {e.lineno}: {e.msg}")
        return 1


if __name__ == "__main__":
    exit(main())
