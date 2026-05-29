"""Replace read_addon_bridge with clipboard-based approach using Windows clipboard APIs.
The Lua addon writes bridge data to a hidden EditBox; the helper reads it via Ctrl+A/Ctrl+C + clipboard."""
import sys

filepath = 'tools/autofish-helper-py/autofish_helper.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.splitlines(keepends=True)

edits = []

# ---- Edit 1: Add clipboard constants after VK_MENU (line with VK_MENU = 0x12) ----
for i, line in enumerate(lines):
    if 'VK_MENU = 0x12' in line:
        insert_lines = [
            'CF_TEXT = 1\n',
            'CF_UNICODETEXT = 13\n',
        ]
        for idx, bline in enumerate(reversed(insert_lines)):
            lines.insert(i + 1, bline)
        edits.append(f'Edit 1: Added clipboard constants after line {i+1}')
        break

# ---- Edit 2: Add clipboard helper functions before def read_addon_bridge ----
for i, line in enumerate(lines):
    if line.strip().startswith('def read_addon_bridge('):
        clip_funcs = (
            '\n'
            'def _read_clipboard_text() -> str | None:\n'
            '    """Read text from the Windows clipboard using ctypes (stdlib).\n'
            '\n'
            '    Returns the clipboard text as a UTF-8 string, or None if no text is\n'
            '    available or the clipboard cannot be opened.\n'
            '    """\n'
            '    user32 = ctypes.windll.user32\n'
            '    if not user32.OpenClipboard(None):\n'
            '        return None\n'
            '    try:\n'
            '        # Try Unicode first\n'
            '        handle = user32.GetClipboardData(CF_UNICODETEXT)\n'
            '        if handle:\n'
            '            return ctypes.c_wchar_p(handle).value\n'
            '        # Fall back to ANSI\n'
            '        handle = user32.GetClipboardData(CF_TEXT)\n'
            '        if handle:\n'
            '            raw = ctypes.c_char_p(handle).value\n'
            '            if raw:\n'
            '                return raw.decode("utf-8", errors="replace")\n'
            '        return None\n'
            '    finally:\n'
            '        user32.CloseClipboard()\n'
            '\n'
            '\n'
            'def _foreground_send_select_all(hwnd: int) -> None:\n'
            '    """Bring the Rift window to foreground and send Ctrl+A to select all.\n'
            '\n'
            '    The addon\'s hidden EditBox must have focus-like selection behavior.\n'
            '    Does NOT check for minimized windows — caller should validate first.\n'
            '    """\n'
            '    user32.SetForegroundWindow(hwnd)\n'
            '    time.sleep(0.2)\n'
            '    KEYEVENTF_KEYUP = 0x0002\n'
            '    # Ctrl down\n'
            '    user32.keybd_event(VK_CONTROL, 0, 0, None)\n'
            '    time.sleep(0.05)\n'
            '    # A down\n'
            '    user32.keybd_event(0x41, 0, 0, None)\n'
            '    time.sleep(0.05)\n'
            '    # A up\n'
            '    user32.keybd_event(0x41, 0, KEYEVENTF_KEYUP, None)\n'
            '    # Ctrl up\n'
            '    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, None)\n'
            '    time.sleep(0.1)\n'
            '\n'
            '\n'
            'def _foreground_send_ctrl_c(hwnd: int) -> None:\n'
            '    """Bring the Rift window to foreground and send Ctrl+C to copy to clipboard.\n'
            '    """\n'
            '    user32.SetForegroundWindow(hwnd)\n'
            '    time.sleep(0.2)\n'
            '    KEYEVENTF_KEYUP = 0x0002\n'
            '    # Ctrl down\n'
            '    user32.keybd_event(VK_CONTROL, 0, 0, None)\n'
            '    time.sleep(0.05)\n'
            '    # C down\n'
            '    user32.keybd_event(0x43, 0, 0, None)\n'
            '    time.sleep(0.05)\n'
            '    # C up\n'
            '    user32.keybd_event(0x43, 0, KEYEVENTF_KEYUP, None)\n'
            '    # Ctrl up\n'
            '    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, None)\n'
            '    time.sleep(0.1)\n'
            '\n'
            '\n'
        )
        for idx, bline in enumerate(reversed(clip_funcs)):
            lines.insert(i, bline)
        edits.append(f'Edit 2: Added clipboard helper functions before line {i+1}')
        break

