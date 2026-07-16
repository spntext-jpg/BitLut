#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path('.')
errors = []

for p in Path('app/src/main/java/com/openhealth/sync').rglob('*.kt'):
    text = p.read_text(errors='ignore')
    if re.search(r'\bobject\s+(BText|FinalUiText)\b', text):
        errors.append(f'Hardcoded UI localization object remains: {p}')
    if re.search(r'\b(BText|FinalUiText)\.t\(', text):
        errors.append(f'Hardcoded UI text call remains: {p}')

for pattern in ['*.bak', 'bitlut_*_patch.py']:
    found = [str(p) for p in root.rglob(pattern) if '.git' not in p.parts]
    if found:
        errors.append(f'Generated artifacts present for {pattern}: ' + ', '.join(found[:10]))

if Path('.kotlin/errors').exists():
    found = [str(p) for p in Path('.kotlin/errors').glob('*') if p.is_file()]
    if found:
        errors.append('Kotlin error artifacts present: ' + ', '.join(found[:10]))

usage = set()
for p in Path('app/src/main/java/com/openhealth/sync').rglob('*.kt'):
    usage.update(re.findall(r'R\.string\.([A-Za-z0-9_]+)', p.read_text(errors='ignore')))
for folder in ['app/src/main/res/values', 'app/src/main/res/values-ru']:
    defined = set()
    for p in Path(folder).glob('*.xml'):
        defined.update(re.findall(r'<string name="([^"]+)"', p.read_text(errors='ignore')))
    missing = sorted(usage - defined)
    if missing:
        errors.append(f'{folder} missing string keys: {missing}')

if errors:
    print('UI localization architecture verification failed:')
    for e in errors:
        print(' -', e)
    sys.exit(1)
print('UI localization architecture verification passed.')
