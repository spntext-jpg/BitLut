#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(".")

MAIN = ROOT / "app/src/main/java/com/openhealth/sync/MainActivity.kt"
ORCHESTRATOR = ROOT / "app/src/main/java/com/openhealth/sync/domain/SyncOrchestrator.kt"
VERIFY = ROOT / "scripts/verify_sync_orchestrator_sprint.py"

def read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def ensure_import(text: str, import_line: str) -> str:
    if import_line in text:
        return text
    m = re.search(r"^package [^\n]+\n", text)
    if not m:
        return import_line + "\n" + text
    return text[:m.end()] + import_line + "\n" + text[m.end():]

def remove_import(text: str, import_line: str) -> str:
    return text.replace(import_line + "\n", "")

def find_matching(text: str, open_index: int, open_char: str = "{", close_char: str = "}") -> int:
    depth = 0
    i = open_index
    in_string = False
    escaped = False
    triple = False
    in_line_comment = False
    in_block_comment = False

    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
        elif in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 1
        elif in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif triple and text.startswith('"""', i):
                in_string = False
                triple = False
                i += 2
            elif not triple and ch == '"':
                in_string = False
        else:
            if ch == "/" and nxt == "/":
                in_line_comment = True
                i += 1
            elif ch == "/" and nxt == "*":
                in_block_comment = True
                i += 1
            elif text.startswith('"""', i):
                in_string = True
                triple = True
                i += 2
            elif ch == '"':
                in_string = True
            elif ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    return i
        i += 1

    raise RuntimeError(f"Matching {close_char} not found")

def remove_named_function(text: str, name: str) -> str:
    pattern = re.compile(r"(?m)^    (?:private\s+)?fun\s+" + re.escape(name) + r"\s*\(")
    while True:
        match = pattern.search(text)
        if not match:
            return text

        brace = text.find("{", match.end())
        if brace == -1:
            return text[:match.start()]

        end = find_matching(text, brace) + 1
        while end < len(text) and text[end] in " \t\r\n":
            end += 1
        text = text[:match.start()] + text[end:]

def remove_function_containing(text: str, token: str) -> str:
    while token in text:
        token_index = text.find(token)

        # Look backwards for the containing Activity-level function.
        candidates = list(re.finditer(r"(?m)^    (?:private\s+)?fun\s+[A-Za-z0-9_]+\s*\(", text[:token_index]))
        if not candidates:
            # Last-resort: remove the single line so build can surface the next issue.
            line_start = text.rfind("\n", 0, token_index) + 1
            line_end = text.find("\n", token_index)
            if line_end == -1:
                line_end = len(text)
            text = text[:line_start] + text[line_end + 1:]
            continue

        start = candidates[-1].start()
        brace = text.find("{", candidates[-1].end())
        if brace == -1:
            line_start = text.rfind("\n", 0, token_index) + 1
            line_end = text.find("\n", token_index)
            if line_end == -1:
                line_end = len(text)
            text = text[:line_start] + text[line_end + 1:]
            continue

        try:
            end = find_matching(text, brace) + 1
        except RuntimeError:
            line_start = text.rfind("\n", 0, token_index) + 1
            line_end = text.find("\n", token_index)
            if line_end == -1:
                line_end = len(text)
            text = text[:line_start] + text[line_end + 1:]
            continue

        while end < len(text) and text[end] in " \t\r\n":
            end += 1
        text = text[:start] + text[end:]

    return text

def insert_before_final_class_brace(text: str, block: str) -> str:
    index = text.rfind("\n}")
    if index == -1:
        raise RuntimeError("MainActivity final brace not found")
    return text[:index].rstrip() + "\n\n" + block.rstrip() + "\n" + text[index:]

def patch_orchestrator() -> None:
    orchestrator = read(ORCHESTRATOR)

    orchestrator = orchestrator.replace(
        "import com.openhealth.sync.data.GoogleHealthManager",
        "import com.openhealth.sync.data.HealthConnectManager",
    )
    if "import com.openhealth.sync.data.HealthConnectManager" not in orchestrator:
        orchestrator = ensure_import(orchestrator, "import com.openhealth.sync.data.HealthConnectManager")

    orchestrator = orchestrator.replace(
        "private val googleManager: GoogleHealthManager",
        "private val googleManager: HealthConnectManager",
    )

    write(ORCHESTRATOR, orchestrator)

