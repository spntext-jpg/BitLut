#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(".")

CONTRACTS = ROOT / "app/src/main/java/com/openhealth/sync/data/HealthDataContracts.kt"
GOOGLE = ROOT / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt"
HUAWEI = ROOT / "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt"
APP_CONTAINER = ROOT / "app/src/main/java/com/openhealth/sync/di/AppContainer.kt"
DASHBOARD_VM = ROOT / "app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt"
SYNC_VM = ROOT / "app/src/main/java/com/openhealth/sync/ui/SyncViewModel.kt"
IMPORT_VM = ROOT / "app/src/main/java/com/openhealth/sync/ui/ImportViewModel.kt"
PERMISSION_REQUESTER = ROOT / "app/src/main/java/com/openhealth/sync/config/GoogleHealthPermissionRequester.kt"
README = ROOT / "README.md"
CONTEXT = ROOT / "CONTEXT.md"
VERIFY = ROOT / "scripts/verify_architecture_hardening_interfaces.py"

OLD_TEMP_PATCHES = [
    "scripts/patch_v196_glass20_gui_polish.py",
    "scripts/patch_v196_gui_neoglass_activity_only.py",
    "scripts/patch_v196_gui_neoglass_activity_only_recovery.py",
]

def read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def cleanup_temp_files() -> None:
    for pattern in [
        "app/src/main/**/*.orig",
        "app/src/main/**/*.bak",
        "app/src/main/**/*.tmp",
    ]:
        for path in ROOT.glob(pattern):
            path.unlink(missing_ok=True)

    for patch in OLD_TEMP_PATCHES:
        Path(patch).unlink(missing_ok=True)

def ensure_import(text: str, import_line: str) -> str:
    if import_line in text:
        return text

    package_match = re.search(r"^package [^\n]+\n", text)
    if not package_match:
        return import_line + "\n" + text

    return text[:package_match.end()] + import_line + "\n" + text[package_match.end():]

def remove_import(text: str, import_line: str) -> str:
    return text.replace(import_line + "\n", "")

def find_matching(text: str, open_index: int, open_char: str = "{", close_char: str = "}") -> int:
    depth = 0
    i = open_index
    in_string = False
    triple = False
    escaped = False
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

def create_contracts() -> None:
    write(CONTRACTS, '''package com.openhealth.sync.data

import android.content.Intent

/**
 * Thin contracts for ViewModel/test boundaries.
 *
 * Keep these interfaces activity-only for v1.9.6. Do not add sleep, pulse,
 * SpO2, HRV, stress or Activity Intensity until Huawei approval scope expands.
 */
interface HealthConnectManager {
    val permissions: Set<String>

    fun requiredPermissions(): Set<String>
    fun getStatus(): HealthConnectStatus

    suspend fun missingRequiredPermissions(): Set<String>
    suspend fun hasAllPermissions(): Boolean
    suspend fun readDashboardSnapshot(daysBack: Int): GoogleDashboardSnapshot?
    suspend fun writeSnapshot(snapshot: HuaweiHealthSnapshot): Boolean
}

interface HuaweiHealthReader {
    fun requestedScopeNames(): String
    fun isAuthorized(): Boolean
    fun isPendingApproval(): Boolean
    fun isAppGalleryVerificationRequired(): Boolean
    fun clearAppGalleryVerificationRequired()
    fun markAppGalleryVerificationRequired()
    fun getAuthorizationIntent(): Intent
    fun getHuaweiIdAuthorizationIntent(): Intent
    fun handleAuthorizationResult(resultCode: Int, data: Intent?): Boolean
    fun markAuthorizationUnknown()

    suspend fun readSnapshot(startTimeMs: Long, endTimeMs: Long): HuaweiHealthSnapshot
}
''')

