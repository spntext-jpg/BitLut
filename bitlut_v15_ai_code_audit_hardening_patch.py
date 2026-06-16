#!/usr/bin/env python3
"""
BitLut v1.5 AI-readable hardening patch.

Goal:
- Keep Huawei import implementation in the codebase.
- Keep Huawei import hidden/disabled until Health Kit approval.
- Keep the shipped runtime focused on a premium Google Health Connect dashboard.
- Improve AID/CD/SOLID/KISS/YAGNI/Secure-by-Design/Observability alignment.

Run from the repository root:
    python3 bitlut_v15_ai_code_audit_hardening_patch.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path.cwd()
APP = ROOT / "app"
SRC = APP / "src" / "main" / "java" / "com" / "openhealth" / "sync"


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    sys.exit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail(f"Missing file: {path}")
    return path.read_text(encoding="utf-8")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old != content:
        path.write_text(content, encoding="utf-8")
        print(f"[WRITE] {path.relative_to(ROOT)}")
    else:
        print(f"[OK] {path.relative_to(ROOT)}")


def replace_or_fail(text: str, pattern: str, replacement: str, label: str, flags: int = re.S) -> str:
    updated, count = re.subn(pattern, replacement, text, flags=flags)
    if count == 0:
        fail(f"Could not patch {label}")
    return updated


def ensure_import(text: str, import_line: str) -> str:
    if import_line in text:
        return text
    package_match = re.search(r"^package .+\n", text, flags=re.M)
    if not package_match:
        fail(f"Cannot add import {import_line}: package declaration not found")
    insert_at = package_match.end()
    return text[:insert_at] + import_line + "\n" + text[insert_at:]


def remove_import(text: str, import_line: str) -> str:
    return text.replace(import_line + "\n", "")


def patch_build_gradle() -> None:
    path = APP / "build.gradle.kts"
    text = read(path)
    text = re.sub(
        r'val envVersionName = System\.getenv\("RELEASE_VERSION"\)\?\.takeIf \{ it\.isNotBlank\(\) \} \?: "[^"]+"',
        'val envVersionName = System.getenv("RELEASE_VERSION")?.takeIf { it.isNotBlank() } ?: "1.5.0"',
        text,
    )
    text = re.sub(
        r'val envVersionCode = System\.getenv\("RELEASE_VERSION_CODE"\)\?\.toIntOrNull\(\) \?: \d+',
        'val envVersionCode = System.getenv("RELEASE_VERSION_CODE")?.toIntOrNull() ?: 25',
        text,
    )
    write(path, text)


def create_feature_flags() -> None:
    write(
        SRC / "config" / "FeatureFlags.kt",
        """package com.openhealth.sync.config

/**
 * Central runtime switches for staged releases.
 *
 * v1.5 ships as a Google Health Connect dashboard-first app for AppGallery review.
 * Huawei import code remains compiled and reviewable, but is not reachable from UI,
 * background work, or permission prompts until Huawei Health Kit approval is granted.
 */
object FeatureFlags {
    const val HUAWEI_IMPORT_ENABLED: Boolean = false
    const val GOOGLE_HEALTH_DASHBOARD_ENABLED: Boolean = true
    const val RELEASE_TRACK: String = "v1.5-dashboard-first"
}
""",
    )


def create_permission_policy() -> None:
    write(
        SRC / "config" / "HealthPermissionPolicy.kt",
        """package com.openhealth.sync.config

import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.ActiveCaloriesBurnedRecord
import androidx.health.connect.client.records.DistanceRecord
import androidx.health.connect.client.records.ElevationGainedRecord
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.FloorsClimbedRecord
import androidx.health.connect.client.records.StepsRecord

/**
 * Health Connect permissions are split by product capability.
 *
 * Security principle: least privilege by default.
 * - Dashboard mode requests read-only access for visible metrics.
 * - Huawei import mode keeps write permissions ready, but hidden behind FeatureFlags.
 */
object HealthPermissionPolicy {
    val dashboardReadPermissions: Set<String> = setOf(
        HealthPermission.getReadPermission(StepsRecord::class),
        HealthPermission.getReadPermission(ExerciseSessionRecord::class),
    )