def patch_main() -> None:
    main = read(MAIN)

    # Remove WorkManager/worker imports from Activity.
    for import_line in [
        "import androidx.work.Constraints",
        "import androidx.work.ExistingPeriodicWorkPolicy",
        "import androidx.work.ExistingWorkPolicy",
        "import androidx.work.NetworkType",
        "import androidx.work.OneTimeWorkRequestBuilder",
        "import androidx.work.PeriodicWorkRequestBuilder",
        "import androidx.work.WorkInfo",
        "import androidx.work.WorkManager",
        "import com.openhealth.sync.data.worker.SyncWorker",
        "import com.openhealth.sync.data.worker.BackgroundSyncScheduler",
        "import java.util.concurrent.TimeUnit",
    ]:
        main = remove_import(main, import_line)

    main = ensure_import(main, "import androidx.lifecycle.lifecycleScope")
    main = ensure_import(main, "import com.openhealth.sync.domain.SyncOrchestrator")
    main = ensure_import(main, "import kotlinx.coroutines.launch")

    # Remove broken old implementations, regardless of exact function names.
    for fn in [
        "setupPeriodicSync",
        "triggerImmediateSync",
        "syncNowAfterPermissionCheck",
    ]:
        main = remove_named_function(main, fn)

    for token in [
        "BackgroundSyncScheduler",
        "WorkManager.getInstance",
        "WorkInfo.State",
        "getWorkInfoByIdLiveData",
        "enqueueImmediateSync",
    ]:
        main = remove_function_containing(main, token)

    # Add orchestrator lazy property if missing.
    if "private val syncOrchestrator: SyncOrchestrator by lazy" not in main:
        anchor = "class MainActivity : ComponentActivity() {\n"
        if anchor not in main:
            raise RuntimeError("MainActivity class anchor not found")
        main = main.replace(
            anchor,
            anchor + '''
    private val syncOrchestrator: SyncOrchestrator by lazy {
        SyncOrchestrator(this, syncViewModel.googleManager)
    }

''',
            1,
        )

    # Add clean functions before final class brace.
    clean_functions = '''
    private fun setupPeriodicSync() {
        syncOrchestrator.schedulePeriodic()
    }

    private fun triggerImmediateSync() {
        lifecycleScope.launch {
            syncOrchestrator.triggerImmediateSync(
                lifecycleOwner = this@MainActivity,
                onStarted = { syncViewModel.markSyncStarted() },
                onMissingPermissions = {
                    Toast.makeText(
                        this@MainActivity,
                        getString(R.string.toast_hc_permissions),
                        Toast.LENGTH_LONG
                    ).show()
                    requestGoogleHealthPermissions()
                },
                onCompleted = { success -> syncViewModel.markSyncCompleted(success) },
                onDashboardRefresh = { dashboardViewModel.refresh() }
            )
        }
    }
'''

    main = insert_before_final_class_brace(main, clean_functions)

    # Ensure onCreate still calls setupPeriodicSync before launch refresh/content.
    if "setupPeriodicSync()" not in main[:main.find("setContent") if "setContent" in main else len(main)]:
        if "refreshUiStatusOnLaunch()" in main:
            main = main.replace(
                "refreshUiStatusOnLaunch()",
                "setupPeriodicSync()\n        refreshUiStatusOnLaunch()",
                1,
            )
        elif "setContent" in main:
            main = main.replace(
                "setContent",
                "setupPeriodicSync()\n        setContent",
                1,
            )

    main = re.sub(r"\n{3,}", "\n\n", main)
    write(MAIN, main)

