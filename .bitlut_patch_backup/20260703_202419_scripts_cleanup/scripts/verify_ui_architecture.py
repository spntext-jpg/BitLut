#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path('.')
failures = []

main = root / 'app/src/main/java/com/openhealth/sync/MainActivity.kt'
if main.exists():
    txt = main.read_text(encoding='utf-8', errors='ignore')
    imports = [line for line in txt.splitlines() if line.startswith('import ')]
    dupes = sorted({x for x in imports if imports.count(x) > 1})
    if dupes:
        failures.append('Duplicate imports in MainActivity.kt: ' + ', '.join(dupes))
    line_count = len(txt.splitlines())
    if line_count > 260:
        failures.append(f'MainActivity.kt is still too large for AID/SOC target: {line_count} lines > 260')
    for marker in ['private object BText', 'private object FinalUiText']:
        if marker in txt:
            failures.append(f'Localization map remains in MainActivity.kt: {marker}')

screen = root / 'app/src/main/java/com/openhealth/sync/ui/DashboardScreen.kt'
if screen.exists():
    refs = []
    for p in (root / 'app/src/main/java/com/openhealth/sync').rglob('*.kt'):
        if p == screen:
            continue
        if re.search(r'\bDashboardScreen\b', p.read_text(encoding='utf-8', errors='ignore')):
            refs.append(str(p))
    if not refs:
        failures.append('Zombie DashboardScreen.kt exists but is not referenced')

for pattern in ['*.bak', 'bitlut_*_patch.py']:
    found = [str(p) for p in root.rglob(pattern) if '.git/' not in str(p)]
    if found:
        failures.append(f'Generated artifacts present for {pattern}: ' + ', '.join(found[:10]))

errors_dir = root / '.kotlin/errors'
if errors_dir.exists():
    files = [str(p) for p in errors_dir.rglob('*') if p.is_file()]
    if files:
        failures.append('Kotlin error artifacts present: ' + ', '.join(files[:10]))

if failures:
    print('UI architecture verification failed:')
    for f in failures:
        print(' - ' + f)
    sys.exit(1)

print('UI architecture verification passed.')
