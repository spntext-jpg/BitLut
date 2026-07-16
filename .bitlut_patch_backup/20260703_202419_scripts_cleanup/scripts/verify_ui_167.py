#!/usr/bin/env python3
from pathlib import Path
import sys

shell = Path("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt").read_text(encoding="utf-8")
main = Path("app/src/main/java/com/openhealth/sync/MainActivity.kt").read_text(encoding="utf-8")

errors = []

if "val icon: ImageVector" not in shell:
    errors.append("MainTab must use ImageVector icons")
if "Icons.Rounded.Today" not in shell or "Icons.Rounded.TrendingUp" not in shell or "Icons.Rounded.Settings" not in shell:
    errors.append("Bottom navigation must use Today / TrendingUp / Settings Material icons")
if "Icon(" not in shell or "imageVector = tab.icon" not in shell:
    errors.append("NavigationBarItem must render Icon(imageVector = tab.icon)")
if "tab_7days" not in shell:
    errors.append("Seven-day tab label key is missing")
if "maxLines" not in shell or "TextOverflow.Ellipsis" not in shell:
    errors.append("Settings UI must protect text from overflow")
if "onImportArchive" not in shell or "import_archive_title" not in shell:
    errors.append("Settings screen must expose archive import action")
if "openHuaweiArchiveImport" not in main or "ACTION_OPEN_DOCUMENT" not in main:
    errors.append("MainActivity must expose Huawei archive picker entry point")

if errors:
    print("UI 1.6.7 verification failed:")
    for e in errors:
        print(" -", e)
    sys.exit(1)

print("UI 1.6.7 verification passed.")
