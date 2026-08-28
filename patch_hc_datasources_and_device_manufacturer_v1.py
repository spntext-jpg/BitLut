#!/usr/bin/env python3
"""
patch_hc_datasources_and_device_manufacturer_v1.py

Implements two of the diagnostic fixes discussed for the corporate-app
import-visibility problem (2026-08-27):

1. Health Connect "data sources" deep link. Health Connect requires a
   writing app to be explicitly added as a contributing data source for
   each category (Steps, Distance, Exercise, etc.) via its own
   "Manage data > Data sources and priority" screen -- a separate consent
   step from the runtime read/write permission grant BitLut already
   requests. A record can exist in the Health Connect store and be visible
   to BitLut itself the moment the permission is granted, while still not
   counting toward totals a third-party reader relies on, if BitLut was
   never added there. BitLut never surfaced a path to that screen before
   this patch, even though the manifest already declares the
   `androidx.health.ACTION_HEALTH_CONNECT_SETTINGS` query intent needed to
   launch it. This patch adds:
     - GoogleHealthManager.healthConnectSettingsIntent(): builds the intent
       (verified against Health Connect's own documented usage of
       HealthConnectClient.ACTION_HEALTH_CONNECT_SETTINGS).
     - MainActivity.openHealthConnectSettings(): launches it via a plain
       startActivity, wrapped in the same try/catch style as
       startHuaweiAuthorization(), reusing the existing (previously
       zero-call-site) toast_hc_launch_failed string for failures.
     - A new diagnostic card in Settings (reusing the existing
       SettingsConnectionCard composable, single action, no secondary),
       wired through FinalBitLutShell -> SettingsScreen via a new
       onOpenHealthConnectSettings callback parameter.
   This is diagnostic, not a guaranteed fix: it gets the user to the right
   screen instead of leaving them with no path there at all.

2. Device manufacturer metadata. bitlutRecordingDevice was
   Device(type = Device.TYPE_UNKNOWN) with no manufacturer/model. Per
   Health Connect's own metadata guidance, supplying manufacturer/model
   (not just type) "helps with attribution in reader applications, so
   users can understand which device or application recorded their data."
   This patch sets manufacturer = "Huawei" (verified as a supported named
   constructor parameter against Health Connect's documented Device usage
   examples), since that much is genuinely true regardless of which
   specific Huawei phone or wearable recorded the data. model is
   deliberately left unset -- BitLut has no reliable per-record model
   signal to report, so guessing one would not be honest the same way
   "Huawei" is.

Both fixes were chosen from a longer list of candidate causes as the
cheapest, safest, most broadly-applicable ones with no new permissions and
no behavior change beyond what's described above. Neither can be verified
from this sandbox to actually resolve the corporate app's import issue --
only a real device and the corporate app's own behavior can confirm that.

Usage:
    python3 patch_hc_datasources_and_device_manufacturer_v1.py

Behavior:
    1. Backs up every touched file to .bitlut_patch_backup/
    2. Applies text-anchored edits to GoogleHealthManager.kt, MainActivity.kt,
       FinalBitLutShell.kt, and both strings.xml files
    3. Runs :app:compileDebugKotlin as a compile gate
    4. On success: git add -A && git commit && git push origin HEAD:main
    5. On failure: dies with a clear message, no commit, no push
    6. Idempotent: safe to run twice; second run reports "already applied"
"""

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
GOOGLE_HEALTH_KT = REPO_ROOT / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt"
MAIN_ACTIVITY_KT = REPO_ROOT / "app/src/main/java/com/openhealth/sync/MainActivity.kt"
SHELL_KT = REPO_ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
STRINGS_EN = REPO_ROOT / "app/src/main/res/values/strings.xml"
STRINGS_RU = REPO_ROOT / "app/src/main/res/values-ru/strings.xml"
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