def patch_google_manager() -> None:
    google = read(GOOGLE)

    google = re.sub(
        r"class GoogleHealthManager\(([^)]*)\)\s*(?::\s*HealthConnectManager)?\s*\{",
        r"class GoogleHealthManager(\1) : HealthConnectManager {",
        google,
        count=1,
    )

    replacements = {
        "val permissions: Set<String>": "override val permissions: Set<String>",
        "fun requiredPermissions(): Set<String>": "override fun requiredPermissions(): Set<String>",
        "fun getStatus(): HealthConnectStatus": "override fun getStatus(): HealthConnectStatus",
        "suspend fun missingRequiredPermissions(): Set<String>": "override suspend fun missingRequiredPermissions(): Set<String>",
        "suspend fun hasAllPermissions(): Boolean": "override suspend fun hasAllPermissions(): Boolean",
        "suspend fun writeSnapshot(snapshot: HuaweiHealthSnapshot): Boolean": "override suspend fun writeSnapshot(snapshot: HuaweiHealthSnapshot): Boolean",
        "suspend fun readDashboardSnapshot(daysBack: Int): GoogleDashboardSnapshot?": "override suspend fun readDashboardSnapshot(daysBack: Int): GoogleDashboardSnapshot?",
    }

    for old, new in replacements.items():
        google = google.replace(old, new)

    # Avoid duplicate override if re-run.
    google = google.replace("override override ", "override ")

    write(GOOGLE, google)

def patch_huawei_manager() -> None:
    huawei = read(HUAWEI)

    for import_line in [
        "import kotlinx.coroutines.CoroutineDispatcher",
        "import kotlinx.coroutines.Dispatchers",
        "import kotlinx.coroutines.withContext",
    ]:
        huawei = ensure_import(huawei, import_line)

    huawei = re.sub(
        r"class HuaweiHealthManager\(private val context: Context\)\s*(?::\s*HuaweiHealthReader)?\s*\{",
        "class HuaweiHealthManager(\n    private val context: Context,\n    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO\n) : HuaweiHealthReader {",
        huawei,
        count=1,
    )

    # Public interface methods.
    for name in [
        "requestedScopeNames",
        "isAuthorized",
        "isPendingApproval",
        "isAppGalleryVerificationRequired",
        "clearAppGalleryVerificationRequired",
        "markAppGalleryVerificationRequired",
        "getAuthorizationIntent",
        "getHuaweiIdAuthorizationIntent",
        "handleAuthorizationResult",
        "markAuthorizationUnknown",
    ]:
        huawei = re.sub(
            rf"(?m)^    fun {name}\(",
            f"    override fun {name}(",
            huawei,
        )

    huawei = re.sub(
        r"(?m)^    suspend fun readSnapshot\(",
        "    override suspend fun readSnapshot(",
        huawei,
    )

    # Wrap readSnapshot in Dispatchers.IO if not already wrapped.
    marker = "override suspend fun readSnapshot("
    idx = huawei.find(marker)
    if idx != -1 and "return withContext(ioDispatcher)" not in huawei[idx:idx + 1200]:
        brace = huawei.find("{", idx)
        if brace == -1:
            raise RuntimeError("HuaweiHealthManager.readSnapshot brace not found")

        end = find_matching(huawei, brace)
        body = huawei[brace + 1:end]

        # The old body ends with "return snapshot"; inside withContext that should be final expression.
        body = body.replace("        return snapshot", "        snapshot")

        new_body = "{\n        return withContext(ioDispatcher) {" + body + "\n        }\n    "
        huawei = huawei[:brace] + new_body + huawei[end:]

    huawei = huawei.replace("override override ", "override ")

    write(HUAWEI, huawei)

def patch_app_container() -> None:
    write(APP_CONTAINER, '''package com.openhealth.sync.di

import android.content.Context
import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.data.HealthConnectManager
import com.openhealth.sync.data.HuaweiHealthManager
import com.openhealth.sync.data.HuaweiHealthReader

class AppContainer(private val context: Context) {
    val googleHealthManager: HealthConnectManager by lazy { GoogleHealthManager(context) }
    val huaweiHealthManager: HuaweiHealthReader by lazy { HuaweiHealthManager(context) }
}
''')

