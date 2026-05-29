import sys

filepath = "tools/autofish-helper-py/autofish_helper.py"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

edit_count = 0

# Edit 1: Add bridge_snapshot param to build_autofish_doctor_report
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped == "session_plan: str," and i > 6400 and i < 6450:
        next_stripped = lines[i+1].strip() if i+1 < len(lines) else ""
        if next_stripped == "*,":
            lines.insert(i+1, "    bridge_snapshot: dict[str, Any] | None = None,\n")
            edit_count += 1
            print(f"Edit 1: Added bridge_snapshot param at line {i+2}")
            break

# Edit 2: Add addonBridge to report summary
for i, line in enumerate(lines):
    stripped = line.strip()
    if "sessionPlanReadyForBoundedSession" in stripped and "session_summary" in stripped:
        indent = " " * (len(line) - len(line.lstrip()))
        lines.insert(i+1, f'{indent}"addonBridgeAvailable": bool(bridge_snapshot is not None and bridge_snapshot.get("available")),\n')
        lines.insert(i+2, f'{indent}"addonBridge": bridge_snapshot if bridge_snapshot else {{"available": False, "reason": "not provided"}},\n')
        edit_count += 1
        print(f"Edit 2: Added addonBridge at line {i+2}")
        break

# Edit 3: Add bridge_snapshot param to build_autofish_doctor_report call
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped == "report = build_autofish_doctor_report(":
        for j in range(i, i+10):
            if j < len(lines):
                js = lines[j].strip()
                if js.startswith("fail_on="):
                    indent = " " * (len(lines[j]) - len(lines[j].lstrip()))
                    lines.insert(j+1, f"{indent}bridge_snapshot=bridge_snapshot,\n")
                    edit_count += 1
                    print(f"Edit 3: Added bridge_snapshot param at line {j+2}")
                    break
        break

# Edit 4: Read bridge_snapshot before calling build_autofish_doctor_report
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("output_root = Path(args.output_root) if args.output_root else Path("):
        indent = " " * (len(line) - len(line.lstrip()))
        insert_index = i
        for k in range(i, i+5):
            if k < len(lines):
                ks = lines[k].strip()
                if ks.startswith("output_root.mkdir(parents=True, exist_ok=True)"):
                    insert_index = k
                    break
        
        insert_lines = [
            f"{indent}# Read addon bridge snapshot if bridge-path provided\n",
            f"{indent}bridge_snapshot = None\n",
            f'{indent}bridge_path = getattr(args, "bridge_path", None)\n',
            f"{indent}if bridge_path:\n",
            f"{indent}    try:\n",
            f"{indent}        bridge_snapshot = read_addon_bridge(bridge_path)\n",
            f"{indent}    except Exception as exc_read:\n",
            f'{indent}        bridge_snapshot = {{"available": False, "reason": f"bridge read failed: {exc_read}"}}\n',
        ]
        for bline in reversed(insert_lines):
            lines.insert(insert_index + 1, bline)
        edit_count += 1
        print(f"Edit 4: Added bridge reading at line {insert_index + 1}")
        break

with open(filepath, "w", encoding="utf-8") as f:
    f.writelines(lines)

print(f"\nTotal edits applied: {edit_count}")