    val huaweiImportPermissions: Set<String> = setOf(
        HealthPermission.getReadPermission(StepsRecord::class),
        HealthPermission.getReadPermission(DistanceRecord::class),
        HealthPermission.getReadPermission(FloorsClimbedRecord::class),
        HealthPermission.getReadPermission(ElevationGainedRecord::class),
        HealthPermission.getReadPermission(ActiveCaloriesBurnedRecord::class),
        HealthPermission.getReadPermission(ExerciseSessionRecord::class),
        HealthPermission.getWritePermission(StepsRecord::class),
        HealthPermission.getWritePermission(DistanceRecord::class),
        HealthPermission.getWritePermission(FloorsClimbedRecord::class),
        HealthPermission.getWritePermission(ElevationGainedRecord::class),
        HealthPermission.getWritePermission(ActiveCaloriesBurnedRecord::class),
        HealthPermission.getWritePermission(ExerciseSessionRecord::class),
    )
}
""",
    )


def patch_google_health_manager() -> None:
    path = SRC / "data" / "GoogleHealthManager.kt"
    text = read(path)
    text = ensure_import(text, "import com.openhealth.sync.config.HealthPermissionPolicy")
    # HealthPermission is now owned by HealthPermissionPolicy. Keep record imports for read/write code.
    text = remove_import(text, "import androidx.health.connect.client.permission.HealthPermission")

    permission_block_pattern = (
        r"\n    // Sprint mode: Google Health dashboard only\.[\s\S]*?\n"
        r"    val permissions: Set<String> = setOf\([\s\S]*?\n    \)\n\n"
        r"    private val zoneRules"
    )
    if re.search(permission_block_pattern, text):
        text = re.sub(
            permission_block_pattern,
            """
    /** Runtime permissions for the visible v1.5 dashboard. */
    val permissions: Set<String> = HealthPermissionPolicy.dashboardReadPermissions

    /** Future Huawei import permissions. Do not request while FeatureFlags.HUAWEI_IMPORT_ENABLED is false. */
    val importPermissions: Set<String> = HealthPermissionPolicy.huaweiImportPermissions

    private val zoneRules""",
            text,
            flags=re.S,
        )
    elif "val permissions: Set<String> = HealthPermissionPolicy.dashboardReadPermissions" not in text:
        text = replace_or_fail(
            text,
            r"\n    val permissions: Set<String> = setOf\([\s\S]*?\n    \)\n\n    private val zoneRules",
            """
    /** Runtime permissions for the visible v1.5 dashboard. */
    val permissions: Set<String> = HealthPermissionPolicy.dashboardReadPermissions

    /** Future Huawei import permissions. Do not request while FeatureFlags.HUAWEI_IMPORT_ENABLED is false. */
    val importPermissions: Set<String> = HealthPermissionPolicy.huaweiImportPermissions

    private val zoneRules""",
            "GoogleHealthManager permissions",
        )

    has_all_pattern = r"\n    suspend fun hasAllPermissions\(\): Boolean \{[\s\S]*?\n    \}\n\n    suspend fun writeSnapshot"
    if re.search(has_all_pattern, text):
        text = re.sub(
            has_all_pattern,
            """
    suspend fun hasAllPermissions(): Boolean = hasPermissions(permissions, "dashboard")

    suspend fun hasImportPermissions(): Boolean = hasPermissions(importPermissions, "huawei-import")

    private suspend fun hasPermissions(required: Set<String>, purpose: String): Boolean {
        val c = healthConnectClient ?: return false
        return try {
            val granted = c.permissionController.getGrantedPermissions()
            val missingCount = required.count { it !in granted }
            AppLogger.d(TAG, "Permission check purpose=$purpose missing=$missingCount")
            missingCount == 0
        } catch (e: Exception) {
            AppLogger.e(TAG, "Permission check failed for $purpose: ${e.message}", e)
            false
        }
    }

    suspend fun writeSnapshot""",
            text,
            flags=re.S,
        )
    elif "suspend fun hasImportPermissions()" not in text:
        fail("GoogleHealthManager permission-check block not found")

    write(path, text)


def patch_sync_worker() -> None:
    path = SRC / "data" / "worker" / "SyncWorker.kt"
    if not path.exists():
        print("[SKIP] SyncWorker not found; Huawei import worker may have been removed earlier.")
        return
    text = read(path)
    text = ensure_import(text, "import com.openhealth.sync.config.FeatureFlags")

    guard = """        if (!FeatureFlags.HUAWEI_IMPORT_ENABLED) {
            AppLogger.w(TAG, "Huawei import is compiled but disabled for ${FeatureFlags.RELEASE_TRACK}")
            return Result.success()
        }