def patch_viewmodels() -> None:
    dashboard = read(DASHBOARD_VM)
    dashboard = remove_import(dashboard, "import com.openhealth.sync.data.GoogleHealthManager")
    dashboard = ensure_import(dashboard, "import com.openhealth.sync.data.HealthConnectManager")
    dashboard = dashboard.replace(
        "private val googleManager: GoogleHealthManager",
        "private val googleManager: HealthConnectManager",
    )
    dashboard = dashboard.replace(
        "googleManager: GoogleHealthManager,",
        "googleManager: HealthConnectManager,",
    )
    write(DASHBOARD_VM, dashboard)

    sync = read(SYNC_VM)
    sync = remove_import(sync, "import com.openhealth.sync.data.GoogleHealthManager")
    sync = remove_import(sync, "import com.openhealth.sync.data.HuaweiHealthManager")
    sync = ensure_import(sync, "import com.openhealth.sync.data.HealthConnectManager")
    sync = ensure_import(sync, "import com.openhealth.sync.data.HuaweiHealthReader")
    sync = sync.replace("val googleManager: GoogleHealthManager", "val googleManager: HealthConnectManager")
    sync = sync.replace("val huaweiHealthManager: HuaweiHealthManager", "val huaweiHealthManager: HuaweiHealthReader")
    sync = sync.replace("googleManager: GoogleHealthManager,", "googleManager: HealthConnectManager,")
    sync = sync.replace("huaweiHealthManager: HuaweiHealthManager,", "huaweiHealthManager: HuaweiHealthReader,")
    write(SYNC_VM, sync)

    import_vm = read(IMPORT_VM)
    import_vm = remove_import(import_vm, "import com.openhealth.sync.data.GoogleHealthManager")
    import_vm = ensure_import(import_vm, "import com.openhealth.sync.data.HealthConnectManager")
    import_vm = import_vm.replace(
        "private val googleManager: GoogleHealthManager",
        "private val googleManager: HealthConnectManager",
    )
    import_vm = import_vm.replace(
        "googleManager: GoogleHealthManager,",
        "googleManager: HealthConnectManager,",
    )
    write(IMPORT_VM, import_vm)

def patch_permission_requester() -> None:
    requester = read(PERMISSION_REQUESTER)

    requester = remove_import(requester, "import com.openhealth.sync.data.GoogleHealthManager")
    requester = ensure_import(requester, "import com.openhealth.sync.data.HealthConnectManager")

    requester = requester.replace(
        "googleManager: GoogleHealthManager,",
        "googleManager: HealthConnectManager,",
    )

    write(PERMISSION_REQUESTER, requester)

def patch_docs() -> None:
    note = """
## v1.9.6 Architecture Hardening 1

Implemented:

- `HealthConnectManager` and `HuaweiHealthReader` interfaces define the app-facing health contracts.
- `GoogleHealthManager` and `HuaweiHealthManager` implement these contracts.
- `DashboardViewModel`, `SyncViewModel`, `ImportViewModel` and the Health Connect permission requester depend on interfaces instead of concrete manager classes.
- `AppContainer` exposes health dependencies through interfaces.
- Huawei snapshot reads are explicitly offloaded through an injectable `CoroutineDispatcher`, defaulting to `Dispatchers.IO`.

Still deferred to a later sprint:

- Moving WorkManager orchestration out of `MainActivity`.
- Splitting `FinalBitLutShell.kt` into feature-level UI files.
- Gradle Version Catalog migration.
""".strip()

    for doc in [README, CONTEXT]:
        if doc.exists():
            content = read(doc)
            if "## v1.9.6 Architecture Hardening 1" not in content:
                content = content.rstrip() + "\n\n" + note + "\n"
            write(doc, content)

