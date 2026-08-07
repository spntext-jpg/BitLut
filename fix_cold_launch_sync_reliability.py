#!/usr/bin/env python3
"""
BitLut patch: 2026-08-07 session -- cold-launch sync reliability.

Diagnosed from a real device log (Xiaomi M2102K1G, Android 13, app 1.11.2)
showing a degraded cold-launch sync: five separate SyncWorker executions
inside 30 seconds, one cancelled by WorkManager immediately after starting,
and two Huawei categories (daily steps, activity sessions) failing with a
"client is not connected" style error in that first attempt only.

IMPORTANT: an earlier pass at this diagnosis in the same chat session
mistakenly treated some of this as already fixed in the codebase (an
onResume() guard, a WorkManager KEEP policy, a Huawei retry helper) --
that was wrong. None of it existed. This script was rewritten from
scratch against the actual uploaded repomix export and every anchor
below was verified line-for-line against that real source before this
script was finalized. All three fixes are genuinely new code.

Three independent, low-risk fixes, none of which touch SyncWindowPlanner
or the lease system (SyncReliability.kt) -- untouched here, per project
rules:

1. MainActivity.kt: onResume() unconditionally re-triggered a sync, with
   no way to tell a genuine "back to the app" resume apart from a system
   permission/authorization screen (POST_NOTIFICATIONS, Health Connect,
   Huawei auth) closing and returning control to the same screen. Adds an
   awaitingSystemResult guard, set right before launching any of those
   three flows and cleared as soon as each one's result callback fires.
   requestGoogleHealthPermissions() (config package) already returns a
   Boolean specifically meant for this -- its own doc comment says so --
   but MainActivity was discarding that return value; this wires it up.

2. BackgroundSyncScheduler.kt: schedulePeriodic() runs on every cold
   launch and re-enqueued the periodic sync with
   ExistingPeriodicWorkPolicy.UPDATE, which can cancel a currently RUNNING
   instance of that same periodic work to apply the "update" -- even when
   the request is byte-for-byte identical, which it always is here. This
   matches the exact log timing (the cancellation fires the same second as
   the periodic-schedule log line). Switches to KEEP, with a one-time
   versioned-unique-name migration (same pattern already used for the
   manual-sync queue in this same file) so any already-scheduled instance
   from a previous UPDATE-policy version is cleanly replaced once, not
   fought with on every future launch.

3. HuaweiHealthManager.kt: adds a connection-race retry helper and wraps
   the two Huawei calls the log showed failing right after cold launch
   (daily step summation, activity-session records) so a transient
   "client is not connected" error gets retried (up to twice) instead of
   either silently dropping that sync attempt's step data or being
   misreported as a 50005 scope denial for workouts.

Run from the repo root:
    python3 fix_cold_launch_sync_reliability.py
"""
import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

TARGET_FILES = [
    "app/src/main/java/com/openhealth/sync/MainActivity.kt",
    "app/src/main/java/com/openhealth/sync/data/worker/BackgroundSyncScheduler.kt",
    "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt",
    "app/src/main/java/com/openhealth/sync/config/GoogleHealthPermissionRequester.kt",
]

# Round 2: fixes 2 real compileDebugKotlin errors reported against the round-1
# version of this script: (1) requestGoogleHealthPermissions() didn't actually
# return Boolean yet -- MainActivity.kt:221 assigned its Unit result to a
# Boolean var; now genuinely changed to return Boolean, with a return value
# at every exit path. (2) HuaweiHealthManager.kt's new retryOnConnectionRace()
# calls delay(), but kotlinx.coroutines.delay was never imported in that file
# -- HuaweiHealthManager.kt:389: Unresolved reference 'delay'. Now imported.


def die(msg: str) -> None:
    print(f"!! {msg}")
    sys.exit(1)


def backup_file(rel_path: str) -> None:
    src = ROOT / rel_path
    dst = BACKUP_DIR / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def apply_edit(rel_path: str, old: str, new: str, desc: str) -> bool:
    """Regex-anchored (plain substring) replacement, exactly 1 occurrence.

    Checks the OLD anchor's count first; NEW-presence is only consulted as
    a fallback once OLD is confirmed absent.
    """
    path = ROOT / rel_path
    text = path.read_text(encoding="utf-8")

    old_count = text.count(old)
    if old_count == 0:
        if text.count(new) >= 1:
            print(f"   (already applied, skipping) {desc}")
            return False
        die(f"Anchor not found for '{desc}' in {rel_path}, and patched text "
            f"is also absent. File may have changed since this script was "
            f"written -- aborting rather than guessing.")

    if old_count != 1:
        die(f"Expected exactly 1 occurrence of anchor for '{desc}' in "
            f"{rel_path}, found {old_count}. Aborting rather than guessing "
            f"which one to patch.")

    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"   applied: {desc}")
    return True