def backup_file(path: Path) -> None:
    if not path.exists():
        die(f"Cannot back up missing file: {path}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:10]
    dest = BACKUP_DIR / f"{path.name}.{digest}.bak"
    if not dest.exists():
        shutil.copy2(path, dest)
        print(f"Backed up {path} -> {dest}")
    else:
        print(f"Backup already exists at {dest}, leaving it in place")


def apply_edit(path: Path, old: str, new: str) -> bool:
    """
    Genuine replacement helper (exact-occurrence-count check on old_str
    only). Use this ONLY when old_str is fully consumed/transformed by the
    edit, i.e. old_str does NOT survive as a substring of new_str. Returns
    True if applied, False if already applied (idempotent skip). Dies on
    any other state.
    """
    text = path.read_text(encoding="utf-8")
    old_count = text.count(old)

    if old_count == 1:
        text = text.replace(old, new, 1)
        path.write_text(text, encoding="utf-8")
        return True

    if old_count == 0:
        return False

    die(
        "Unexpected file state for edit.\n"
        f"  old_str occurrences: {old_count} (expected exactly 1 pre-patch or 0 post-patch)\n"
        f"  file: {path}\n"
        "Refusing to guess; inspect the file manually."
    )


def apply_insertion(path: Path, anchor: str, new_with_anchor: str, unique_marker: str) -> bool:
    """
    Pure-insertion helper: use this whenever anchor survives unchanged as a
    substring of new_with_anchor (i.e. the edit only adds text next to an
    anchor rather than replacing it). Using apply_edit for this case is a
    real, previously-hit bug: anchor's occurrence count stays 1 after the
    insertion (it's still there, untouched), so an exact-count check keyed
    on the anchor alone would reapply the insertion forever, duplicating it
    on every run.

    Idempotency here is keyed on unique_marker instead: a substring that
    exists ONLY inside new_with_anchor's added text, never in the
    surrounding unpatched file. unique_marker present -> already inserted,
    skip. unique_marker absent and anchor present exactly once -> insert.
    Anything else is a real anomaly.
    """
    text = path.read_text(encoding="utf-8")
    marker_count = text.count(unique_marker)

    if marker_count >= 1:
        return False

    anchor_count = text.count(anchor)
    if anchor_count == 1:
        text = text.replace(anchor, new_with_anchor, 1)
        path.write_text(text, encoding="utf-8")
        return True

    die(
        "Unexpected file state for insertion.\n"
        f"  unique_marker occurrences: {marker_count} (expected 0 pre-patch)\n"
        f"  anchor occurrences: {anchor_count} (expected exactly 1 pre-patch)\n"
        f"  file: {path}\n"
        "Refusing to guess; inspect the file manually."
    )



def run(cmd: list, cwd: Path) -> None:
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        die(f"Command failed ({result.returncode}): {' '.join(cmd)}")


# ---------------------------------------------------------------------------
# GoogleHealthManager.kt edits
# ---------------------------------------------------------------------------

GHM_EDIT_1_OLD = '''    fun findInstalledHcPackage(): String? {
        for (packageName in HC_PACKAGES) {
            try {
                context.packageManager.getPackageInfo(packageName, 0)
                AppLogger.d(TAG, "Found Health Connect package: $packageName")
                return packageName
            } catch (_: PackageManager.NameNotFoundException) {
                AppLogger.d(TAG, "Health Connect package not found: $packageName")
            }
        }
        return null
    }

'''

GHM_EDIT_1_NEW = '''    fun findInstalledHcPackage(): String? {
        for (packageName in HC_PACKAGES) {
            try {
                context.packageManager.getPackageInfo(packageName, 0)
                AppLogger.d(TAG, "Found Health Connect package: $packageName")
                return packageName
            } catch (_: PackageManager.NameNotFoundException) {
                AppLogger.d(TAG, "Health Connect package not found: $packageName")
            }
        }
        return null
    }

    /**
     * Sprint 2026-08-27: opens Health Connect's own settings screen, from
     * which the user can reach "Manage data > Data sources and priority".
     * This is a distinct, separate consent step from the runtime read/write
     * permission grant BitLut already requests: Health Connect requires a
     * writing app to be explicitly added as a contributing data source for
     * each category (Steps, Distance, Exercise, etc.) before its records
     * count toward totals a reader relies on, even though the records exist
     * in the store and are visible to BitLut itself the moment the runtime
     * permission is granted. This was a plausible, previously-unaddressed
     * reason a third-party reader could show no BitLut-synced activity: the
     * permission grant alone does not guarantee BitLut is listed there.
     *
     * `ACTION_HEALTH_CONNECT_SETTINGS` (declared as
     * `androidx.health.ACTION_HEALTH_CONNECT_SETTINGS` in the manifest's
     * `<queries>` block already, for this exact purpose) opens Health
     * Connect's general settings screen; Health Connect does not currently
     * expose a stable, documented deep link straight into the data-sources
     * sub-screen, so this is the closest available entry point. The caller
     * (MainActivity) is responsible for wrapping startActivity in a
     * try/catch, matching the existing pattern for the Huawei authorization
     * intent below.
     */
    fun healthConnectSettingsIntent(): android.content.Intent =
        android.content.Intent(HealthConnectClient.ACTION_HEALTH_CONNECT_SETTINGS)

'''

GHM_EDIT_2_OLD = '''     * free to treat RECORDING_METHOD_UNKNOWN as untrustworthy and skip
     * importing it, which matches a real corporate-app report of BitLut's
     * synced workouts being invisible there despite being visible in Google
     * Fit. `Device(type = Device.TYPE_UNKNOWN)` is used rather than guessing
     * a manufacturer/model: BitLut runs on the phone relaying data that
     * Huawei Health already attributed to whatever wearable or phone
     * actually recorded it, so BitLut has no reliable device-type signal of
     * its own to report.
     */
    private val bitlutRecordingDevice = Device(type = Device.TYPE_UNKNOWN)'''

GHM_EDIT_2_NEW = '''     * free to treat RECORDING_METHOD_UNKNOWN as untrustworthy and skip
     * importing it, which matches a real corporate-app report of BitLut's
     * synced workouts being invisible there despite being visible in Google
     * Fit.
     *
     * Sprint 2026-08-27: `manufacturer = "Huawei"` added (model deliberately
     * left unset). Per Health Connect's own metadata guidance, supplying
     * manufacturer/model -- not just `type` -- "helps with attribution in
     * reader applications, so users can understand which device or
     * application recorded their data," and is one of the plausible,
     * previously-unaddressed reasons a stricter third-party reader might
     * decline a record whose device info is empty beyond TYPE_UNKNOWN.
     * "Huawei" is used rather than a specific model because that much is
     * genuinely true regardless of which Huawei phone or wearable actually
     * recorded the data -- BitLut relays whatever Huawei Health already
     * attributed the activity to, and has no reliable per-record model
     * signal of its own to report. Guessing a specific model would not be
     * true in the same way, so `model` is deliberately left unset;
     * `Device.TYPE_UNKNOWN` remains correct for the same reason.
     */
    private val bitlutRecordingDevice = Device(type = Device.TYPE_UNKNOWN, manufacturer = "Huawei")'''

GHM_EDITS = [
    ("add healthConnectSettingsIntent()", "insert", GHM_EDIT_1_OLD, GHM_EDIT_1_NEW, "fun healthConnectSettingsIntent()"),
    ("add manufacturer to bitlutRecordingDevice", "edit", GHM_EDIT_2_OLD, GHM_EDIT_2_NEW),
]

# ---------------------------------------------------------------------------
# MainActivity.kt edits
# ---------------------------------------------------------------------------

MA_EDIT_1_OLD = '''                    onSyncNow = { triggerImmediateSync() },
                    onExportCsv = { exportCsv() },
'''

MA_EDIT_1_NEW = '''                    onSyncNow = { triggerImmediateSync() },
                    onExportCsv = { exportCsv() },
                    onOpenHealthConnectSettings = { openHealthConnectSettings() },
'''

MA_EDIT_2_OLD = '''    private fun startHuaweiAuthorization() {'''

MA_EDIT_2_NEW = '''    /**
     * Sprint 2026-08-27: opens Health Connect's own settings screen so the
     * user can check "Manage data > Data sources and priority" -- see the
     * doc comment on GoogleHealthManager.healthConnectSettingsIntent() for
     * why this is a distinct step from BitLut's own runtime permission
     * grant. syncViewModel.googleManager is declared as the
     * HealthConnectManager interface, which does not expose this
     * GoogleHealthManager-specific function -- same reason exportCsv()
     * above casts to the concrete type. AppContainer always constructs a
     * real GoogleHealthManager, so this cast is safe in practice; the
     * null-check is defensive only. No ActivityResultLauncher/onResult
     * handling is needed here (unlike Huawei's authorization intent):
     * Health Connect's own settings screen returns no result BitLut acts
     * on, so a plain startActivity is enough, wrapped in the same
     * try/catch pattern as startHuaweiAuthorization above in case Health
     * Connect itself is missing or the intent otherwise fails to resolve.
     */
    private fun openHealthConnectSettings() {
        try {
            val googleManager = syncViewModel.googleManager as? com.openhealth.sync.data.GoogleHealthManager
            if (googleManager == null) {
                Toast.makeText(this, getString(R.string.toast_hc_launch_failed), Toast.LENGTH_LONG).show()
                return
            }
            startActivity(googleManager.healthConnectSettingsIntent())
        } catch (e: Exception) {
            AppLogger.e("MainActivity", "Opening Health Connect settings failed: ${e.message}", e)
            Toast.makeText(this, getString(R.string.toast_hc_launch_failed), Toast.LENGTH_LONG).show()
        }
    }

    private fun startHuaweiAuthorization() {'''

MA_EDITS = [
    ("wire onOpenHealthConnectSettings into FinalBitLutShell call", "insert", MA_EDIT_1_OLD, MA_EDIT_1_NEW, "onOpenHealthConnectSettings = { openHealthConnectSettings() }"),
    ("add openHealthConnectSettings()", "insert", MA_EDIT_2_OLD, MA_EDIT_2_NEW, "private fun openHealthConnectSettings()"),
]

# ---------------------------------------------------------------------------
# FinalBitLutShell.kt edits
# ---------------------------------------------------------------------------

SHELL_EDIT_1_OLD = '''    onSyncNow: () -> Unit,
    onExportCsv: () -> Unit = {},
'''

SHELL_EDIT_1_NEW = '''    onSyncNow: () -> Unit,
    onExportCsv: () -> Unit = {},
    onOpenHealthConnectSettings: () -> Unit = {},
'''

SHELL_EDIT_2_OLD = '''                MainTab.Settings -> SettingsScreen(palette, syncState, onRefresh, wrappedOnRequestGoogle, onRequestHuawei, onSyncNow,
                    onImportArchive = { showArchiveImport = true },
                    onExportCsv = onExportCsv,
'''

SHELL_EDIT_2_NEW = '''                MainTab.Settings -> SettingsScreen(palette, syncState, onRefresh, wrappedOnRequestGoogle, onRequestHuawei, onSyncNow,
                    onImportArchive = { showArchiveImport = true },
                    onExportCsv = onExportCsv,
                    onOpenHealthConnectSettings = onOpenHealthConnectSettings,
'''

SHELL_EDIT_3_OLD = '''    onImportArchive: () -> Unit,
    onExportCsv: () -> Unit,
'''

SHELL_EDIT_3_NEW = '''    onImportArchive: () -> Unit,
    onExportCsv: () -> Unit,
    onOpenHealthConnectSettings: () -> Unit,
'''

SHELL_EDIT_4_OLD = '''        SettingsConnectionCard(
            palette = palette,
            title = stringResource(R.string.manual_sync_title),
            accent = HealthAccent.violet(),
            icon = Icons.Rounded.CloudSync,
            primaryAction = stringResource(R.string.sync_now),
            onPrimaryAction = onSyncNow,
            secondaryAction = stringResource(R.string.import_archive_title),
            onSecondaryAction = onImportArchive
        )
'''

SHELL_EDIT_4_NEW = '''        SettingsConnectionCard(
            palette = palette,
            title = stringResource(R.string.manual_sync_title),
            accent = HealthAccent.violet(),
            icon = Icons.Rounded.CloudSync,
            primaryAction = stringResource(R.string.sync_now),
            onPrimaryAction = onSyncNow,
            secondaryAction = stringResource(R.string.import_archive_title),
            onSecondaryAction = onImportArchive
        )

        // Sprint 2026-08-27: a corporate/third-party Health Connect reader
        // not counting BitLut-synced workouts can be caused by BitLut never
        // being added as a data source for a given category in Health
        // Connect's own settings -- a separate consent step from the
        // runtime permission grant above. See the doc comment on
        // GoogleHealthManager.healthConnectSettingsIntent() for the full
        // rationale. This card is diagnostic, not a fix in itself: it just
        // gets the user to the right screen instead of leaving them with no
        // path there at all.
        SettingsConnectionCard(
            palette = palette,
            title = stringResource(R.string.health_connect_data_sources_title),
            accent = HealthAccent.mind(),
            icon = Icons.Rounded.Cloud,
            primaryAction = stringResource(R.string.health_connect_data_sources_button),
            onPrimaryAction = onOpenHealthConnectSettings
        )
'''

SHELL_EDITS = [
    ("add onOpenHealthConnectSettings param to FinalBitLutShell", "insert", SHELL_EDIT_1_OLD, SHELL_EDIT_1_NEW, "onOpenHealthConnectSettings: () -> Unit = {},"),
    ("thread onOpenHealthConnectSettings into SettingsScreen call", "insert", SHELL_EDIT_2_OLD, SHELL_EDIT_2_NEW, "onOpenHealthConnectSettings = onOpenHealthConnectSettings,"),
    ("add onOpenHealthConnectSettings param to SettingsScreen", "insert", SHELL_EDIT_3_OLD, SHELL_EDIT_3_NEW, "    onOpenHealthConnectSettings: () -> Unit,\n"),
    ("add Health Connect data sources card", "insert", SHELL_EDIT_4_OLD, SHELL_EDIT_4_NEW, "R.string.health_connect_data_sources_title"),
]

# ---------------------------------------------------------------------------
# strings.xml edits
# ---------------------------------------------------------------------------

EN_EDITS = [
    (
        "add health_connect_data_sources_* strings (EN)",
        "insert",
        '''    <string name="import_archive_title">Import archive</string>''',
        '''    <string name="import_archive_title">Import archive</string>
    <string name="health_connect_data_sources_title">Health Connect data sources</string>
    <string name="health_connect_data_sources_button">Open Health Connect settings</string>''',
        "health_connect_data_sources_title",
    ),
]

RU_EDITS = [
    (
        "add health_connect_data_sources_* strings (RU)",
        "insert",
        '''    <string name="import_archive_title">Импорт архива</string>''',
        '''    <string name="import_archive_title">Импорт архива</string>
    <string name="health_connect_data_sources_title">Источники данных Health Connect</string>
    <string name="health_connect_data_sources_button">Открыть настройки Health Connect</string>''',
        "health_connect_data_sources_title",
    ),
]


def apply_edit_group(label: str, path: Path, edits: list) -> bool:
    """
    edits: list of tuples, either
      (name, "edit", old, new)          -> genuine replacement
      (name, "insert", anchor, new_with_anchor, unique_marker) -> pure insertion
    """
    if not path.exists():
        die(f"Target file not found: {path}")
    backup_file(path)
    any_applied = False
    for edit in edits:
        kind = edit[1]
        name = edit[0]
        if kind == "edit":
            _, _, old, new = edit
            applied = apply_edit(path, old, new)
        elif kind == "insert":
            _, _, anchor, new_with_anchor, unique_marker = edit
            applied = apply_insertion(path, anchor, new_with_anchor, unique_marker)
        else:
            die(f"Unknown edit kind '{kind}' for '{name}'")
        print(f"  [{label}] {name}: {'applied' if applied else 'already applied, skipped'}")
        any_applied = any_applied or applied
    return any_applied


def main() -> None:
    changed = False

    changed |= apply_edit_group("GoogleHealthManager.kt", GOOGLE_HEALTH_KT, GHM_EDITS)
    changed |= apply_edit_group("MainActivity.kt", MAIN_ACTIVITY_KT, MA_EDITS)
    changed |= apply_edit_group("FinalBitLutShell.kt", SHELL_KT, SHELL_EDITS)
    changed |= apply_edit_group("strings.xml", STRINGS_EN, EN_EDITS)
    changed |= apply_edit_group("strings.xml (ru)", STRINGS_RU, RU_EDITS)

    if not changed:
        print("Already applied -- nothing to do, skipping compile/commit/push.")
        return

    gradlew = REPO_ROOT / "gradlew"
    if not gradlew.exists():
        die(f"gradlew not found at {gradlew}; cannot run compile gate.")

    run(
        [
            str(gradlew),
            ":app:compileDebugKotlin",
            "--no-daemon",
            "--max-workers=1",
            "--no-watch-fs",
            "--console=plain",
            "-Dorg.gradle.jvmargs=-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8",
            "-Pkotlin.compiler.execution.strategy=in-process",
        ],
        cwd=REPO_ROOT,
    )

    print("Compile gate passed. Committing and pushing.")
    run(["git", "add", "-A"], cwd=REPO_ROOT)
    run(
        [
            "git",
            "commit",
            "-m",
            "Add Health Connect data-sources settings deep link in Settings; "
            "set Device manufacturer=Huawei on synced records",
        ],
        cwd=REPO_ROOT,
    )
    run(["git", "push", "origin", "HEAD:main"], cwd=REPO_ROOT)
    print("Done.")


if __name__ == "__main__":
    main()
