from pathlib import Path
import re

MAIN = Path('app/src/main/java/com/openhealth/sync/MainActivity.kt')
if not MAIN.exists():
    raise SystemExit('MainActivity.kt not found. Run this script from the repository root.')

text = MAIN.read_text(encoding='utf-8')

# Repair possible previous over-aggressive replacements.
text = text.replace('Screenandroidx.compose.foundation.layout.Column', 'ScreenColumn')
text = text.replace('androidx.compose.foundation.layout.androidx.compose.foundation.layout.Column(', 'androidx.compose.foundation.layout.Column(')

# Column is a composable function. ColumnScope is the receiver type for Column content.
text = text.replace('content: @Composable Column.() -> Unit', 'content: @Composable ColumnScope.() -> Unit')
text = text.replace('content: @Composable androidx.compose.foundation.layout.Column.() -> Unit', 'content: @Composable ColumnScope.() -> Unit')
text = text.replace('@Composable Column.() -> Unit', '@Composable ColumnScope.() -> Unit')
text = text.replace('@Composable androidx.compose.foundation.layout.Column.() -> Unit', '@Composable ColumnScope.() -> Unit')

lines = text.splitlines(True)
imports = [
    'import androidx.compose.foundation.layout.Column\n',
    'import androidx.compose.foundation.layout.ColumnScope\n',
]
existing = set(line for line in lines if line.startswith('import '))
insert_at = 0
for i, line in enumerate(lines):
    if line.startswith('import '):
        insert_at = i + 1

for imp in imports:
    if imp not in existing:
        lines.insert(insert_at, imp)
        insert_at += 1

text = ''.join(lines)

# Keep the file idempotent: remove duplicate import lines while preserving order.
seen_imports = set()
out = []
for line in text.splitlines(True):
    if line.startswith('import '):
        if line in seen_imports:
            continue
        seen_imports.add(line)
    out.append(line)
text = ''.join(out)

MAIN.write_text(text, encoding='utf-8')

print('Applied Column/ColumnScope hotfix')
print('Relevant references:')
for idx, line in enumerate(text.splitlines(), 1):
    if 'Column' in line:
        print(f'{idx}: {line}')
