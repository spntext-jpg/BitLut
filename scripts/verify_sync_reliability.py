#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(".")
google = root / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt"
huawei = root / "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt"

errors = []

g = google.read_text(encoding="utf-8")

if "HealthPermissionPolicy.syncPermissions" not in g:
    errors.append("GoogleHealthManager.permissions must use HealthPermissionPolicy.syncPermissions")

if "clientRecordId" not in g or "generateRecordId" not in g:
    errors.append("GoogleHealthManager must assign stable Metadata.clientRecordId for dedupe/upsert safety")

record_types = [
    "StepsRecord",
    "DistanceRecord",
    "FloorsClimbedRecord",
    "ElevationGainedRecord",
    "ActiveCaloriesBurnedRecord",
    "ExerciseSessionRecord",
]

def find_call_end(text: str, open_paren: int) -> int:
    depth = 0
    i = open_paren
    in_string = False
    escape = False
    while i < len(text):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return -1

for record in record_types:
    pos = 0
    while True:
        idx = g.find(record + "(", pos)
        if idx == -1:
            break
        end = find_call_end(g, idx + len(record))
        if end == -1:
            errors.append(f"Could not parse {record} constructor")
            break
        block = g[idx:end + 1]
        if "metadata" not in block or "bitlutMetadata" not in block:
            errors.append(f"{record} constructor missing bitlutMetadata(...)")
        pos = end + 1

if "writeSnapshot" in g:
    m = re.search(r"suspend\s+fun\s+writeSnapshot\s*\([^)]*\)\s*:\s*Boolean\s*\{(.*?)\n\s*\}", g, re.S)
    if m and "&&" in m.group(1):
        errors.append("writeSnapshot should not be a chained && expression; isolate category writes")

if huawei.exists():
    h = huawei.read_text(encoding="utf-8")
    if "MAX_LOOKBACK_MS" in h and "readChunk" not in h and "chunk" not in h.lower():
        print("Warning: Huawei read chunking guardrail not yet detected. Add daily chunking in P1.")

if errors:
    print("Sync reliability verification failed:")
    for e in errors:
        print(" -", e)
    sys.exit(1)

print("Sync reliability verification passed.")
