#!/usr/bin/env python3
from pathlib import Path
import sys

path = Path("app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt")
s = path.read_text(encoding="utf-8")
errors = []

if "HUAWEI_READ_CHUNK_MS" not in s:
    errors.append("Missing HUAWEI_READ_CHUNK_MS daily chunk constant")
if "readPointsRaw" not in s:
    errors.append("Original readPoints implementation must be preserved as readPointsRaw")
if "while (chunkStart <" not in s:
    errors.append("readPoints wrapper must iterate daily chunks")
if "distinctBy" not in s:
    errors.append("readPoints wrapper must dedupe boundary overlaps")
if "shouldBypassChunkingForHuaweiRead" not in s:
    errors.append("Missing activity/session chunking bypass")
for keyword in ["activity", "exercise", "session", "sport"]:
    if keyword not in s.lower():
        errors.append(f"Chunking bypass should mention {keyword}")

if errors:
    print("Huawei chunking verification failed:")
    for e in errors:
        print(" -", e)
    sys.exit(1)

print("Huawei chunking verification passed.")