def patch_main_activity() -> None:
    rel = "app/src/main/java/com/openhealth/sync/MainActivity.kt"
    print("==> MainActivity.kt: adding awaitingSystemResult guard")

    apply_edit(
        rel,
        old='    private val syncOrchestrator: SyncOrchestrator by lazy {\n'
            '        SyncOrchestrator(this, syncViewModel.googleManager)\n'
            '    }\n'
            '\n'
            '\n'
            '    private val notificationPermissionLauncher =\n'
            '        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->\n'
            '            AppLogger.i("MainActivity", "POST_NOTIFICATIONS permission result: $granted")\n'
            '            // No toast either way: this permission is optional polish (goal\n'
            '            // reminders, streak/record celebrations), not something the core\n'
            '            // sync flow depends on, so a denial should not interrupt the\n'
            '            // person with an error-style message.\n'
            '        }\n'
            '\n'
            '    private val googlePermissionLauncher = registerForActivityResult(\n'
            '        PermissionController.createRequestPermissionResultContract()\n'
            '    ) { granted ->\n'
            '        AppLogger.i("MainActivity", "Health Connect permissions returned: $granted")\n'
            '        syncViewModel.refreshStatuses()\n'
            '        dashboardViewModel.refresh()\n'
            '\n'
            '        if (!granted.containsAll(syncViewModel.googleManager.permissions)) {\n'
            '            Toast.makeText(this, getString(R.string.toast_hc_permissions), Toast.LENGTH_LONG).show()\n'
            '        }\n'
            '    }\n'
            '\n'
            '    private val huaweiAuthorizationLauncher =\n'
            '        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->\n'
            '            val success = syncViewModel.huaweiHealthManager.handleAuthorizationResult(',
        new='    private val syncOrchestrator: SyncOrchestrator by lazy {\n'
            '        SyncOrchestrator(this, syncViewModel.googleManager)\n'
            '    }\n'
            '\n'
            '    /**\n'
            '     * onResume() is meant to catch a genuine "person switched back to the\n'
            '     * app" event and kick off a fresh sync. A system permission dialog\n'
            '     * (POST_NOTIFICATIONS) or a full-screen flow the app itself launched\n'
            '     * (Health Connect permissions, Huawei authorization) also triggers\n'
            '     * onResume() when it returns -- but that is not the person "coming\n'
            '     * back", it\'s this same screen resuming right where it left off. A\n'
            '     * real device log showed several redundant sync triggers firing back\n'
            '     * to back right after a cold launch (five separate SyncWorker\n'
            '     * executions inside 30 seconds, several of them manual-sync triggers\n'
            '     * competing for the sync lease with the periodic one) -- consistent\n'
            '     * with onResume() unconditionally re-triggering a sync every time one\n'
            '     * of these system screens closes. Set to true right before launching\n'
            '     * any of those three flows, reset to false as soon as its result\n'
            '     * callback fires (or immediately, if the launch itself failed to\n'
            '     * start and no result will ever arrive).\n'
            '     */\n'
            '    private var awaitingSystemResult = false\n'
            '\n'
            '    private val notificationPermissionLauncher =\n'
            '        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->\n'
            '            awaitingSystemResult = false\n'
            '            AppLogger.i("MainActivity", "POST_NOTIFICATIONS permission result: $granted")\n'
            '            // No toast either way: this permission is optional polish (goal\n'
            '            // reminders, streak/record celebrations), not something the core\n'
            '            // sync flow depends on, so a denial should not interrupt the\n'
            '            // person with an error-style message.\n'
            '        }\n'
            '\n'
            '    private val googlePermissionLauncher = registerForActivityResult(\n'
            '        PermissionController.createRequestPermissionResultContract()\n'
            '    ) { granted ->\n'
            '        awaitingSystemResult = false\n'
            '        AppLogger.i("MainActivity", "Health Connect permissions returned: $granted")\n'
            '        syncViewModel.refreshStatuses()\n'
            '        dashboardViewModel.refresh()\n'
            '\n'
            '        if (!granted.containsAll(syncViewModel.googleManager.permissions)) {\n'
            '            Toast.makeText(this, getString(R.string.toast_hc_permissions), Toast.LENGTH_LONG).show()\n'
            '        }\n'
            '    }\n'
            '\n'
            '    private val huaweiAuthorizationLauncher =\n'
            '        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->\n'
            '            awaitingSystemResult = false\n'
            '            val success = syncViewModel.huaweiHealthManager.handleAuthorizationResult(',
        desc="add awaitingSystemResult flag + reset it in all 3 result-launcher callbacks",
    )

    apply_edit(
        rel,
        old='    override fun onResume() {\n'
            '        super.onResume()\n'
            '        refreshUiStatusOnLaunch()\n'
            '        triggerAutomaticSyncOnLaunch()\n'
            '    }',
        new='    override fun onResume() {\n'
            '        super.onResume()\n'
            '        refreshUiStatusOnLaunch()\n'
            '        if (awaitingSystemResult) {\n'
            '            AppLogger.i("MainActivity", "Skipping onResume auto-sync: a system permission/authorization screen is still in progress")\n'
            '        } else {\n'
            '            triggerAutomaticSyncOnLaunch()\n'
            '        }\n'
            '    }',
        desc="gate onResume()'s auto-sync trigger behind the guard",
    )

    apply_edit(
        rel,
        old='    private fun requestGoogleHealthPermissions() {\n'
            '        com.openhealth.sync.config.requestGoogleHealthPermissions(\n'
            '            context = this,\n'
            '            googleManager = syncViewModel.googleManager,\n'
            '            launcher = googlePermissionLauncher\n'
            '        )\n'
            '    }',
        new='    private fun requestGoogleHealthPermissions() {\n'
            '        awaitingSystemResult = com.openhealth.sync.config.requestGoogleHealthPermissions(\n'
            '            context = this,\n'
            '            googleManager = syncViewModel.googleManager,\n'
            '            launcher = googlePermissionLauncher\n'
            '        )\n'
            '    }',
        desc="capture requestGoogleHealthPermissions()'s return value into the guard",
    )

    apply_edit(
        rel,
        old='            huaweiAuthorizationLauncher.launch(syncViewModel.huaweiHealthManager.getAuthorizationIntent())\n'
            '        } catch (e: Exception) {\n'
            '            AppLogger.e("MainActivity", "Huawei authorization start failed: ${e.message}", e)\n'
            '            Toast.makeText(this, getString(R.string.toast_huawei_start_failed), Toast.LENGTH_LONG).show()\n'
            '        }\n'
            '    }',
        new='            awaitingSystemResult = true\n'
            '            huaweiAuthorizationLauncher.launch(syncViewModel.huaweiHealthManager.getAuthorizationIntent())\n'
            '        } catch (e: Exception) {\n'
            '            awaitingSystemResult = false\n'
            '            AppLogger.e("MainActivity", "Huawei authorization start failed: ${e.message}", e)\n'
            '            Toast.makeText(this, getString(R.string.toast_huawei_start_failed), Toast.LENGTH_LONG).show()\n'
            '        }\n'
            '    }',
        desc="set the guard before launching Huawei authorization, clear it if the launch itself throws",
    )

    apply_edit(
        rel,
        old='        if (!granted) {\n'
            '            notificationPermissionLauncher.launch(android.Manifest.permission.POST_NOTIFICATIONS)\n'
            '        }',
        new='        if (!granted) {\n'
            '            awaitingSystemResult = true\n'
            '            notificationPermissionLauncher.launch(android.Manifest.permission.POST_NOTIFICATIONS)\n'
            '        }',
        desc="set the guard before launching the POST_NOTIFICATIONS system dialog",
    )