"""
    if "Huawei import is compiled but disabled" not in text:
        text = text.replace(
            "        AppLogger.i(TAG, \"Starting Huawei -> Health Connect sync\")\n\n",
            "        AppLogger.i(TAG, \"Starting Huawei -> Health Connect sync\")\n\n" + guard,
        )
    text = text.replace(
        "val googlePermissionsOk = googleManager.hasAllPermissions()",
        "val googlePermissionsOk = googleManager.hasImportPermissions()",
    )
    text = text.replace(
        "Health Connect write permissions are missing",
        "Health Connect import permissions are missing",
    )
    write(path, text)


def patch_main_activity() -> None:
    main_path = SRC / "MainActivity.kt"
    dashboard_path = SRC / "ui" / "DashboardScreen.kt"
    dashboard = read(dashboard_path)

    if "onSyncClick" in dashboard:
        dashboard_call = """                DashboardScreen(
                    viewModel = dashboardViewModel,
                    onSyncClick = { requestGooglePermissionsOrOpenProvider() }
                )"""
    else:
        dashboard_call = """                DashboardScreen(
                    viewModel = dashboardViewModel,
                    onRequestPermissions = { requestGooglePermissionsOrOpenProvider() },
                    onRefresh = { dashboardViewModel.refresh() }
                )"""

    write(
        main_path,
        f"""package com.openhealth.sync

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import com.openhealth.sync.ui.DashboardScreen
import com.openhealth.sync.ui.DashboardViewModel
import com.openhealth.sync.ui.theme.BitLutExpressiveTheme
import com.openhealth.sync.util.AppLogger

/**
 * Single-entry activity for the v1.5 dashboard-first release.
 *
 * Huawei import remains compiled behind FeatureFlags, but MainActivity deliberately exposes
 * only the Google Health Connect dashboard until Huawei Health Kit approval is granted.
 */
class MainActivity : ComponentActivity() {{

    private val dashboardViewModel: DashboardViewModel by viewModels {{
        val app = application as SyncApplication
        DashboardViewModel.provideFactory(app.container.googleHealthManager)
    }}

    private val googlePermissionLauncher = registerForActivityResult(
        PermissionController.createRequestPermissionResultContract()
    ) {{ granted ->
        AppLogger.i("MainActivity", "Health Connect permissions returned: $granted")
        dashboardViewModel.refresh()
        val app = application as SyncApplication
        if (!granted.containsAll(app.container.googleHealthManager.permissions)) {{
            Toast.makeText(this, getString(R.string.toast_hc_no_permissions), Toast.LENGTH_LONG).show()
        }}
    }}

    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        setContent {{
            BitLutExpressiveTheme {{
{dashboard_call}
            }}
        }}
    }}

    override fun onResume() {{
        super.onResume()
        dashboardViewModel.refresh()
    }}

    private fun requestGooglePermissionsOrOpenProvider() {{
        when (HealthConnectClient.getSdkStatus(this)) {{
            HealthConnectClient.SDK_AVAILABLE -> {{
                Toast.makeText(this, getString(R.string.toast_hc_opening), Toast.LENGTH_SHORT).show()
                val app = application as SyncApplication
                googlePermissionLauncher.launch(app.container.googleHealthManager.permissions)
            }}
            else -> {{
                Toast.makeText(this, getString(R.string.toast_hc_required), Toast.LENGTH_LONG).show()
                openUriWithFallback(
                    primary = "market://details?id=com.google.android.apps.healthdata",
                    fallback = "https://play.google.com/store/apps/details?id=com.google.android.apps.healthdata"
                )
            }}
        }}
    }}

    private fun openUriWithFallback(primary: String, fallback: String) {{
        runCatching {{ startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(primary))) }}
            .onFailure {{ startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(fallback))) }}
    }}
}}
""",
    )


def create_review_doc() -> None:
    write(
        ROOT / "docs" / "CODE_REVIEW_2026_V15.md",
        """# BitLut v1.5 Code Review Notes