# ---- Edit 3: Replace read_addon_bridge function ----
new_read_addon_bridge = '''def read_addon_bridge(hwnd: int, pid: int) -> dict[str, Any]:
    """Read the addon's bridge snapshot via Windows clipboard relay.

    The Lua addon writes structured envelope JSON to a hidden EditBox.
    This helper brings the Rift window to foreground, sends Ctrl+A/Ctrl+C
    to copy the EditBox content to the clipboard, then reads and parses it.

    Returns a dict with keys: available, snapshot, messageType, etc.
    On failure returns available=False with a reason string.
    """
    try:
        _foreground_send_select_all(hwnd)
        _foreground_send_ctrl_c(hwnd)
    except Exception as exc:
        return {
            "available": False,
            "reason": f"failed to send keyboard input: {exc}",
        }

    text = _read_clipboard_text()
    if not text:
        return {
            "available": False,
            "reason": "clipboard was empty after Ctrl+A/Ctrl+C — EditBox may not have focus or content",
        }

    # Try parsing as a single JSON envelope (preferred) or JSONL
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            payload = parsed.get("payload") if isinstance(parsed.get("payload"), dict) else {}
            return {
                "available": True,
                "source": "clipboard-single",
                "messageType": parsed.get("messageType", "unknown"),
                "contractVersion": parsed.get("contractVersion", "unknown"),
                "issuedAtUtc": parsed.get("issuedAtUtc", "unknown"),
                "snapshot": payload,
            }
    except json.JSONDecodeError:
        pass

    # Try JSONL (last line wins)
    last_envelope = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
            last_envelope = parsed
        except json.JSONDecodeError:
            continue

    if isinstance(last_envelope, dict):
        payload = last_envelope.get("payload") if isinstance(last_envelope.get("payload"), dict) else {}
        return {
            "available": True,
            "source": "clipboard-jsonl",
            "messageType": last_envelope.get("messageType", "unknown"),
            "contractVersion": last_envelope.get("contractVersion", "unknown"),
            "issuedAtUtc": last_envelope.get("issuedAtUtc", "unknown"),
            "snapshot": payload,
        }

    return {
        "available": False,
        "reason": "no parseable JSON or JSONL found in clipboard text",
    }


'''

# Find the old function and replace it
old_func_start = None
old_func_end = None
for i, line in enumerate(lines):
    if line.strip().startswith('def read_addon_bridge('):
        old_func_start = i
        # Find the next function definition or file end
        for j in range(i + 1, len(lines)):
            stripped = lines[j].strip()
            if stripped.startswith('def ') and not stripped.startswith('def read_addon_bridge'):
                old_func_end = j
                break
            if stripped.startswith('class '):
                old_func_end = j
                break
        if old_func_end is None:
            old_func_end = len(lines)
        break

if old_func_start is not None and old_func_end is not None:
    # Replace the range
    new_lines = new_read_addon_bridge.splitlines(keepends=True)
    lines[old_func_start:old_func_end] = new_lines
    edits.append(f'Edit 3: Replaced read_addon_bridge function (lines {old_func_start+1}-{old_func_end}) with clipboard version')
else:
    edits.append('Edit 3: FAILED - could not find read_addon_bridge function')

# ---- Edit 4: Update run_addon_snapshot to accept hwnd/pid ----
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith('def run_addon_snapshot('):
        # Replace the function body
        new_func = '''def run_addon_snapshot(args: argparse.Namespace) -> int:
    """Read and display the latest addon bridge snapshot via clipboard relay."""
    hwnd = getattr(args, "hwnd", None)
    pid = getattr(args, "pid", None)
    if not hwnd or not pid:
        print("--pid and --hwnd are required for clipboard bridge reading", file=sys.stderr)
        return 1
    bridge = read_addon_bridge(hwnd, pid)
    print(json.dumps(bridge, indent=2, default=str))
    if bridge.get("available"):
        return 0
    print(f"Bridge snapshot unavailable: {bridge.get('reason', 'unknown')}", file=sys.stderr)
    return 1


'''
        old_end = i + 1
        for j in range(i + 1, len(lines)):
            stripped = lines[j].strip()
            if stripped.startswith('def ') and not stripped.startswith('def run_addon_snapshot'):
                old_end = j
                break
            if stripped.startswith('class '):
                old_end = j
                break
        
        new_func_lines = new_func.splitlines(keepends=True)
        lines[i:old_end] = new_func_lines
        edits.append(f'Edit 4: Updated run_addon_snapshot function (line {i+1})')
        break

# Write the modified file
with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)

for e in edits:
    print(e)
print(f'Done. Wrote {len(lines)} lines.')
