#!/usr/bin/env python3
"""
patch_sync_activity_signal_and_midnight_cache_v1.py

Fixes two real-device bugs confirmed against an actual diagnostic log
(2026-08-31, Xiaomi M2102K1G / Android 13 / app 1.16.1):

## Bug 1: "Syncing..." indicator never appears

Root cause, confirmed by tracing the log's four SyncWorker invocations
against source: SyncViewModel.isSyncing was wired ONLY to
markSyncStarted()/markSyncCompleted(), which MainActivity calls only from
its two UI-triggered sync paths (manual "Sync now", auto-sync-on-launch).
SyncWorker itself -- a plain CoroutineWorker with no ViewModel reference,
whether running as the periodic 30-minute job or a one-time manual job --
has no path to that flag at all.

In the supplied log, owner=98964f8d... (never enqueued through
SyncOrchestrator -- confirmed by the absence of a matching
"Manual Huawei -> Health Connect sync work id=..." log line for it) is
the one that actually won SyncReliability's lease and performed the real
~10-second Huawei read + Health Connect write. The UI-triggered attempt
(owner=2e2f71b4...) fired markSyncStarted(), immediately lost the lease
race, and called markSyncCompleted() within about the same second -- a
true->false flip far too fast to ever render, even with an alpha-only
fade.

Fix: a new HuaweiConfig.SYNC_ACTIVITY_TAG, applied only to SyncWorker's
two enqueue sites (BackgroundSyncScheduler.schedulePeriodic and
enqueueImmediateSync) -- NOT to the existing SYNC_WORKER_TAG, which is
also applied to the unrelated EveningReminderWorker and would falsely
report "syncing" while a reminder notification job runs. MainActivity now
observes WorkManager.getWorkInfosByTagLiveData(SYNC_ACTIVITY_TAG) and
feeds "is any tagged work RUNNING/ENQUEUED/BLOCKED" into a new
SyncViewModel.setBackgroundSyncActive(). SyncUiState.isSyncing becomes a
computed property: isUiTriggeredSyncing OR isBackgroundSyncActive.

## Bug 2: yesterday's steps flash before clearing to today's data

Root cause, confirmed by comparing the two cache-consuming code paths:
DashboardViewModel.buildInitialState() already zeroes daily-total fields
when the on-disk cache predates today (sprint 2026-08-26), but
refreshFromCache() -- called both on a sync's own completion AND, per
SyncOrchestrator's lease-collision handling, on a delayed retry timer
(8s/12s after the LOSING/deferred sync's own "already running" result,
independent of when the WINNING sync's cache write actually lands) --
had no such guard. That retry can read the on-disk cache in the narrow
window before the winning sync's fresh write for the new day lands,
re-applying yesterday's still-cached real numbers over what
buildInitialState() had already correctly zeroed on cold launch, until a
later refresh corrects it again a few seconds later.

Fix: extracted buildInitialState()'s zeroing logic into a shared
zeroedDailyTotals() helper, and refreshFromCache() now applies the exact
same "cache predates today" check before committing the cached snapshot,
zeroing daily totals instead of re-showing yesterday's numbers.
recentWorkouts (real workout history) is untouched by either path, same
as before.

Mandatory workflow already completed before this script was written:
hand-edited mirror -> real diff -> this script generated from that diff
-> tested on a clean extraction with a fake gradlew -> byte-diffed
against the mirror -> re-run for idempotency. See delivery notes.
"""
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"

HUAWEI_CONFIG_FILE = REPO_ROOT / "app/src/main/java/com/openhealth/sync/data/remote/HuaweiConfig.kt"
SCHEDULER_FILE = REPO_ROOT / "app/src/main/java/com/openhealth/sync/data/worker/BackgroundSyncScheduler.kt"
SYNC_VM_FILE = REPO_ROOT / "app/src/main/java/com/openhealth/sync/ui/SyncViewModel.kt"
MAIN_ACTIVITY_FILE = REPO_ROOT / "app/src/main/java/com/openhealth/sync/MainActivity.kt"
DASHBOARD_VM_FILE = REPO_ROOT / "app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt"


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


