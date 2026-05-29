"""Apply final fixes to align bridge with clipboard-based approach."""
import sys

filepath = 'tools/autofish-helper-py/autofish_helper.py'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

edits = []

# ---- Fix 1: Remove bridge reading from run_session_plan_doctor ----
for i, line in enumerate(lines):
    if 'output_root.mkdir(parents=True, exist_ok=True)' in line and i > 2090 and i < 2120:
        remove_start = i + 1  # first line after mkdir
        for j in range(remove_start, min(remove_start + 20, len(lines))):
            if lines[j].strip().startswith('report = build_session_plan_doctor_report('):
                remove_end = j  # exclude this line
                bridge_lines = lines[remove_start:remove_end]
                bridge_text = ''.join(bridge_lines)
                if 'bridge_snapshot' in bridge_text:
                    # Remove those lines
                    lines[remove_start:remove_end] = []
                    edits.append(f'Fix 1: Removed bridge reading lines {remove_start+1}-{remove_end} from run_session_plan_doctor')
                break
        break

# ---- Fix 2: Update run_autofish_doctor to use hwnd/pid for bridge ----
for i, line in enumerate(lines):
    if 'output_root.mkdir(parents=True, exist_ok=True)' in line and i > 6700 and i < 6750:
        # Find the bridge reading lines that follow
        for j in range(i + 1, min(i + 20, len(lines))):
            if lines[j].strip().startswith('report = build_autofish_doctor_report('):
                # Replace the bridge reading section between mkdir and report call
                remove_start = i + 1
                remove_end = j
                old_bridge = ''.join(lines[remove_start:remove_end])
                if 'bridge_snapshot' in old_bridge or 'bridge_path' in old_bridge:
                    new_bridge = [
                        '    # Read addon bridge snapshot if pid/hwnd provided\n',
                        '    bridge_snapshot = None\n',
                        '    bridge_hwnd = getattr(args, "hwnd", None)\n',
                        '    bridge_pid = getattr(args, "pid", None)\n',
                        '    if bridge_hwnd and bridge_pid:\n',
                        '        try:\n',
                        '            bridge_snapshot = read_addon_bridge(bridge_hwnd, bridge_pid)\n',
                        '        except Exception as exc_read:\n',
                        '            bridge_snapshot = {"available": False, "reason": f"bridge read failed: {exc_read}"}\n',
                    ]
                    lines[remove_start:remove_end] = new_bridge
                    edits.append(f'Fix 2: Updated run_autofish_doctor bridge reading lines {remove_start+1}-{remove_end}')
                break
        break

# ---- Fix 3: Update addon-snapshot subparser to use --pid and --hwnd ----
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith('addon_snapshot.add_argument(') and '--bridge-path' in stripped:
        # Replace these arguments with --pid and --hwnd
        # Find the range: from this line to the next add_argument or set_defaults
        start = i
        end = i + 1
        for j in range(i + 1, min(i + 10, len(lines))):
            s = lines[j].strip()
            if s.startswith('addon_snapshot.add_argument(') or s.startswith('addon_snapshot.set_defaults('):
                end = j
                break
        
        new_args = [
            '    addon_snapshot.add_argument("--pid", type=int, required=True, help="Rift process PID for window focus")\n',
            '    addon_snapshot.add_argument("--hwnd", type=int, required=True, help="Rift window HWND for keyboard input")\n',
        ]
        lines[start:end] = new_args
        edits.append(f'Fix 3: Replaced --bridge-path with --pid/--hwnd in addon-snapshot subparser (lines {start+1}-{end})')
        break

# ---- Fix 4: Add --pid/--hwnd to doctor subparser ----
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith('doctor.add_argument(') and '--bridge-path' in stripped:
        start = i
        # This is a multi-line argument, find its end
        for j in range(i, min(i + 10, len(lines))):
            if lines[j].strip().endswith(')'):
                end = j + 1
                break
        else:
            end = i + 1
        
        new_doctor_args = [
            '    doctor.add_argument("--pid", type=int, help="Rift process PID for optional bridge clipboard snapshot")\n',
            '    doctor.add_argument("--hwnd", type=int, help="Rift window HWND for optional bridge clipboard snapshot")\n',
        ]
        lines[start:end] = new_doctor_args
        edits.append(f'Fix 4: Replaced --bridge-path with --pid/--hwnd in doctor subparser (lines {start+1}-{end})')
        break

# Write the modified file
with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)

for e in edits:
    print(e)
print(f'Done. Wrote {len(lines)} lines.')