def patch_background_sync_scheduler() -> None:
    rel = "app/src/main/java/com/openhealth/sync/data/worker/BackgroundSyncScheduler.kt"
    print("==> BackgroundSyncScheduler.kt: periodic sync UPDATE -> versioned KEEP")

    apply_edit(
        rel,
        old='    const val UNIQUE_SYNC_NOW = "bitlut_sync_now_v2"\n'
            '    private const val LEGACY_UNIQUE_SYNC_NOW = "bitlut_sync_now"\n'
            '    const val UNIQUE_PERIODIC_SYNC = "bitlut_periodic_sync"\n'
            '    const val UNIQUE_EVENING_REMINDER = "bitlut_evening_reminder"\n'
            '\n'
            '    private const val KEY_MANUAL_QUEUE_V2_MIGRATED = "manual_sync_queue_v2_migrated"',
        new='    const val UNIQUE_SYNC_NOW = "bitlut_sync_now_v2"\n'
            '    private const val LEGACY_UNIQUE_SYNC_NOW = "bitlut_sync_now"\n'
            '    const val UNIQUE_PERIODIC_SYNC = "bitlut_periodic_sync_v2"\n'
            '    private const val LEGACY_UNIQUE_PERIODIC_SYNC = "bitlut_periodic_sync"\n'
            '    const val UNIQUE_EVENING_REMINDER = "bitlut_evening_reminder"\n'
            '\n'
            '    private const val KEY_MANUAL_QUEUE_V2_MIGRATED = "manual_sync_queue_v2_migrated"\n'
            '    private const val KEY_PERIODIC_SYNC_V2_MIGRATED = "periodic_sync_v2_migrated"',
        desc="version UNIQUE_PERIODIC_SYNC + add its migration-flag key",
    )

    apply_edit(
        rel,
        old='    fun schedulePeriodic(context: Context) {\n'
            '        clearLegacyManualQueueOnce(context)\n'
            '\n'
            '        val request = PeriodicWorkRequestBuilder<SyncWorker>(\n'
            '            SYNC_INTERVAL_MINUTES,\n'
            '            TimeUnit.MINUTES,\n'
            '            SYNC_FLEX_MINUTES,\n'
            '            TimeUnit.MINUTES\n'
            '        )\n'
            '            .setConstraints(syncConstraints())\n'
            '            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, INITIAL_BACKOFF_MINUTES, TimeUnit.MINUTES)\n'
            '            .addTag(HuaweiConfig.SYNC_WORKER_TAG)\n'
            '            .build()\n'
            '\n'
            '        WorkManager.getInstance(context.applicationContext).enqueueUniquePeriodicWork(\n'
            '            UNIQUE_PERIODIC_SYNC,\n'
            '            ExistingPeriodicWorkPolicy.UPDATE,\n'
            '            request\n'
            '        )\n'
            '\n'
            '        AppLogger.i(TAG, "Scheduled periodic Huawei -> Health Connect sync every ${SYNC_INTERVAL_MINUTES} minutes")',
        new='    fun schedulePeriodic(context: Context) {\n'
            '        clearLegacyManualQueueOnce(context)\n'
            '        clearLegacyPeriodicSyncOnce(context)\n'
            '\n'
            '        val request = PeriodicWorkRequestBuilder<SyncWorker>(\n'
            '            SYNC_INTERVAL_MINUTES,\n'
            '            TimeUnit.MINUTES,\n'
            '            SYNC_FLEX_MINUTES,\n'
            '            TimeUnit.MINUTES\n'
            '        )\n'
            '            .setConstraints(syncConstraints())\n'
            '            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, INITIAL_BACKOFF_MINUTES, TimeUnit.MINUTES)\n'
            '            .addTag(HuaweiConfig.SYNC_WORKER_TAG)\n'
            '            .build()\n'
            '\n'
            '        // schedulePeriodic() runs on every single cold launch (from\n'
            '        // MainActivity.onCreate). ExistingPeriodicWorkPolicy.UPDATE\n'
            '        // re-applies the request even when it is byte-for-byte identical to\n'
            '        // what\'s already scheduled -- and WorkManager can cancel a\n'
            '        // currently RUNNING instance of that periodic work to do so. A real\n'
            '        // device log showed exactly this: "Sync cancelled by\n'
            '        // WorkManager/system: Job was cancelled" firing in the same second\n'
            '        // as schedulePeriodic()\'s own log line, immediately followed by a\n'
            '        // retry. KEEP is a true no-op when a non-cancelled\n'
            '        // UNIQUE_PERIODIC_SYNC already exists, so it never touches an\n'
            '        // in-flight run. clearLegacyPeriodicSyncOnce() above migrates any\n'
            '        // existing installs off the old UPDATE-scheduled work once; if\n'
            '        // SYNC_INTERVAL_MINUTES/constraints/backoff ever need to change in\n'
            '        // a future release, bump UNIQUE_PERIODIC_SYNC to a new name (same\n'
            '        // versioned-migration pattern) so existing installs adopt the new\n'
            '        // schedule cleanly instead of relying on UPDATE to change a request\n'
            '        // mid-run.\n'
            '        WorkManager.getInstance(context.applicationContext).enqueueUniquePeriodicWork(\n'
            '            UNIQUE_PERIODIC_SYNC,\n'
            '            ExistingPeriodicWorkPolicy.KEEP,\n'
            '            request\n'
            '        )\n'
            '\n'
            '        AppLogger.i(TAG, "Scheduled periodic Huawei -> Health Connect sync every ${SYNC_INTERVAL_MINUTES} minutes")',
        desc="clearLegacyPeriodicSyncOnce() + switch to KEEP",
    )

    apply_edit(
        rel,
        old='    private fun clearLegacyManualQueueOnce(context: Context) {\n'
            '        val appContext = context.applicationContext\n'
            '        val prefs = appContext.getSharedPreferences(HuaweiConfig.PREFS_NAME, Context.MODE_PRIVATE)\n'
            '        if (prefs.getBoolean(KEY_MANUAL_QUEUE_V2_MIGRATED, false)) return\n'
            '        WorkManager.getInstance(appContext).cancelUniqueWork(LEGACY_UNIQUE_SYNC_NOW)\n'
            '        prefs.edit().putBoolean(KEY_MANUAL_QUEUE_V2_MIGRATED, true).apply()\n'
            '        AppLogger.i(TAG, "Cleared legacy manual-sync queue; migrated to $UNIQUE_SYNC_NOW")\n'
            '    }\n'
            '\n'
            '    private fun computeInitialDelayUntilEveningReminder(): Duration {',
        new='    private fun clearLegacyManualQueueOnce(context: Context) {\n'
            '        val appContext = context.applicationContext\n'
            '        val prefs = appContext.getSharedPreferences(HuaweiConfig.PREFS_NAME, Context.MODE_PRIVATE)\n'
            '        if (prefs.getBoolean(KEY_MANUAL_QUEUE_V2_MIGRATED, false)) return\n'
            '        WorkManager.getInstance(appContext).cancelUniqueWork(LEGACY_UNIQUE_SYNC_NOW)\n'
            '        prefs.edit().putBoolean(KEY_MANUAL_QUEUE_V2_MIGRATED, true).apply()\n'
            '        AppLogger.i(TAG, "Cleared legacy manual-sync queue; migrated to $UNIQUE_SYNC_NOW")\n'
            '    }\n'
            '\n'
            '    private fun clearLegacyPeriodicSyncOnce(context: Context) {\n'
            '        val appContext = context.applicationContext\n'
            '        val prefs = appContext.getSharedPreferences(HuaweiConfig.PREFS_NAME, Context.MODE_PRIVATE)\n'
            '        if (prefs.getBoolean(KEY_PERIODIC_SYNC_V2_MIGRATED, false)) return\n'
            '        WorkManager.getInstance(appContext).cancelUniqueWork(LEGACY_UNIQUE_PERIODIC_SYNC)\n'
            '        prefs.edit().putBoolean(KEY_PERIODIC_SYNC_V2_MIGRATED, true).apply()\n'
            '        AppLogger.i(TAG, "Cleared legacy periodic-sync schedule; migrated to $UNIQUE_PERIODIC_SYNC")\n'
            '    }\n'
            '\n'
            '    private fun computeInitialDelayUntilEveningReminder(): Duration {',
        desc="add clearLegacyPeriodicSyncOnce() migration function",
    )


