"""
Re-indent Tab 02 district content block:
  Lines between 'else:' + 'cur = dc.iloc[0]' (after line ~1234)
  and '# 03 EDUCATION ANALYTICS' that are at exactly 8-space indent
  need to become 12-space indent so they sit inside the else: block.

Only touches lines inside Tab 02 that need indenting.
Writes in-place. Creates a .bak backup first.
"""
from pathlib import Path
import shutil

PATH = Path(r"c:\Users\userp\Desktop\ShalaScope_Maharashtra\dashboard\app.py")

# Backup
BAK = PATH.with_suffix(".py.bak")
shutil.copy2(PATH, BAK)
print(f"Backup: {BAK}")

lines = PATH.read_text(encoding="utf-8-sig").splitlines(keepends=True)

# Find the start line (the first line after 'cur = dc.iloc[0]' in Tab 02)
# and the end line (# 03 EDUCATION ANALYTICS)
start_idx = None
end_idx   = None

for i, l in enumerate(lines):
    if start_idx is None and "cur = dc.iloc[0]" in l:
        # The NEXT non-rank_txt line is where district content starts
        # We want to re-indent starting from "# ── District headline"
        pass
    if "# ── District headline" in l and start_idx is None:
        start_idx = i
    if "# 03 EDUCATION ANALYTICS" in l:
        end_idx = i
        break

print(f"Re-indent from line {start_idx+1} to {end_idx}")

changed = 0
for i in range(start_idx, end_idx):
    l = lines[i]
    # Count leading spaces
    stripped = l.lstrip()
    leading  = len(l) - len(l.lstrip('\n')) - len(stripped)  # handles \n at end
    # More accurate:
    raw = l.rstrip('\n')
    n_spaces = len(raw) - len(raw.lstrip(' '))
    if n_spaces == 8:
        lines[i] = "    " + l  # add 4 more spaces
        changed += 1

print(f"Re-indented {changed} lines")
PATH.write_text("".join(lines), encoding="utf-8")

# Verify syntax
import ast
try:
    ast.parse("".join(lines))
    print("SYNTAX OK after re-indent")
except SyntaxError as e:
    print(f"SYNTAX ERROR at line {e.lineno}: {e.msg}")
    # Restore backup
    shutil.copy2(BAK, PATH)
    print("Backup restored")