def write_verifier() -> None:
    write(VERIFY, r'''#!/usr/bin/env python3
from pathlib import Path
import sys

errors = []

def read(path):
    p = Path(path)
    if not p.exists():
        errors.append(f"Missing {path}")
        return ""
    return p.read_text(encoding="utf-8")

orchestrator = read("app/src/main/java/com/openhealth/sync/domain/SyncOrchestrator.kt")
main = read("app/src/main/java/com/openhealth/sync/MainActivity.kt")

def require(condition, message):
    if not condition:
        errors.append(message)

require("class SyncOrchestrator(" in orchestrator, "SyncOrchestrator class missing")
require("private val googleManager: HealthConnectManager" in orchestrator, "Orchestrator must depend on HealthConnectManager interface")
require("fun schedulePeriodic()" in orchestrator, "Orchestrator must expose schedulePeriodic")
require("suspend fun triggerImmediateSync(" in orchestrator, "Orchestrator must expose triggerImmediateSync")
require("BackgroundSyncScheduler.schedulePeriodic(appContext)" in orchestrator, "Periodic scheduling must delegate to BackgroundSyncScheduler")
require("BackgroundSyncScheduler.enqueueImmediateSync(appContext)" in orchestrator, "Immediate sync must delegate to BackgroundSyncScheduler")
require("googleManager.missingRequiredPermissions()" in orchestrator, "Manual sync must preflight required Health Connect permissions")
require("WorkManager.getInstance(appContext)" in orchestrator, "Orchestrator must own WorkManager access")
require("getWorkInfoByIdLiveData(requestId).observe(lifecycleOwner)" in orchestrator, "Work observation must be lifecycle-owned")

require("private val syncOrchestrator: SyncOrchestrator by lazy" in main, "MainActivity must own SyncOrchestrator")
require("private fun setupPeriodicSync()" in main, "MainActivity missing setupPeriodicSync")
require("private fun triggerImmediateSync()" in main, "MainActivity missing triggerImmediateSync")
require("syncOrchestrator.schedulePeriodic()" in main, "setupPeriodicSync must delegate to orchestrator")
require("syncOrchestrator.triggerImmediateSync(" in main, "triggerImmediateSync must delegate to orchestrator")
require("requestGoogleHealthPermissions()" in main, "Missing permission flow must still open Health Connect request")

for forbidden in [
    "import androidx.work.WorkManager",
    "import androidx.work.WorkInfo",
    "import androidx.work.OneTimeWorkRequestBuilder",
    "import androidx.work.PeriodicWorkRequestBuilder",
    "import com.openhealth.sync.data.worker.BackgroundSyncScheduler",
    "BackgroundSyncScheduler",
    "WorkManager.getInstance",
    "WorkInfo.State",
    "getWorkInfoByIdLiveData",
]:
    require(forbidden not in main, f"MainActivity must not contain orchestration detail: {forbidden}")

if errors:
    print("Sync Orchestrator recovery verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Sync Orchestrator recovery verification passed.")
''')
    VERIFY.chmod(0o755)

def self_check() -> None:
    orchestrator = read(ORCHESTRATOR)
    main = read(MAIN)

    errors = []

    if "private val googleManager: HealthConnectManager" not in orchestrator:
        errors.append("SyncOrchestrator does not use HealthConnectManager interface")

    for token in [
        "private fun setupPeriodicSync()",
        "private fun triggerImmediateSync()",
        "syncOrchestrator.schedulePeriodic()",
        "syncOrchestrator.triggerImmediateSync(",
    ]:
        if token not in main:
            errors.append(f"MainActivity missing {token}")

    for forbidden in [
        "BackgroundSyncScheduler",
        "WorkManager.getInstance",
        "WorkInfo.State",
        "getWorkInfoByIdLiveData",
        "import androidx.work.WorkManager",
        "import androidx.work.WorkInfo",
    ]:
        if forbidden in main:
            errors.append(f"MainActivity still contains {forbidden}")

    if errors:
        print("Sync Orchestrator recovery patch failed:")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)

def main() -> None:
    patch_orchestrator()
    patch_main()
    write_verifier()
    self_check()
    print("Recovered Sync Orchestrator integration.")

if __name__ == "__main__":
    main()
