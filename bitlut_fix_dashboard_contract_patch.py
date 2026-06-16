#!/usr/bin/env python3
"""
BitLut recovery patch: align MainActivity and DashboardScreen contract after stacked patches.

Goal:
- Keep Huawei import code in the repository for later Health Kit approval.
- Keep Huawei runtime hidden/disabled for AppGallery dashboard-first build.
- Use Google Health Connect dashboard only at runtime.
- Fix compile error caused by MainActivity using onRequestPermissions/onRefresh while
  the local DashboardScreen still exposes onSyncClick.

Run from the repository root:
  python3 bitlut_fix_dashboard_contract_patch.py
  ./gradlew :app:compileDebugKotlin --no-daemon
  ./gradlew :app:assembleDebug --no-daemon
"""
from pathlib import Path
import re
import shutil
from datetime import datetime

ROOT = Path.cwd()
MAIN = ROOT / "app/src/main/java/com/openhealth/sync/MainActivity.kt"
DASH = ROOT / "app/src/main/java/com/openhealth/sync/ui/DashboardScreen.kt"
FLAGS = ROOT / "app/src/main/java/com/openhealth/sync/FeatureFlags.kt"
DOC = ROOT / "docs/HUAWEI_IMPORT_REENABLE.md"

for path in (MAIN, DASH):
    if not path.exists():
        raise SystemExit(f"Missing expected file: {path}")

backup_dir = ROOT / f".bitlut_recovery_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
for path in (MAIN, DASH):
    dst = backup_dir / path.relative_to(ROOT)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)

# Feature flag: explicit source of truth. We do not delete Huawei code; we hide runtime entry points.
FLAGS.write_text(
    """package com.openhealth.sync\n\n/**\n * Runtime feature gates.\n *\n * Huawei import stays in the codebase for the Health Kit approval phase, but it must\n * remain disabled in the AppGallery dashboard-first build. Flip this only after Huawei\n * Health Kit access is approved and import QA is complete.\n */\nobject FeatureFlags {\n    const val HUAWEI_IMPORT_ENABLED: Boolean = false\n}\n""",
    encoding="utf-8",
)