def backup(path: Path) -> None:
    if not path.exists():
        die(f"Cannot back up missing file: {path}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    rel = path.relative_to(REPO_ROOT)
    dest = BACKUP_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(path, dest)


def apply_edit(path: Path, old: str, new: str, expected_old_count: int, expected_new_count: int, description: str) -> None:
    """Genuine replacement. Idempotent via exact old_str occurrence count."""
    text = path.read_text(encoding="utf-8")
    old_count = text.count(old)
    new_count = text.count(new)

    if old_count == 0 and new_count >= expected_new_count:
        print(f"  [skip] {description} (already applied)")
        return

    if old_count != expected_old_count:
        die(
            f"{description}: expected {expected_old_count} occurrence(s) of anchor "
            f"in {path.name}, found {old_count}. Aborting -- source has diverged."
        )

    backup(path)
    text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print(f"  [applied] {description}")


def apply_insertion(path: Path, anchor: str, new_with_anchor: str, unique_marker: str, description: str) -> None:
    """Pure insertion next to text that itself stays unchanged. Idempotent via unique_marker."""
    text = path.read_text(encoding="utf-8")

    if unique_marker in text:
        print(f"  [skip] {description} (already applied)")
        return

    if text.count(anchor) != 1:
        die(
            f"{description}: expected exactly 1 occurrence of anchor in {path.name}, "
            f"found {text.count(anchor)}. Aborting -- source has diverged."
        )

    backup(path)
    text = text.replace(anchor, new_with_anchor)
    path.write_text(text, encoding="utf-8")
    print(f"  [applied] {description}")


def validate_kotlin_braces(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count("{") != text.count("}"):
        die(f"Brace mismatch in {path.name} after patching -- aborting before build.")
    if text.count("(") != text.count(")"):
        die(f"Parenthesis mismatch in {path.name} after patching -- aborting before build.")


def main() -> None:
    for f in (HUAWEI_CONFIG_FILE, SCHEDULER_FILE, SYNC_VM_FILE, MAIN_ACTIVITY_FILE, DASHBOARD_VM_FILE):
        if not f.exists():
            die(f"Expected file not found: {f}")

    print("== 1/5: New SYNC_ACTIVITY_TAG (HuaweiConfig.kt) ==")

    apply_insertion(
        HUAWEI_CONFIG_FILE,
        anchor='    const val SYNC_WORKER_TAG: String = "BitLutSyncWorker"\n',
        new_with_anchor=(
            '    const val SYNC_WORKER_TAG: String = "BitLutSyncWorker"\n'
            '\n'
            "    // 2026-08-31: SYNC_WORKER_TAG above is applied to every worker in this\n"
            "    // app (SyncWorker's periodic + one-time requests, AND\n"
            "    // EveningReminderWorker's periodic request) -- fine for WorkManager\n"
            '    // maintenance/cancellation, but useless for driving a "Syncing..." UI\n'
            "    // indicator, since it can't tell a real health-data sync apart from an\n"
            "    // unrelated notification-scheduling worker. This tag is applied only to\n"
            "    // SyncWorker's two enqueue sites (schedulePeriodic + enqueueImmediateSync\n"
            "    // in BackgroundSyncScheduler), so observing WorkInfo for THIS tag\n"
            '    // reflects "is any SyncWorker (periodic or manual, whichever one)\n'
            '    // actually running right now" -- a real device log showed the previous\n'
            "    // isSyncing signal (SyncViewModel.markSyncStarted/markSyncCompleted,\n"
            "    // wired only to the two MainActivity-triggered call sites) never fired\n"
            "    // at all when the periodic background worker happened to win the sync\n"
            "    // lease race: the UI-triggered attempt got deferred and its own\n"
            "    // started/completed pair collapsed to well under a second, too fast to\n"
            "    // ever render, while the periodic worker that did the real 10-second\n"
            "    // sync had no path to isSyncing whatsoever.\n"
            '    // BITLUT_SYNC_ACTIVITY_TAG_2026_08_31\n'
            '    const val SYNC_ACTIVITY_TAG: String = "BitLutSyncActivity"\n'
        ),
        unique_marker="BITLUT_SYNC_ACTIVITY_TAG_2026_08_31",
        description="add SYNC_ACTIVITY_TAG constant",
    )

    validate_kotlin_braces(HUAWEI_CONFIG_FILE)

    print("== 2/5: Apply SYNC_ACTIVITY_TAG to SyncWorker's two enqueue sites (BackgroundSyncScheduler.kt) ==")

    apply_edit(
        SCHEDULER_FILE,
        old=(
            '            .setConstraints(syncConstraints())\n'
            '            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, INITIAL_BACKOFF_MINUTES, TimeUnit.MINUTES)\n'
            '            .addTag(HuaweiConfig.SYNC_WORKER_TAG)\n'
            '            .build()\n'
            '\n'
            '        // schedulePeriodic() runs on every single cold launch (from\n'
        ),
        new=(
            '            .setConstraints(syncConstraints())\n'
            '            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, INITIAL_BACKOFF_MINUTES, TimeUnit.MINUTES)\n'
            '            .addTag(HuaweiConfig.SYNC_WORKER_TAG)\n'
            '            .addTag(HuaweiConfig.SYNC_ACTIVITY_TAG)\n'
            '            .build()\n'
            '\n'
            '        // schedulePeriodic() runs on every single cold launch (from\n'
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="tag periodic SyncWorker request with SYNC_ACTIVITY_TAG",
    )

    apply_edit(
        SCHEDULER_FILE,
        old=(
            '            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, INITIAL_BACKOFF_MINUTES, TimeUnit.MINUTES)\n'
            '            .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)\n'
            '            .addTag(HuaweiConfig.SYNC_WORKER_TAG)\n'
            '            .build()\n'
            '\n'
            '        workManager.enqueueUniqueWork(\n'
        ),
        new=(
            '            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, INITIAL_BACKOFF_MINUTES, TimeUnit.MINUTES)\n'
            '            .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)\n'
            '            .addTag(HuaweiConfig.SYNC_WORKER_TAG)\n'
            '            .addTag(HuaweiConfig.SYNC_ACTIVITY_TAG)\n'
            '            .build()\n'
            '\n'
            '        workManager.enqueueUniqueWork(\n'
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="tag one-time manual SyncWorker request with SYNC_ACTIVITY_TAG",
    )

    validate_kotlin_braces(SCHEDULER_FILE)

    print("== 3/5: isSyncing becomes derived (SyncViewModel.kt) ==")

    apply_edit(
        SYNC_VM_FILE,
        old=(
            'data class SyncUiState(\n'
            '    val isGoogleAvailable: Boolean = false,\n'
            '    val showImportScreen: Boolean = false,\n'
            '    val hasGooglePermissions: Boolean = false,\n'
            '    val needsPermissionRefresh: Boolean = false,\n'
            '    val isHuaweiAuthorized: Boolean = false,\n'
            '    val lastHuaweiAuthFailureReason: HuaweiAuthFailureReason? = null,\n'
            '    val selectedDataSource: HealthDataSource = HealthDataSource.HUAWEI_HEALTH,\n'
            '    val isSyncing: Boolean = false,\n'
            '    val syncStatus: String = "sync_status_idle",\n'
            '    val lastSyncTime: String = "sync_no_data"\n'
            ')\n'
        ),
        new=(
            'data class SyncUiState(\n'
            '    val isGoogleAvailable: Boolean = false,\n'
            '    val showImportScreen: Boolean = false,\n'
            '    val hasGooglePermissions: Boolean = false,\n'
            '    val needsPermissionRefresh: Boolean = false,\n'
            '    val isHuaweiAuthorized: Boolean = false,\n'
            '    val lastHuaweiAuthFailureReason: HuaweiAuthFailureReason? = null,\n'
            '    val selectedDataSource: HealthDataSource = HealthDataSource.HUAWEI_HEALTH,\n'
            '    // 2026-08-31: isSyncing (below) is now the OR of these two independent\n'
            "    // raw signals -- see its own doc comment for why a single flag wasn't\n"
            "    // enough. Not private: SyncViewModel's markSyncStarted()/\n"
            "    // markSyncCompleted()/setBackgroundSyncActive() need to set these via\n"
            "    // copy(), and a private constructor property's generated copy()\n"
            '    // parameter is only accessible from inside this class, not from\n'
            '    // SyncViewModel even though it lives in the same file -- Kotlin scopes\n'
            '    // member visibility to the class, not the file. Callers outside this\n'
            '    // file should still read isSyncing, not these two fields directly.\n'
            '    val isUiTriggeredSyncing: Boolean = false,\n'
            '    val isBackgroundSyncActive: Boolean = false,\n'
            '    val syncStatus: String = "sync_status_idle",\n'
            '    val lastSyncTime: String = "sync_no_data"\n'
            ') {\n'
            '    /**\n'
            '     * True while the "Syncing..." indicator should show. Previously this was\n'
            '     * one flag, flipped only by SyncViewModel.markSyncStarted()/\n'
            '     * markSyncCompleted(), which MainActivity calls only from its two\n'
            '     * UI-triggered sync paths (manual refresh, auto-sync-on-launch). A real\n'
            '     * device log showed that signal alone is not reliable: when the\n'
            '     * periodic background SyncWorker happens to win the sync-run lease\n'
            "     * race, the UI-triggered attempt gets deferred by SyncReliability's\n"
            '     * lease check almost immediately, so its own started->completed pair\n'
            '     * can collapse to well under a second -- too fast to ever render a\n'
            '     * fade-in -- while the periodic worker actually doing the real,\n'
            '     * multi-second sync has no path to this flag at all. isBackgroundSyncActive\n'
            '     * (fed from a WorkManager tag observer in MainActivity, see\n'
            '     * HuaweiConfig.SYNC_ACTIVITY_TAG) reflects "is any SyncWorker instance,\n'
            '     * whichever one, actually RUNNING or ENQUEUED right now" regardless of\n'
            '     * which path triggered it, so the indicator now shows for the sync that\n'
            '     * is really doing the work.\n'
            '     */\n'
            '    val isSyncing: Boolean get() = isUiTriggeredSyncing || isBackgroundSyncActive\n'
            '}\n'
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="replace stored isSyncing with derived isUiTriggeredSyncing || isBackgroundSyncActive",
    )

    apply_edit(
        SYNC_VM_FILE,
        old=(
            '    fun markSyncStarted() {\n'
            '        _uiState.update { it.copy(isSyncing = true, syncStatus = "sync_status_syncing") }\n'
            '    }\n'
            '\n'
            '    fun markSyncCompleted(success: Boolean) {\n'
            '        val statusMsg = if (success) "sync_status_success" else "sync_status_error"\n'
            '        val time = if (success) SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date()) else _uiState.value.lastSyncTime\n'
            '        if (success) prefs.edit().putString("last_sync_time", time).apply()\n'
            '        _uiState.update { it.copy(isSyncing = false, syncStatus = statusMsg, lastSyncTime = time) }\n'
            '        // Do not re-query Health Connect permissions here. A completed sync\n'
            '        // already proved the provider path; repeating the permission snapshot\n'
            '        // was one contributor to the quota storm.\n'
            '    }\n'
        ),
        new=(
            '    fun markSyncStarted() {\n'
            '        _uiState.update { it.copy(isUiTriggeredSyncing = true, syncStatus = "sync_status_syncing") }\n'
            '    }\n'
            '\n'
            '    fun markSyncCompleted(success: Boolean) {\n'
            '        val statusMsg = if (success) "sync_status_success" else "sync_status_error"\n'
            '        val time = if (success) SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date()) else _uiState.value.lastSyncTime\n'
            '        if (success) prefs.edit().putString("last_sync_time", time).apply()\n'
            '        _uiState.update { it.copy(isUiTriggeredSyncing = false, syncStatus = statusMsg, lastSyncTime = time) }\n'
            '        // Do not re-query Health Connect permissions here. A completed sync\n'
            '        // already proved the provider path; repeating the permission snapshot\n'
            '        // was one contributor to the quota storm.\n'
            '    }\n'
            '\n'
            '    /**\n'
            "     * Fed by MainActivity's WorkManager tag observer (HuaweiConfig.\n"
            "     * SYNC_ACTIVITY_TAG) -- see SyncUiState.isSyncing's doc comment for why\n"
            '     * this exists alongside markSyncStarted()/markSyncCompleted(). Does not\n'
            '     * touch syncStatus: that field carries a specific outcome message\n'
            '     * (success/error) that only the UI-triggered path, which actually\n'
            '     * observes a result, can meaningfully report.\n'
            '     */\n'
            '    fun setBackgroundSyncActive(active: Boolean) {\n'
            '        _uiState.update { it.copy(isBackgroundSyncActive = active) }\n'
            '    }\n'
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="update markSyncStarted/markSyncCompleted, add setBackgroundSyncActive",
    )

    validate_kotlin_braces(SYNC_VM_FILE)

    print("== 4/5: WorkManager tag observer (MainActivity.kt) ==")

    apply_edit(
        MAIN_ACTIVITY_FILE,
        old=(
            'import androidx.lifecycle.lifecycleScope\n'
            'import com.openhealth.sync.config.HealthDataSource\n'
            'import com.openhealth.sync.domain.SyncOrchestrator\n'
        ),
        new=(
            'import androidx.lifecycle.lifecycleScope\n'
            'import androidx.work.WorkInfo\n'
            'import androidx.work.WorkManager\n'
            'import com.openhealth.sync.config.HealthDataSource\n'
            'import com.openhealth.sync.data.remote.HuaweiConfig\n'
            'import com.openhealth.sync.domain.SyncOrchestrator\n'
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="add WorkInfo/WorkManager/HuaweiConfig imports",
    )

    apply_edit(
        MAIN_ACTIVITY_FILE,
        old=(
            '        enableEdgeToEdge()\n'
            '\n'
            '        setupPeriodicSync()\n'
            '\n'
            '        setContent {\n'
        ),
        new=(
            '        enableEdgeToEdge()\n'
            '\n'
            '        setupPeriodicSync()\n'
            '        observeBackgroundSyncActivity()\n'
            '\n'
            '        setContent {\n'
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="call observeBackgroundSyncActivity() from onCreate()",
    )

    apply_insertion(
        MAIN_ACTIVITY_FILE,
        anchor=(
            '    /**\n'
            '     * POST_NOTIFICATIONS is a runtime permission on API 33+ (Android 13).\n'
        ),
        new_with_anchor=(
            '    /**\n'
            "     * 2026-08-31: drives SyncViewModel.isSyncing's other half. See\n"
            "     * SyncUiState.isSyncing's doc comment for the full story -- in short,\n"
            "     * markSyncStarted()/markSyncCompleted() only fire from this Activity's\n"
            '     * own two sync-trigger call sites, so a real periodic background sync\n'
            '     * that wins the lease race (confirmed on a real device log) never shows\n'
            '     * "Syncing...", while a UI-triggered attempt that loses that race can\n'
            '     * flip started->completed inside under a second. Observing WorkInfo for\n'
            '     * HuaweiConfig.SYNC_ACTIVITY_TAG (applied only to SyncWorker\'s two\n'
            '     * enqueue sites, not the unrelated EveningReminderWorker) reflects\n'
            '     * whether any SyncWorker instance -- periodic or manual, whichever one\n'
            '     * -- is actually RUNNING/ENQUEUED/BLOCKED right now, independent of\n'
            '     * which path triggered it.\n'
            '     *\n'
            '     * getWorkInfosByTagLiveData(), not a one-shot query: WorkManager can\n'
            '     * hold multiple tagged requests concurrently (the periodic job plus a\n'
            '     * momentarily-enqueued manual one), so "any" must be recomputed on every\n'
            '     * change to that set, not just observed once. LiveData.observe(this, ...)\n'
            "     * ties this to the Activity's lifecycle automatically -- no manual\n"
            "     * removeObserver() needed, matching how PermissionController's launcher\n"
            '     * callbacks are also lifecycle-scoped in this file.\n'
            '     */\n'
            '    // BITLUT_OBSERVE_BACKGROUND_SYNC_ACTIVITY_2026_08_31\n'
            '    private fun observeBackgroundSyncActivity() {\n'
            '        WorkManager.getInstance(applicationContext)\n'
            '            .getWorkInfosByTagLiveData(HuaweiConfig.SYNC_ACTIVITY_TAG)\n'
            '            .observe(this) { infos ->\n'
            '                val active = infos.orEmpty().any { info ->\n'
            '                    when (info.state) {\n'
            '                        WorkInfo.State.RUNNING,\n'
            '                        WorkInfo.State.ENQUEUED,\n'
            '                        WorkInfo.State.BLOCKED -> true\n'
            '                        WorkInfo.State.SUCCEEDED,\n'
            '                        WorkInfo.State.FAILED,\n'
            '                        WorkInfo.State.CANCELLED -> false\n'
            '                    }\n'
            '                }\n'
            '                syncViewModel.setBackgroundSyncActive(active)\n'
            '            }\n'
            '    }\n'
            '\n'
            '    /**\n'
            '     * POST_NOTIFICATIONS is a runtime permission on API 33+ (Android 13).\n'
        ),
        unique_marker="BITLUT_OBSERVE_BACKGROUND_SYNC_ACTIVITY_2026_08_31",
        description="insert observeBackgroundSyncActivity()",
    )

    validate_kotlin_braces(MAIN_ACTIVITY_FILE)

    print("== 5/5: Midnight-staleness guard in refreshFromCache() (DashboardViewModel.kt) ==")

    apply_edit(
        DASHBOARD_VM_FILE,
        old=(
            '        _state.update { current ->\n'
            '            readAchievementsIntoState(\n'
            '                current.withSnapshot(cached.snapshot).copy(\n'
            '                    isLoading = false,\n'
            '                    hasPermissions = true,\n'
            '                    permissionsChecked = true,\n'
            '                    isFromCache = false,\n'
            '                    lastUpdatedAtMs = cached.dataChangedAtMs\n'
            '                )\n'
            '            )\n'
            '        }\n'
            '    }\n'
        ),
        new=(
            "        // 2026-08-31: this used to apply cached.snapshot unconditionally,\n"
            '        // with no check for whether the ON-DISK CACHE itself still predates\n'
            '        // today. buildInitialState() already had this exact guard for cold\n'
            '        // launch, but refreshFromCache() -- called both on a sync\'s own\n'
            "        // completion AND, per SyncOrchestrator's lease-collision handling,\n"
            '        // on a delayed retry timer that fires independently of whether the\n'
            '        // winning sync has actually finished writing yet -- had none. A real\n'
            '        // device log showed the race directly: a deferred sync trigger\'s\n'
            '        // retry (SyncOrchestrator\'s LEASE_COLLISION_RETRY_DELAYS_MS,\n'
            '        // 8s/12s after ITS OWN "already running" result, not after the\n'
            "        // WINNING sync's completion) could fire and read the cache a moment\n"
            "        // before the winning sync's own write landed -- at exactly the\n"
            '        // moment right after midnight, that stale on-disk blob is still\n'
            "        // yesterday's real numbers, correctly zeroed by buildInitialState()\n"
            "        // on cold launch but then overwritten right back to yesterday's\n"
            '        // totals by this unconditional apply, until the next refresh\n'
            "        // (or the winning sync's own completion callback) corrected it a\n"
            '        // few seconds later. Applying the same cachedDate-before-today\n'
            "        // check here closes that window: a stale-across-midnight cache read\n"
            '        // through this path now also zeroes daily totals instead of\n'
            "        // briefly re-displaying yesterday's numbers as if they were today's.\n"
            '        val cachedDate = Instant.ofEpochMilli(cached.savedAtMs).atZone(ZoneId.systemDefault()).toLocalDate()\n'
            '        val isStaleAcrossMidnight = cachedDate.isBefore(LocalDate.now())\n'
            '        if (isStaleAcrossMidnight) {\n'
            '            AppLogger.i(\n'
            '                TAG,\n'
            '                "refreshFromCache(): cache is from $cachedDate, before today (${LocalDate.now()}) -- " +\n'
            '                    "zeroing daily totals instead of re-showing yesterday\'s numbers"\n'
            '            )\n'
            '        }\n'
            '\n'
            '        _state.update { current ->\n'
            '            val next = readAchievementsIntoState(\n'
            '                current.withSnapshot(cached.snapshot).copy(\n'
            '                    isLoading = false,\n'
            '                    hasPermissions = true,\n'
            '                    permissionsChecked = true,\n'
            '                    isFromCache = false,\n'
            '                    lastUpdatedAtMs = cached.dataChangedAtMs\n'
            '                )\n'
            '            )\n'
            '            if (isStaleAcrossMidnight) next.zeroedDailyTotals() else next\n'
            '        }\n'
            '    }\n'
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="add midnight-staleness guard to refreshFromCache()",
    )

    apply_edit(
        DASHBOARD_VM_FILE,
        old=(
            '        return withCachedSnapshot.copy(\n'
            '            stepsToday = 0L,\n'
            '            distanceMeters = 0.0,\n'
            '            caloriesKcal = 0.0,\n'
            '            workoutMinutesToday = 0L,\n'
            '            activeHoursToday = 0,\n'
            '            elevationMetersToday = 0.0,\n'
            '            floorsToday = 0.0\n'
            '        )\n'
            '    }\n'
            '\n'
            '    private fun readGoalsIntoState(state: DashboardUiState): DashboardUiState = state.copy(\n'
        ),
        new=(
            '        return withCachedSnapshot.zeroedDailyTotals()\n'
            '    }\n'
            '\n'
            '    /**\n'
            "     * 2026-08-31: same midnight-rollover zeroing buildInitialState() already\n"
            '     * applied when the cache predates today, extracted so refreshFromCache()\n'
            '     * can apply the identical rule. Only the daily-total fields reset;\n'
            '     * recentWorkouts (real history) is untouched.\n'
            '     */\n'
            '    private fun DashboardUiState.zeroedDailyTotals(): DashboardUiState = copy(\n'
            '        stepsToday = 0L,\n'
            '        distanceMeters = 0.0,\n'
            '        caloriesKcal = 0.0,\n'
            '        workoutMinutesToday = 0L,\n'
            '        activeHoursToday = 0,\n'
            '        elevationMetersToday = 0.0,\n'
            '        floorsToday = 0.0\n'
            '    )\n'
            '\n'
            '    private fun readGoalsIntoState(state: DashboardUiState): DashboardUiState = state.copy(\n'
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="extract zeroedDailyTotals() helper, use it from buildInitialState()",
    )

    validate_kotlin_braces(DASHBOARD_VM_FILE)

    print("== Build gate: :app:compileDebugKotlin ==")
    gradlew = REPO_ROOT / "gradlew"
    if not gradlew.exists():
        die("gradlew not found at repo root")

    result = subprocess.run(
        [
            str(gradlew), ":app:compileDebugKotlin",
            "--no-daemon", "--max-workers=1", "--no-watch-fs", "--console=plain",
            "-Dorg.gradle.jvmargs=-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8",
            "-Pkotlin.compiler.execution.strategy=in-process",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    print(result.stdout[-4000:])
    if result.returncode != 0:
        print(result.stderr[-4000:], file=sys.stderr)
        die("compileDebugKotlin failed -- not committing/pushing. See output above.")

    print("== Compile gate passed. Checking for changes to commit. ==")
    subprocess.run(["git", "add", "-A"], cwd=str(REPO_ROOT), check=True)

    status_result = subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(REPO_ROOT), capture_output=True, text=True
    )
    if not status_result.stdout.strip():
        print("Nothing staged to commit (all steps already applied on a prior run). Skipping commit/push.")
        print("Done.")
        return

    commit_msg = (
        "Fix Syncing indicator never showing + yesterday's steps flash at midnight\n\n"
        "Both root-caused against a real device diagnostic log (2026-08-31).\n\n"
        "- HuaweiConfig.kt / BackgroundSyncScheduler.kt: new SYNC_ACTIVITY_TAG,\n"
        "  applied only to SyncWorker's periodic + one-time requests (not the\n"
        "  unrelated EveningReminderWorker, which shares the older generic\n"
        "  SYNC_WORKER_TAG).\n"
        "- MainActivity.kt: observes WorkManager.getWorkInfosByTagLiveData for\n"
        "  that tag and feeds SyncViewModel.setBackgroundSyncActive().\n"
        "- SyncViewModel.kt: SyncUiState.isSyncing is now a computed property\n"
        "  (isUiTriggeredSyncing || isBackgroundSyncActive) instead of one flag\n"
        "  only ever set by markSyncStarted()/markSyncCompleted(), which never\n"
        "  fired when a periodic background sync (not a UI-triggered one) won\n"
        "  the sync-run lease race -- confirmed directly in the log, where the\n"
        "  UI-triggered attempt's own started->completed pair collapsed to\n"
        "  under a second while the periodic worker did the real 10s sync.\n"
        "- DashboardViewModel.kt: refreshFromCache() now applies the same\n"
        "  cache-predates-today guard buildInitialState() already had.\n"
        "  refreshFromCache() is also invoked from SyncOrchestrator's\n"
        "  lease-collision retry timer, which can read the on-disk cache in\n"
        "  the narrow window before a fresh new-day sync write lands --\n"
        "  previously that re-applied yesterday's real numbers over the\n"
        "  already-correctly-zeroed dashboard until a later refresh corrected\n"
        "  it again a few seconds later. Extracted the zeroing logic into a\n"
        "  shared zeroedDailyTotals() helper used by both code paths.\n"
    )
    commit_result = subprocess.run(
        ["git", "commit", "-m", commit_msg], cwd=str(REPO_ROOT), capture_output=True, text=True
    )
    if commit_result.returncode != 0:
        print(commit_result.stdout)
        print(commit_result.stderr, file=sys.stderr)
        die("git commit failed")
    print(commit_result.stdout)

    push_result = subprocess.run(
        ["git", "push", "origin", "HEAD:main"], cwd=str(REPO_ROOT), capture_output=True, text=True
    )
    print(push_result.stdout)
    if push_result.returncode != 0:
        print(push_result.stderr, file=sys.stderr)
        die("git push failed")

    print("Done.")


if __name__ == "__main__":
    main()