def patch_google_health_permission_requester() -> None:
    rel = "app/src/main/java/com/openhealth/sync/config/GoogleHealthPermissionRequester.kt"
    print("==> GoogleHealthPermissionRequester.kt: make it genuinely return Boolean")

    apply_edit(
        rel,
        old=' * Checks Health Connect availability first and wraps the actual launch() call in\n'
            ' * try/catch: if no app on the device can handle the permission-request intent (no\n'
            ' * Health Connect provider installed, or a provider that doesn\'t support the\n'
            ' * contract), ActivityResultLauncher.launch() can throw synchronously. Previously this\n'
            ' * call had no guard at all in MainActivity, which is the most likely direct cause of\n'
            ' * the AppGallery review crash report ("click connect google health - app crashes").\n'
            ' */\n'
            'fun requestGoogleHealthPermissions(\n'
            '    context: Context,\n'
            '    googleManager: HealthConnectManager,\n'
            '    launcher: ActivityResultLauncher<Set<String>>\n'
            ') {\n'
            '    when (googleManager.getStatus()) {\n'
            '        HealthConnectStatus.NOT_INSTALLED -> {\n'
            '            Toast.makeText(context, context.getString(R.string.toast_hc_not_installed), Toast.LENGTH_LONG).show()\n'
            '            return\n'
            '        }\n'
            '        HealthConnectStatus.NEEDS_UPDATE -> {\n'
            '            Toast.makeText(context, context.getString(R.string.toast_hc_needs_update), Toast.LENGTH_LONG).show()\n'
            '            return\n'
            '        }\n'
            '        HealthConnectStatus.NOT_SUPPORTED -> {\n'
            '            Toast.makeText(context, context.getString(R.string.toast_hc_not_supported), Toast.LENGTH_LONG).show()\n'
            '            return\n'
            '        }\n'
            '        HealthConnectStatus.AVAILABLE -> {\n'
            '            // fall through to the actual launch below\n'
            '        }\n'
            '    }\n'
            '    try {\n'
            '        launcher.launch(googleManager.permissions)\n'
            '    } catch (e: Exception) {\n'
            '        AppLogger.e(TAG, "Failed to launch Health Connect permission request: ${e.message}", e)\n'
            '        Toast.makeText(context, context.getString(R.string.toast_hc_launch_failed), Toast.LENGTH_LONG).show()\n'
            '    }\n'
            '}',
        new=' * Checks Health Connect availability first and wraps the actual launch() call in\n'
            ' * try/catch: if no app on the device can handle the permission-request intent (no\n'
            ' * Health Connect provider installed, or a provider that doesn\'t support the\n'
            ' * contract), ActivityResultLauncher.launch() can throw synchronously. Previously this\n'
            ' * call had no guard at all in MainActivity, which is the most likely direct cause of\n'
            ' * the AppGallery review crash report ("click connect google health - app crashes").\n'
            ' *\n'
            ' * Returns true only when launcher.launch() was actually invoked without throwing --\n'
            ' * i.e. only when a system permission screen is genuinely about to appear and its\n'
            ' * result callback will eventually fire. MainActivity uses this to know when the\n'
            ' * next onResume() is just that screen returning, not a real "back to the app" event.\n'
            ' */\n'
            'fun requestGoogleHealthPermissions(\n'
            '    context: Context,\n'
            '    googleManager: HealthConnectManager,\n'
            '    launcher: ActivityResultLauncher<Set<String>>\n'
            '): Boolean {\n'
            '    when (googleManager.getStatus()) {\n'
            '        HealthConnectStatus.NOT_INSTALLED -> {\n'
            '            Toast.makeText(context, context.getString(R.string.toast_hc_not_installed), Toast.LENGTH_LONG).show()\n'
            '            return false\n'
            '        }\n'
            '        HealthConnectStatus.NEEDS_UPDATE -> {\n'
            '            Toast.makeText(context, context.getString(R.string.toast_hc_needs_update), Toast.LENGTH_LONG).show()\n'
            '            return false\n'
            '        }\n'
            '        HealthConnectStatus.NOT_SUPPORTED -> {\n'
            '            Toast.makeText(context, context.getString(R.string.toast_hc_not_supported), Toast.LENGTH_LONG).show()\n'
            '            return false\n'
            '        }\n'
            '        HealthConnectStatus.AVAILABLE -> {\n'
            '            // fall through to the actual launch below\n'
            '        }\n'
            '    }\n'
            '    return try {\n'
            '        launcher.launch(googleManager.permissions)\n'
            '        true\n'
            '    } catch (e: Exception) {\n'
            '        AppLogger.e(TAG, "Failed to launch Health Connect permission request: ${e.message}", e)\n'
            '        Toast.makeText(context, context.getString(R.string.toast_hc_launch_failed), Toast.LENGTH_LONG).show()\n'
            '        false\n'
            '    }\n'
            '}',
        desc="make requestGoogleHealthPermissions() genuinely return Boolean",
    )


