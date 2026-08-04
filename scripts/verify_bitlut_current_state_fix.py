#!/usr/bin/env python3
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(".")
errors = []

def read(path: str) -> str:
    p = ROOT / path
    if not p.exists():
        errors.append(f"Missing {path}")
        return ""
    return p.read_text(encoding="utf-8")

def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

parser = read("app/src/main/java/com/openhealth/sync/data/import/HuaweiExportParser.kt")
scheduler = read("app/src/main/java/com/openhealth/sync/data/worker/BackgroundSyncScheduler.kt")
orch = read("app/src/main/java/com/openhealth/sync/domain/SyncOrchestrator.kt")
import_vm = read("app/src/main/java/com/openhealth/sync/ui/ImportViewModel.kt")
import_screen = read("app/src/main/java/com/openhealth/sync/ui/ImportScreen.kt")
main = read("app/src/main/java/com/openhealth/sync/MainActivity.kt")
shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
app_build = read("app/build.gradle.kts")
huawei_config = read("app/src/main/java/com/openhealth/sync/data/remote/HuaweiConfig.kt")
gitignore = read(".gitignore")

for token in ["MAX_SINGLE_JSON_BYTES", "MAX_TOTAL_ZIP_JSON_BYTES", "MAX_ZIP_ENTRIES", "Skipped unrecognized JSON without loading it", "is JSONArray -> root", "ExportKind.CALORIES", "ExportKind.ACTIVITY", "readBytesBounded"]:
    require(token in parser, f"Parser hardening missing: {token}")
require("zip.readBytes().toString" not in parser, "Parser still performs unbounded ZIP entry read")
require("JSONObject(content)" not in parser, "Parser still assumes object root")

for token in ["suspend fun enqueueImmediateSync", "immediateEnqueueMutex.withLock", "getWorkInfosForUniqueWorkFlow(UNIQUE_SYNC_NOW)", ".first()", "activeBefore.id"]:
    require(token in scheduler, f"Manual sync single-flight fix missing: {token}")
require("getWorkInfosForUniqueWork(UNIQUE_SYNC_NOW)" not in scheduler, "Scheduler still uses Guava ListenableFuture query API")
require(".result.get()" not in scheduler, "Scheduler still blocks on WorkManager Operation.result")
require("return request.id" not in scheduler, "Scheduler still blindly returns discarded KEEP request ID")
require("private suspend fun enqueueAfterPermissionCheck" in orch, "Orchestrator enqueue path must be suspend")
require("liveData.removeObserver(this)" in orch, "Terminal WorkManager observer is not detached")

require("collectAsStateWithLifecycle" in import_screen, "Import screen state collection is not lifecycle-aware")
require("automirrored.rounded.DirectionsRun" not in import_screen, "Import screen still uses AutoMirrored DirectionsRun")
require("import_error_read_failed|" in import_vm, "Import read error is not localization-key based")
require("import_error_write_failed|" in import_vm, "Import write error is not localization-key based")
require("if (\"steps\" in result.succeededCategories)" in import_vm, "Partial import counts are still overstated")
require("CancellationException" in import_vm, "Import cancellation is not propagated")

require("archiveImportLauncher" not in main, "Dead archive ActivityResult launcher remains")
require("openHuaweiArchiveImport" not in main, "Dead archive picker function remains")
require("onImportArchive = { openHuaweiArchiveImport() }" not in main, "MainActivity still wires dead archive callback")
require("onImportArchive: () -> Unit = {}" not in shell, "FinalBitLutShell retains unused archive callback")
require("onImportArchive = { showArchiveImport = true }" in shell, "In-app archive import navigation was removed")

require("HUAWEI_SCOPES" not in app_build, "Stale HUAWEI_SCOPES BuildConfig field remains")
require("HUAWEI_SCOPES" not in huawei_config, "Stale HuaweiConfig.SCOPES remains")
require("healthkit.heartrate" not in app_build.lower(), "Heart-rate scope remains in activity-only build config")
require(any(line.strip() == ".env.signing.local" for line in gitignore.splitlines()), ".env.signing.local is not ignored")

base_strings = ROOT / "app/src/main/res/values/strings.xml"
try:
    tree = ET.parse(base_strings)
    names = {node.attrib["name"] for node in tree.getroot() if "name" in node.attrib}
except Exception as exc:
    errors.append(f"Base strings.xml is invalid: {exc}")
    names = set()

for kt in (ROOT / "app/src/main/java").rglob("*.kt"):
    text = kt.read_text(encoding="utf-8")
    for name in re.findall(r"R\.string\.([A-Za-z0-9_]+)", text):
        require(name in names, f"Missing base string resource {name} referenced by {kt}")
    require("<<<<<<<" not in text and ">>>>>>>" not in text, f"Merge conflict marker in {kt}")

if errors:
    print("BitLut current-state verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)
print("BitLut current-state verification passed.")