# MainActivity: compile-safe, KISS, no WorkManager auto-sync, no Huawei runtime call.
# It intentionally calls DashboardScreen(onSyncClick = ...), because the current project
# variant exposes that API. The callback refreshes when permissions are present and requests
# Google Health Connect read access otherwise.
MAIN.write_text(
    """package com.openhealth.sync\n\nimport android.content.Intent\nimport android.net.Uri\nimport android.os.Bundle\nimport android.widget.Toast\nimport androidx.activity.ComponentActivity\nimport androidx.activity.compose.setContent\nimport androidx.activity.result.contract.ActivityResultContracts\nimport androidx.activity.viewModels\nimport androidx.health.connect.client.HealthConnectClient\nimport androidx.health.connect.client.PermissionController\nimport androidx.lifecycle.lifecycleScope\nimport com.openhealth.sync.ui.DashboardScreen\nimport com.openhealth.sync.ui.DashboardViewModel\nimport com.openhealth.sync.ui.theme.BitLutExpressiveTheme\nimport com.openhealth.sync.util.AppLogger\nimport kotlinx.coroutines.launch\n\nclass MainActivity : ComponentActivity() {\n\n    private val dashboardViewModel: DashboardViewModel by viewModels {\n        val app = application as SyncApplication\n        DashboardViewModel.provideFactory(app.container.googleHealthManager)\n    }\n\n    private val googlePermissionLauncher = registerForActivityResult(\n        PermissionController.createRequestPermissionResultContract()\n    ) { granted ->\n        AppLogger.i(\"MainActivity\", \"Health Connect permissions returned: $granted\")\n        dashboardViewModel.refresh()\n\n        val app = application as SyncApplication\n        if (!granted.containsAll(app.container.googleHealthManager.permissions)) {\n            Toast.makeText(this, getString(R.string.toast_hc_no_permissions), Toast.LENGTH_LONG).show()\n        }\n    }\n\n    override fun onCreate(savedInstanceState: Bundle?) {\n        super.onCreate(savedInstanceState)\n\n        setContent {\n            BitLutExpressiveTheme {\n                DashboardScreen(\n                    viewModel = dashboardViewModel,\n                    onSyncClick = { refreshOrRequestGoogleHealthPermissions() }\n                )\n            }\n        }\n    }\n\n    override fun onResume() {\n        super.onResume()\n        dashboardViewModel.refresh()\n    }\n\n    private fun refreshOrRequestGoogleHealthPermissions() {\n        lifecycleScope.launch {\n            val app = application as SyncApplication\n            if (app.container.googleHealthManager.hasAllPermissions()) {\n                dashboardViewModel.refresh()\n            } else {\n                requestGooglePermissionsOrOpenProvider()\n            }\n        }\n    }\n\n    private fun requestGooglePermissionsOrOpenProvider() {\n        val status = HealthConnectClient.getSdkStatus(this)\n        if (status == HealthConnectClient.SDK_AVAILABLE) {\n            Toast.makeText(this, getString(R.string.toast_hc_opening), Toast.LENGTH_SHORT).show()\n            val app = application as SyncApplication\n            googlePermissionLauncher.launch(app.container.googleHealthManager.permissions)\n        } else {\n            Toast.makeText(this, getString(R.string.toast_hc_required), Toast.LENGTH_LONG).show()\n            openUriWithFallback(\n                \"market://details?id=com.google.android.apps.healthdata\",\n                \"https://play.google.com/store/apps/details?id=com.google.android.apps.healthdata\"\n            )\n        }\n    }\n\n    private fun openUriWithFallback(primary: String, fallback: String) {\n        runCatching { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(primary))) }\n            .onFailure { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(fallback))) }\n    }\n}\n""",
    encoding="utf-8",
)

# DashboardScreen: make the button/callback naming less misleading while preserving API.
dash = DASH.read_text(encoding="utf-8")
# Keep signature compatible with current project state, but ensure no accidental Huawei wording remains.
dash = dash.replace("Huawei Health intelligence dashboard", "Google Health intelligence dashboard")
dash = dash.replace("Google Health intelligence dashboard", "Google Health intelligence dashboard")
dash = dash.replace("Connect Huawei Health", "Connect Google Health")
dash = dash.replace("Huawei Health", "Google Health")
dash = dash.replace("Sync now", "Refresh")
dash = dash.replace("Start sync", "Connect")
dash = dash.replace("onSyncClick", "onSyncClick")
DASH.write_text(dash, encoding="utf-8")

DOC.parent.mkdir(parents=True, exist_ok=True)
DOC.write_text(
    """# Huawei import re-enable checklist\n\nHuawei import is intentionally preserved in the source tree and hidden at runtime.\n\nCurrent AppGallery approval build:\n\n- visible product: Google Health Connect dashboard\n- visible data: daily steps, weekly steps, imported workouts\n- hidden feature: Huawei Health import\n- disabled runtime: WorkManager Huawei sync / automatic Huawei import\n- feature flag: `FeatureFlags.HUAWEI_IMPORT_ENABLED = false`\n\nAfter Huawei Health Kit approval:\n\n1. Confirm AppGallery package name, SHA-256 fingerprint, Health Kit approval, and `agconnect-services.json`.\n2. Run Huawei import QA on a Huawei/HMS device.\n3. Flip `FeatureFlags.HUAWEI_IMPORT_ENABLED` to `true`.\n4. Re-enable the import entry point in navigation/sidebar only after QA passes.\n5. Request write permissions only in the import flow, not for dashboard-only browsing.\n""",
    encoding="utf-8",
)

print("OK: repaired MainActivity/DashboardScreen contract.")
print(f"Backup saved to: {backup_dir.relative_to(ROOT)}")
print("Next: ./gradlew :app:compileDebugKotlin --no-daemon")