def patch_huawei_health_manager() -> None:
    rel = "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt"
    print("==> HuaweiHealthManager.kt: connection-race retry helper")

    apply_edit(
        rel,
        old='import kotlinx.coroutines.CancellationException\n'
            'import kotlinx.coroutines.CoroutineDispatcher\n'
            'import kotlinx.coroutines.Dispatchers\n'
            'import kotlinx.coroutines.withContext',
        new='import kotlinx.coroutines.CancellationException\n'
            'import kotlinx.coroutines.CoroutineDispatcher\n'
            'import kotlinx.coroutines.Dispatchers\n'
            'import kotlinx.coroutines.delay\n'
            'import kotlinx.coroutines.withContext',
        desc="add missing kotlinx.coroutines.delay import",
    )

    apply_edit(
        rel,
        old='    private fun ensureRuntimeReady() {\n'
            '        if (!HmsCoreHelper.isInstalled(context)) {\n'
            '            throw IllegalStateException(HmsCoreHelper.missingMessage)\n'
            '        }\n'
            '\n'
            '        if (!HmsCoreHelper.isHuaweiHealthInstalled(context)) {\n'
            '            throw IllegalStateException("Huawei Health is required. Install Huawei Health, sign in, and try again.")\n'
            '        }\n'
            '    }\n'
            '\n'
            '    private suspend fun readDailyStepTotals(endTimeMs: Long): List<StepData> {',
        new='    private fun ensureRuntimeReady() {\n'
            '        if (!HmsCoreHelper.isInstalled(context)) {\n'
            '            throw IllegalStateException(HmsCoreHelper.missingMessage)\n'
            '        }\n'
            '\n'
            '        if (!HmsCoreHelper.isHuaweiHealthInstalled(context)) {\n'
            '            throw IllegalStateException("Huawei Health is required. Install Huawei Health, sign in, and try again.")\n'
            '        }\n'
            '    }\n'
            '\n'
            '    /**\n'
            '     * The very first Huawei Health Kit call made after a cold app-process\n'
            '     * start (or after the underlying HMS client has been idle long enough\n'
            '     * to drop its connection) can race the client\'s own async connection\n'
            '     * handshake and fail with a "client is not connected" style error, even\n'
            '     * though nothing is actually broken -- a later call, moments later,\n'
            '     * succeeds with no special handling at all. A real device log showed\n'
            '     * this hitting two different Huawei controllers in the very same sync\n'
            '     * attempt: the daily step summation failed with "50011: the client is\n'
            '     * not connected", and the activity-records read failed right after it\n'
            '     * and was logged as a 50005 scope denial -- but that same category\n'
            '     * succeeded about 20 seconds later, in the very next sync attempt, with\n'
            '     * no re-authorization happening in between. A genuine scope denial\n'
            '     * can\'t resolve itself in 20 seconds; a connection race that clears up\n'
            '     * once the HMS client finishes connecting can, which is a strong sign\n'
            '     * that read was hitting the same race, just surfaced as a different\n'
            '     * exception type by that particular Huawei controller. That same log\n'
            '     * also showed a second sync attempt competing for the sync lease at\n'
            '     * almost the same moment, which plausibly added the contention that\n'
            '     * caused the race in the first place. This retries up to twice (three\n'
            '     * attempts total) before giving up. SecurityException (genuine scope\n'
            '     * denial, e.g. 50005) and CancellationException are rethrown\n'
            '     * immediately on the very first attempt, untouched -- retrying either\n'
            '     * of those would just delay a correct, final outcome, not fix anything.\n'
            '     */\n'
            '    private suspend fun <T> retryOnConnectionRace(block: suspend () -> T): T {\n'
            '        var lastConnectionRaceError: Exception? = null\n'
            '        for (attempt in 1..CONNECTION_RACE_MAX_ATTEMPTS) {\n'
            '            try {\n'
            '                return block()\n'
            '            } catch (e: CancellationException) {\n'
            '                throw e\n'
            '            } catch (e: SecurityException) {\n'
            '                throw e\n'
            '            } catch (e: Exception) {\n'
            '                val looksLikeConnectionRace = e.message?.contains("not connected", ignoreCase = true) == true\n'
            '                if (!looksLikeConnectionRace) throw e\n'
            '                lastConnectionRaceError = e\n'
            '                if (attempt < CONNECTION_RACE_MAX_ATTEMPTS) {\n'
            '                    AppLogger.w(\n'
            '                        TAG,\n'
            '                        "Huawei Health Kit call failed with a client-not-connected style error " +\n'
            '                            "(attempt $attempt/$CONNECTION_RACE_MAX_ATTEMPTS); " +\n'
            '                            "retrying in ${CONNECTION_RACE_RETRY_DELAY_MS}ms: ${e.message}"\n'
            '                    )\n'
            '                    delay(CONNECTION_RACE_RETRY_DELAY_MS)\n'
            '                }\n'
            '            }\n'
            '        }\n'
            '        throw lastConnectionRaceError!!\n'
            '    }\n'
            '\n'
            '    private suspend fun readDailyStepTotals(endTimeMs: Long): List<StepData> {',
        desc="add retryOnConnectionRace() helper",
    )

    apply_edit(
        rel,
        old='            dataController\n'
            '                .readDailySummation(DataType.DT_CONTINUOUS_STEPS_DELTA, startDate, endDate)\n'
            '                .awaitTask()\n'
            '        } catch (e: CancellationException) {',
        new='            retryOnConnectionRace {\n'
            '                dataController\n'
            '                    .readDailySummation(DataType.DT_CONTINUOUS_STEPS_DELTA, startDate, endDate)\n'
            '                    .awaitTask()\n'
            '            }\n'
            '        } catch (e: CancellationException) {',
        desc="wrap daily step summation read in retryOnConnectionRace",
    )

    apply_edit(
        rel,
        old='        val reply = HuaweiHiHealth.getActivityRecordsController(context)\n'
            '            .getActivityRecord(options)\n'
            '            .awaitTask()\n'
            '        val records = reply.getActivityRecords().orEmpty()',
        new='        val reply = retryOnConnectionRace {\n'
            '            HuaweiHiHealth.getActivityRecordsController(context)\n'
            '                .getActivityRecord(options)\n'
            '                .awaitTask()\n'
            '        }\n'
            '        val records = reply.getActivityRecords().orEmpty()',
        desc="wrap activity-records read in retryOnConnectionRace",
    )

    apply_edit(
        rel,
        old='    private companion object {\n'
            '        private const val HUAWEI_READ_CHUNK_MS: Long = 24L * 60L * 60L * 1000L\n'
            '        private const val ACTIVITY_HISTORY_WINDOW_DAYS = 7L\n'
            '        private val SYNTHETIC_HUAWEI_ACTIVITY_NAME = Regex(',
        new='    private companion object {\n'
            '        private const val HUAWEI_READ_CHUNK_MS: Long = 24L * 60L * 60L * 1000L\n'
            '        private const val ACTIVITY_HISTORY_WINDOW_DAYS = 7L\n'
            '        private const val CONNECTION_RACE_RETRY_DELAY_MS = 2_000L\n'
            '        private const val CONNECTION_RACE_MAX_ATTEMPTS = 3\n'
            '        private val SYNTHETIC_HUAWEI_ACTIVITY_NAME = Regex(',
        desc="add CONNECTION_RACE_RETRY_DELAY_MS / CONNECTION_RACE_MAX_ATTEMPTS constants",
    )


