"""Add --dry-run flag to write-addon-command subparser."""
import ast

path = 'tools/autofish-helper-py/autofish_helper.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

anchor = '    write_addon_cmd_parser.add_argument(\n        "--saved-vars-path",\n        default=None,\n        help="Path to AutoFish.lua SavedVariables file for direct injection",\n    )'

replacement = '    write_addon_cmd_parser.add_argument(\n        "--saved-vars-path",\n        default=None,\n        help="Path to AutoFish.lua SavedVariables file for direct injection",\n    )\n    write_addon_cmd_parser.add_argument(\n        "--dry-run",\n        action="store_true",\n        help="Preview the command that would be written without modifying any files",\n    )'

if anchor in content:
    content = content.replace(anchor, replacement, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added --dry-run flag")
else:
    print("ERROR: Anchor not found")

try:
    ast.parse(content)
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax error at line {e.lineno}: {e.msg}")