def write_verifier() -> None:
    write(VERIFY, r'''#!/usr/bin/env python3
from pathlib import Path
import re
import sys

errors = []

def read(path):
    p = Path(path)
    if not p.exists():
        errors.append(f"Missing {path}")
        return ""
    return p.read_text(encoding="utf-8")

contracts = read("app/src/main/java/com/openhealth/sync/data/HealthDataContracts.kt")
google = read("app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt")
huawei = read("app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt")
container = read("app/src/main/java/com/openhealth/sync/di/AppContainer.kt")
dashboard = read("app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt")
sync_vm = read("app/src/main/java/com/openhealth/sync/ui/SyncViewModel.kt")
import_vm = read("app/src/main/java/com/openhealth/sync/ui/ImportViewModel.kt")
requester = read("app/src/main/java/com/openhealth/sync/config/GoogleHealthPermissionRequester.kt")

def require(condition, message):
    if not condition:
        errors.append(message)

require("interface HealthConnectManager" in contracts, "Missing HealthConnectManager interface")
require("interface HuaweiHealthReader" in contracts, "Missing HuaweiHealthReader interface")
require("class GoogleHealthManager(" in google and ": HealthConnectManager" in google, "GoogleHealthManager must implement HealthConnectManager")
require("class HuaweiHealthManager(" in huawei and ": HuaweiHealthReader" in huawei, "HuaweiHealthManager must implement HuaweiHealthReader")

for token in [
    "override val permissions",
    "override fun requiredPermissions",
    "override fun getStatus",
    "override suspend fun missingRequiredPermissions",
    "override suspend fun hasAllPermissions",
    "override suspend fun readDashboardSnapshot",
    "override suspend fun writeSnapshot",
]:
    require(token in google, f"GoogleHealthManager missing {token}")

for token in [
    "private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO",
    "return withContext(ioDispatcher)",
    "override suspend fun readSnapshot",
]:
    require(token in huawei, f"HuaweiHealthManager missing IO hardening token: {token}")

require("val googleHealthManager: HealthConnectManager" in container, "AppContainer must expose HealthConnectManager")
require("val huaweiHealthManager: HuaweiHealthReader" in container, "AppContainer must expose HuaweiHealthReader")

for name, text in [
    ("DashboardViewModel", dashboard),
    ("SyncViewModel", sync_vm),
    ("ImportViewModel", import_vm),
    ("GoogleHealthPermissionRequester", requester),
]:
    require("HealthConnectManager" in text, f"{name} must depend on HealthConnectManager")
    require("GoogleHealthManager" not in text, f"{name} must not depend on concrete GoogleHealthManager")

require("HuaweiHealthReader" in sync_vm, "SyncViewModel must depend on HuaweiHealthReader")
require("HuaweiHealthManager" not in sync_vm, "SyncViewModel must not depend on concrete HuaweiHealthManager")

for forbidden in [
    "SleepSessionRecord",
    "HeartRateRecord",
    "OxygenSaturationRecord",
    "HeartRateVariabilityRmssdRecord",
    "READ_SLEEP",
    "READ_HEART_RATE",
    "READ_OXYGEN_SATURATION",
    "READ_HEART_RATE_VARIABILITY",
]:
    require(forbidden not in contracts, f"Contracts must stay activity-only: {forbidden}")

if errors:
    print("Architecture hardening interface verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Architecture hardening interface verification passed.")
''')
    VERIFY.chmod(0o755)

def self_check() -> None:
    files = {
        "contracts": read(CONTRACTS),
        "google": read(GOOGLE),
        "huawei": read(HUAWEI),
        "container": read(APP_CONTAINER),
        "dashboard": read(DASHBOARD_VM),
        "sync": read(SYNC_VM),
        "import": read(IMPORT_VM),
        "requester": read(PERMISSION_REQUESTER),
    }

    errors = []

    if "interface HealthConnectManager" not in files["contracts"]:
        errors.append("HealthConnectManager not created")
    if "interface HuaweiHealthReader" not in files["contracts"]:
        errors.append("HuaweiHealthReader not created")
    if ": HealthConnectManager" not in files["google"]:
        errors.append("GoogleHealthManager does not implement HealthConnectManager")
    if ": HuaweiHealthReader" not in files["huawei"]:
        errors.append("HuaweiHealthManager does not implement HuaweiHealthReader")
    if "return withContext(ioDispatcher)" not in files["huawei"]:
        errors.append("Huawei readSnapshot is not wrapped in ioDispatcher")
    if "val googleHealthManager: HealthConnectManager" not in files["container"]:
        errors.append("AppContainer does not expose HealthConnectManager")
    if "val huaweiHealthManager: HuaweiHealthReader" not in files["container"]:
        errors.append("AppContainer does not expose HuaweiHealthReader")

    for key in ["dashboard", "sync", "import", "requester"]:
        if "GoogleHealthManager" in files[key]:
            errors.append(f"{key} still depends on concrete GoogleHealthManager")

    if "HuaweiHealthManager" in files["sync"]:
        errors.append("sync still depends on concrete HuaweiHealthManager")

    if errors:
        print("Architecture hardening patch failed:")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)

def main() -> None:
    cleanup_temp_files()
    create_contracts()
    patch_google_manager()
    patch_huawei_manager()
    patch_app_container()
    patch_viewmodels()
    patch_permission_requester()
    patch_docs()
    write_verifier()
    self_check()
    print("Applied Architecture Hardening 1: health manager interfaces and IO dispatcher safety.")

if __name__ == "__main__":
    main()