def main() -> None:
    print("==> Checking target files exist")
    for rel in TARGET_FILES:
        if not (ROOT / rel).exists():
            die(f"Expected file not found: {rel} (run this from the repo root)")

    print(f"==> Backing up touched files to {BACKUP_DIR.relative_to(ROOT)}")
    for rel in TARGET_FILES:
        backup_file(rel)

    patch_main_activity()
    patch_background_sync_scheduler()
    patch_google_health_permission_requester()
    patch_huawei_health_manager()

    print("==> Best-effort compile check")
    gradlew = ROOT / "gradlew"
    if gradlew.exists():
        result = subprocess.run(
            ["./gradlew", ":app:compileDebugKotlin", "--console=plain"],
            cwd=ROOT,
        )
        if result.returncode != 0:
            die("compileDebugKotlin failed -- NOT committing or pushing. "
                "Fix the error above (or paste it back) before re-running.")
        print("==> Compile check passed")
    else:
        print("   gradlew not found -- skipping compile check (unexpected outside "
              "a throwaway sandbox; NOT committing automatically).")
        return

    print("==> git add / commit / push")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    commit = subprocess.run(
        ["git", "commit", "-m",
         "Fix cold-launch sync reliability: guard onResume() auto-sync against "
         "system-screen returns, stop periodic re-enqueue from cancelling an "
         "in-flight run, retry Huawei calls on cold-launch connection races"],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("   (nothing to commit -- all edits were likely already applied)")
        return
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)
    print("==> Done: pushed to origin/main")


if __name__ == "__main__":
    main()