## Product scope

v1.5 is a dashboard-first release for AppGallery review. The visible app shows Google Health Connect data only:

- steps today;
- weekly steps;
- imported workouts / Health Connect exercise sessions.

Huawei import remains in the repository and compiled codebase, but it is not reachable from navigation, permissions, or background workers until Huawei Health Kit approval is granted.

## 2026 engineering principles applied

### AID / AI-readable code

- Feature flags are centralized in `config/FeatureFlags.kt`.
- Health permissions are centralized in `config/HealthPermissionPolicy.kt`.
- `MainActivity` has one clear responsibility: dashboard entry and Health Connect permission routing.

### Clear documentation

- The staged-release contract is documented in code comments and this file.
- Future Huawei import re-enable steps should only touch feature flags, navigation, and import permission prompts.

### KISS / YAGNI / AHA

- No new abstraction layer was added for the current single-screen runtime.
- Huawei import is preserved, not reworked, because it is future capability rather than current release scope.

### Secure by Design / Zero Trust Programming

- Dashboard mode requests the minimum read-only Health Connect permission set.
- Import write permissions are defined separately and are not requested while Huawei import is disabled.
- `SyncWorker` exits successfully before any Huawei API call while the feature flag is disabled.

### Green Coding

- No periodic Huawei background sync is scheduled in the v1.5 runtime.
- Dashboard refresh remains user/session-driven instead of running unnecessary background work.

### Observability First

- `AppLogger` keeps bounded in-app logs and filters noisy debug entries from the UI.
- Worker and permission decisions log high-level state without exposing secrets.

## Re-enable Huawei import after approval

1. Set `FeatureFlags.HUAWEI_IMPORT_ENABLED = true`.
2. Restore/import navigation entry.
3. Request `googleHealthManager.importPermissions` only inside the import flow.
4. Run a real-device smoke test on a Huawei/HMS device.
5. Verify AppGallery Health Kit scopes, release SHA-256, package name, and `agconnect-services.json`.
""",
    )


def run_static_audit() -> None:
    print("\n[AUDIT] Static checks")
    required = [
        SRC / "config" / "FeatureFlags.kt",
        SRC / "config" / "HealthPermissionPolicy.kt",
        SRC / "data" / "GoogleHealthManager.kt",
        SRC / "MainActivity.kt",
    ]
    for path in required:
        if path.exists():
            print(f"[OK] {path.relative_to(ROOT)}")
        else:
            fail(f"Required file missing after patch: {path}")

    main = read(SRC / "MainActivity.kt")
    forbidden_runtime = ["setupPeriodicSync(", "WorkManager.getInstance"]
    for token in forbidden_runtime:
        if token in main:
            fail(f"MainActivity still contains runtime background sync token: {token}")
    print("[OK] MainActivity has no automatic Huawei background sync")

    worker_path = SRC / "data" / "worker" / "SyncWorker.kt"
    if worker_path.exists():
        worker = read(worker_path)
        if "FeatureFlags.HUAWEI_IMPORT_ENABLED" not in worker:
            fail("SyncWorker is missing Huawei feature-flag guard")
        print("[OK] SyncWorker is guarded by FeatureFlags.HUAWEI_IMPORT_ENABLED")

    build = read(APP / "build.gradle.kts")
    if '?: "1.5.0"' not in build:
        fail("build.gradle.kts default versionName is not 1.5.0")
    print("[OK] Default versionName is 1.5.0")


def main() -> None:
    if not APP.exists() or not SRC.exists():
        fail("Run this script from the BitLut repository root")

    print("[START] BitLut v1.5 AI-readable hardening patch")
    patch_build_gradle()
    create_feature_flags()
    create_permission_policy()
    patch_google_health_manager()
    patch_sync_worker()
    patch_main_activity()
    create_review_doc()
    run_static_audit()
    print("\n[DONE] Patch applied. Now run:")
    print("  ./gradlew :app:compileDebugKotlin --no-daemon")
    print("  ./gradlew :app:assembleDebug --no-daemon")


if __name__ == "__main__":
    main()
