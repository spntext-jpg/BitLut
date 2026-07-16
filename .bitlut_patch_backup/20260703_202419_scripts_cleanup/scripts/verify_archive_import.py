#!/usr/bin/env python3
from pathlib import Path
import sys

shell = Path("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt").read_text(encoding="utf-8")
main = Path("app/src/main/java/com/openhealth/sync/MainActivity.kt").read_text(encoding="utf-8")
vm = Path("app/src/main/java/com/openhealth/sync/ui/ImportViewModel.kt").read_text(encoding="utf-8")

errors = []

if "ImportScreen(" not in shell:
    errors.append("FinalBitLutShell must render ImportScreen for archive import")
if "showArchiveImport" not in shell:
    errors.append("FinalBitLutShell must keep showArchiveImport state")
if "importViewModel: ImportViewModel" not in shell:
    errors.append("FinalBitLutShell must receive ImportViewModel")
if "importViewModel = importViewModel" not in main:
    errors.append("MainActivity must pass ImportViewModel into FinalBitLutShell")
if "parseFile(uri: Uri)" not in vm or "confirmImport(summary: HuaweiExportSummary)" not in vm:
    errors.append("ImportViewModel must retain parseFile and confirmImport flow")
if "googleManager.writeSnapshot(summary.snapshot)" not in vm:
    errors.append("ImportViewModel must write parsed archive snapshot to GoogleHealthManager")

if errors:
    print("Archive import verification failed:")
    for e in errors:
        print(" -", e)
    sys.exit(1)

print("Archive import verification passed.")
