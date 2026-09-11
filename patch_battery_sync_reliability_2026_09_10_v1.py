#!/usr/bin/env python3
"""
patch_battery_sync_reliability_2026_09_10_v1.py

Two things in one patch, per Paulo's explicit request to bundle them:

PART A -- background sync reliability
--------------------------------------
Diagnostic log from a real Xiaomi M2102K1G (Android 13/MIUI) device showed
a ~5.2 hour gap where the 30-minute periodic background sync never ran,
only catching up once the app was opened manually. Root cause: OEM battery
management (MIUI's autostart/battery-saver restrictions, and the
equivalent on Huawei EMUI/Magic UI) force-stopping the app process well
before WorkManager would otherwise run its next scheduled sync.
WorkManager's own library code already recovers automatically from both a
device reboot (its internal RescheduleReceiver) and an app force-stop (its
internal ForceStopRunnable) the next time the process starts for any
reason -- so this patch does NOT add a custom BOOT_COMPLETED receiver,
which would only duplicate what WorkManager already does and was
considered and rejected as unnecessary (YAGNI) after checking WorkManager's
own documented internals. What this patch actually does:

  1. Moves BackgroundSyncScheduler.schedulePeriodic()/scheduleEveningReminder()
     from MainActivity.onCreate() to SyncApplication.onCreate(), so BitLut's
     own idempotent scheduling call runs on every process start (including
     ones triggered by WorkManager's own background executor), not only
     when a person taps the launcher icon. Both calls are already
     idempotent (ExistingPeriodicWorkPolicy.KEEP + a one-time migration
     flag), so this has no duplicate-scheduling risk.
  2. Adds an Android 12+ (API 31) advisory card in Settings
     (BatteryOptimizationCard) that detects when the OS reports BitLut is
     not exempt from battery optimization and opens the general "ignore
     battery optimizations" settings list (ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)
     -- not the direct one-tap ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS
     dialog, which needs an extra manifest permission and is meant for
     apps whose core function requires the exemption (VPNs, alarm clocks),
     not best-effort background sync like BitLut's. No new manifest
     permission is added by this patch.

This does NOT fix background sync by itself -- only the person can grant
the OS-level exemption. What it fixes is that BitLut now visibly tells the
person when the exemption is missing and gives them a one-tap way to reach
the right settings screen, instead of silently degrading for hours with no
explanation.

PART B -- code-quality pass (DRY/SOLID/KISS/YAGNI), requested in the same
sprint
--------------------------------------------------------------------------
A full-codebase review against these principles was run before writing
this patch. Most of the codebase held up well (HuaweiHealthManager's
per-metric read functions already share a common readMetric() core with
only genuinely-differing per-metric logic left duplicated; AppContainer.kt
is a clean, well-documented DI setup with correct dependency inversion via
HealthConnectManager/HuaweiHealthReader interfaces; GoalPrefs.kt already
documents its own YAGNI discipline). Three concrete, low-risk findings
were fixed:

  3. GoogleHealthManager.kt: writeDistanceBatch/writeFloorsBatch/
     writeElevationBatch/writeActiveCaloriesBatch were four functions with
     an identical filter-then-map-then-replaceRecords shape, differing
     only in field name, predicate, and record type. Extracted a single
     private generic writeContinuousMetricBatch() helper; all four
     existing call signatures and behavior are unchanged.
  4. FinalBitLutShell.kt: PrimaryButton and SecondaryButton duplicated
     their entire interaction-source/press-scale-animation/shape/
     elevation/content-padding/text-styling block, differing only in
     colors and border. Extracted a shared private PillActionButton core;
     PrimaryButton/SecondaryButton remain as thin, identically-named
     wrappers so no call site anywhere in the file changes.
  5. WorkoutFilterPrefs.kt: setMinDurationMinutes(), setExcludedExerciseTypes(),
     and MIN_DURATION_PRESETS_MINUTES had zero callers anywhere in the
     codebase (verified by exact-name grep across the full source tree,
     not a heuristic) -- write-side API left over from a Settings UI that
     was removed. Removed per Paulo's explicit decision. The read side
     (minDurationMinutes(), excludedExerciseTypes(), apply()) is fully
     live and unchanged.

One first-pass automated unused-import sweep was run and discarded: its
"body after last import" slicing heuristic produced obviously wrong
results (e.g. flagging ComponentActivity/setContent in MainActivity.kt as
unused when both are trivially used), so per this project's own documented
lesson about automated sweeps needing individual verification, none of
those findings are included here rather than reporting an unverified list.

FinalBitLutShell.kt's size (~2500 lines, 41 composables) was noted as a
Single-Responsibility observation but deliberately NOT acted on: splitting
it purely for line-count reasons, with no real Kotlin compiler available
in the environment that generated this patch to verify a large mechanical
refactor, would trade a real, working file for meaningfully higher
regression risk with no functional benefit -- flagged for Paulo's own
future judgment call, not fixed here.

Mandatory workflow already completed before this script was written:
hand-edited a mirror -> real diffs (diff -u against the canonical tree from
the latest repomix export) -> this script generated from those diffs ->
tested on a clean extraction with a fake gradlew -> byte-diffed against
the mirror -> re-run for idempotency.
"""
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"

WORKOUT_FILTER_PREFS_FILE = REPO_ROOT / "app" / "src" / "main" / "java" / "com" / "openhealth" / "sync" / "config" / "WorkoutFilterPrefs.kt"
SYNC_APPLICATION_FILE = REPO_ROOT / "app" / "src" / "main" / "java" / "com" / "openhealth" / "sync" / "SyncApplication.kt"
BATTERY_HELPER_FILE = REPO_ROOT / "app" / "src" / "main" / "java" / "com" / "openhealth" / "sync" / "util" / "BatteryOptimizationHelper.kt"
MAIN_ACTIVITY_FILE = REPO_ROOT / "app" / "src" / "main" / "java" / "com" / "openhealth" / "sync" / "MainActivity.kt"
GOOGLE_HEALTH_MANAGER_FILE = REPO_ROOT / "app" / "src" / "main" / "java" / "com" / "openhealth" / "sync" / "data" / "GoogleHealthManager.kt"
FINAL_SHELL_FILE = REPO_ROOT / "app" / "src" / "main" / "java" / "com" / "openhealth" / "sync" / "ui" / "screens" / "FinalBitLutShell.kt"
STRINGS_EN_FILE = REPO_ROOT / "app" / "src" / "main" / "res" / "values" / "strings.xml"
STRINGS_RU_FILE = REPO_ROOT / "app" / "src" / "main" / "res" / "values-ru" / "strings.xml"


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
    """Pure insertion: anchor text itself is unchanged and still present after
    the edit, so idempotency cannot key on the anchor's occurrence count (it
    would still be found, as a substring of new_with_anchor, on every re-run).
    Keys instead on unique_marker, a string that only exists after this
    insertion has been applied.
    """
    text = path.read_text(encoding="utf-8")

    if unique_marker in text:
        print(f"  [skip] {description} (already applied)")
        return

    anchor_count = text.count(anchor)
    if anchor_count != 1:
        die(
            f"{description}: expected exactly 1 occurrence of anchor in {path.name}, "
            f"found {anchor_count}. Aborting -- source has diverged."
        )

    backup(path)
    text = text.replace(anchor, new_with_anchor)
    path.write_text(text, encoding="utf-8")
    print(f"  [applied] {description}")


def create_new_file(path: Path, content: str, description: str) -> None:
    """Idempotent creation of a brand-new file. Skips if the file already
    exists with this exact content; aborts if it exists with different
    content (source has diverged from what this script expects)."""
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == content:
            print(f"  [skip] {description} (already applied)")
            return
        die(
            f"{description}: {path.name} already exists with different content. "
            "Aborting -- source has diverged."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  [applied] {description}")


def validate_strings_xml_parity() -> None:
    """Real-XML-parser validation (not just text diffing) for both strings
    files this patch touches, plus an EN/RU string-count parity check --
    per this project's own documented lesson that XML comment bodies and
    other issues are only caught by a real parser, and that the project
    maintains strict 1:1 EN/RU string parity."""
    for f in (STRINGS_EN_FILE, STRINGS_RU_FILE):
        try:
            ET.parse(f)
        except ET.ParseError as e:
            die(f"{f.name} is not well-formed XML after this patch's edits: {e}")

    en_count = len(ET.parse(STRINGS_EN_FILE).getroot().findall("string"))
    ru_count = len(ET.parse(STRINGS_RU_FILE).getroot().findall("string"))
    if en_count != ru_count:
        die(
            f"EN/RU string parity broken after this patch's edits: "
            f"values/strings.xml has {en_count}, values-ru/strings.xml has {ru_count}."
        )
    print(f"  [ok] strings.xml EN/RU parity maintained ({en_count}/{ru_count})")


def run_compile_gate() -> None:
    gradlew = REPO_ROOT / "gradlew"
    if not gradlew.exists():
        die("gradlew not found; cannot run compile gate")

    cmd = [
        str(gradlew),
        ":app:assembleDebug",
        ":app:lintDebug",
        "--no-daemon",
        "--max-workers=1",
        "--no-watch-fs",
        "--console=plain",
        "-Dorg.gradle.jvmargs=-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8",
        "-Pkotlin.compiler.execution.strategy=in-process",
    ]
    print("Running compile gate: " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        die("Compile gate failed. No commit/push performed. See Gradle output above.")


def git_commit_and_push() -> None:
    subprocess.run(["git", "add", "-A"], cwd=REPO_ROOT, check=True)
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    if not status.stdout.strip():
        print("Nothing to commit (already applied and clean).")
        return

    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "Add Android 12+ battery-optimization hint, schedule periodic sync "
            "from Application.onCreate(), DRY/YAGNI cleanup pass",
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=REPO_ROOT, check=True)



WORKOUT_FILTER_PREFS_OLD = 'package com.openhealth.sync.config\n\nimport android.content.Context\nimport android.content.SharedPreferences\nimport com.openhealth.sync.data.ActivitySessionData\nimport com.openhealth.sync.data.remote.HuaweiConfig\n\n/**\n * Lets the person exclude specific workout types, or workouts shorter than a\n * minimum duration, from being written to Health Connect as discrete\n * ExerciseSessionRecord entries -- e.g. "don\'t sync walks under 5 minutes".\n *\n * This only filters the workout SESSION entries themselves. Steps, distance,\n * and calories for that same time window come from Huawei\'s separate\n * continuous data streams (see GoogleHealthManager.writeSnapshot()) and are\n * completely unaffected by this filter -- a filtered-out walk still counts\n * toward the day\'s step total, it just doesn\'t show up as its own workout\n * card. No new Huawei scope or Health Connect permission is involved: this\n * is purely app-side filtering of data that\'s already being read.\n *\n * Defaults to "everything syncs" (0-minute minimum, nothing excluded), so\n * existing installs see no behavior change until the person explicitly\n * opens Settings and changes something.\n */\nclass WorkoutFilterPrefs(context: Context) {\n\n    private val prefs: SharedPreferences = context.getSharedPreferences(\n        HuaweiConfig.PREFS_NAME,\n        Context.MODE_PRIVATE\n    )\n\n    fun minDurationMinutes(): Int = prefs.getInt(KEY_MIN_DURATION_MINUTES, 0)\n\n    fun setMinDurationMinutes(value: Int) {\n        require(value >= 0) { "Minimum duration cannot be negative" }\n        prefs.edit().putInt(KEY_MIN_DURATION_MINUTES, value).apply()\n    }\n\n    fun excludedExerciseTypes(): Set<Int> =\n        prefs.getStringSet(KEY_EXCLUDED_EXERCISE_TYPES, emptySet())\n            .orEmpty()\n            .mapNotNull { it.toIntOrNull() }\n            .toSet()\n\n    fun setExcludedExerciseTypes(types: Set<Int>) {\n        prefs.edit()\n            .putStringSet(KEY_EXCLUDED_EXERCISE_TYPES, types.map { it.toString() }.toSet())\n            .apply()\n    }\n\n    /** Applied right before a freshly-read batch of sessions is written to Health Connect. */\n    fun apply(sessions: List<ActivitySessionData>): List<ActivitySessionData> {\n        val minDurationMs = minDurationMinutes() * 60_000L\n        val excluded = excludedExerciseTypes()\n        if (minDurationMs <= 0L && excluded.isEmpty()) return sessions\n        return sessions.filter { session ->\n            val durationMs = session.endTimeMs - session.startTimeMs\n            durationMs >= minDurationMs && session.exerciseType !in excluded\n        }\n    }\n\n    companion object {\n        private const val KEY_MIN_DURATION_MINUTES = "workout_filter_min_duration_minutes"\n        private const val KEY_EXCLUDED_EXERCISE_TYPES = "workout_filter_excluded_exercise_types"\n\n        /** Preset chips offered in Settings for the minimum-duration filter. */\n        val MIN_DURATION_PRESETS_MINUTES = listOf(0, 5, 10, 15, 30)\n    }\n}'
WORKOUT_FILTER_PREFS_NEW = 'package com.openhealth.sync.config\n\nimport android.content.Context\nimport android.content.SharedPreferences\nimport com.openhealth.sync.data.ActivitySessionData\nimport com.openhealth.sync.data.remote.HuaweiConfig\n\n/**\n * Lets the person exclude specific workout types, or workouts shorter than a\n * minimum duration, from being written to Health Connect as discrete\n * ExerciseSessionRecord entries -- e.g. "don\'t sync walks under 5 minutes".\n *\n * This only filters the workout SESSION entries themselves. Steps, distance,\n * and calories for that same time window come from Huawei\'s separate\n * continuous data streams (see GoogleHealthManager.writeSnapshot()) and are\n * completely unaffected by this filter -- a filtered-out walk still counts\n * toward the day\'s step total, it just doesn\'t show up as its own workout\n * card. No new Huawei scope or Health Connect permission is involved: this\n * is purely app-side filtering of data that\'s already being read.\n *\n * Defaults to "everything syncs" (0-minute minimum, nothing excluded), so\n * existing installs see no behavior change until the person explicitly\n * opens Settings and changes something.\n *\n * Read-only from the sync path\'s perspective: the Settings UI that used to\n * let a person change these values was removed, so only the read\n * accessors below (minDurationMinutes(), excludedExerciseTypes(), apply())\n * remain. If that UI comes back, reintroduce setters at that point rather\n * than keeping unused write-side API around in the meantime (2026-09 code\n * review, DRY/YAGNI pass).\n */\nclass WorkoutFilterPrefs(context: Context) {\n\n    private val prefs: SharedPreferences = context.getSharedPreferences(\n        HuaweiConfig.PREFS_NAME,\n        Context.MODE_PRIVATE\n    )\n\n    fun minDurationMinutes(): Int = prefs.getInt(KEY_MIN_DURATION_MINUTES, 0)\n\n    fun excludedExerciseTypes(): Set<Int> =\n        prefs.getStringSet(KEY_EXCLUDED_EXERCISE_TYPES, emptySet())\n            .orEmpty()\n            .mapNotNull { it.toIntOrNull() }\n            .toSet()\n\n    /** Applied right before a freshly-read batch of sessions is written to Health Connect. */\n    fun apply(sessions: List<ActivitySessionData>): List<ActivitySessionData> {\n        val minDurationMs = minDurationMinutes() * 60_000L\n        val excluded = excludedExerciseTypes()\n        if (minDurationMs <= 0L && excluded.isEmpty()) return sessions\n        return sessions.filter { session ->\n            val durationMs = session.endTimeMs - session.startTimeMs\n            durationMs >= minDurationMs && session.exerciseType !in excluded\n        }\n    }\n\n    companion object {\n        private const val KEY_MIN_DURATION_MINUTES = "workout_filter_min_duration_minutes"\n        private const val KEY_EXCLUDED_EXERCISE_TYPES = "workout_filter_excluded_exercise_types"\n    }\n}'
SYNC_APPLICATION_OLD = 'package com.openhealth.sync\nimport android.app.Application\nimport com.openhealth.sync.di.AppContainer\nclass SyncApplication : Application() {\n    lateinit var container: AppContainer\n    override fun onCreate() {\n        super.onCreate()\n        container = AppContainer(this)\n    }\n}'
SYNC_APPLICATION_NEW = "package com.openhealth.sync\nimport android.app.Application\nimport com.openhealth.sync.data.worker.BackgroundSyncScheduler\nimport com.openhealth.sync.di.AppContainer\nclass SyncApplication : Application() {\n    lateinit var container: AppContainer\n    override fun onCreate() {\n        super.onCreate()\n        container = AppContainer(this)\n\n        // 2026-09: previously only scheduled from MainActivity.onCreate(),\n        // which meant the periodic sync and evening reminder were only\n        // re-registered when a person actually opened the app. WorkManager\n        // itself already recovers from a device reboot (its own internal\n        // RescheduleReceiver) and from the app being force-stopped (its\n        // own ForceStopRunnable, which re-applies pending work the next\n        // time this process starts for any reason) -- so this call is not\n        // what makes background sync survive those two cases, WorkManager's\n        // own library code already does that. What this closes is a\n        // narrower gap: Application.onCreate() runs on every process start,\n        // including ones triggered by WorkManager's own background executor\n        // waking the process to run a job, not just ones triggered by a\n        // person tapping the launcher icon. Both calls are idempotent\n        // (ExistingPeriodicWorkPolicy.KEEP plus a one-time SharedPreferences\n        // migration flag), so calling them here in addition to their\n        // existing MainActivity call has no duplicate-scheduling risk.\n        BackgroundSyncScheduler.schedulePeriodic(this)\n        BackgroundSyncScheduler.scheduleEveningReminder(this)\n    }\n}"
BATTERY_HELPER_CONTENT = 'package com.openhealth.sync.util\n\nimport android.content.Context\nimport android.content.Intent\nimport android.net.Uri\nimport android.os.Build\nimport android.os.PowerManager\nimport android.provider.Settings\n\n/**\n * Android 12+ (API 31) advisory for OEM battery/autostart restrictions.\n *\n * BitLut\'s background sync (BackgroundSyncScheduler\'s 30-minute\n * PeriodicWorkRequest) already relies on WorkManager\'s own guarantees, which\n * are sufficient on stock Android. On OEM skins with their own aggressive\n * battery managers (EMUI/Magic UI "Protected Apps", MIUI/HyperOS\n * autostart/battery saver, and similar on other manufacturers), the OS can\n * still force-stop the app process well before WorkManager would otherwise\n * run it again -- WorkManager recovers automatically the next time the\n * process starts for any reason, but if the OEM restriction keeps\n * preventing that, syncs can silently stop appearing for hours. This can\'t\n * be fixed from inside the app; the person has to grant the exemption\n * themselves. This helper only detects the condition and opens the\n * relevant system settings screen -- it never requests the exemption\n * directly (see below for why).\n *\n * Scoped to API 31+ only: this is when BitLut\'s diagnostic evidence for\n * this failure mode exists, and Android\'s own battery-settings UI varies\n * enough release to release that supporting every version back to minSdk\n * 26 was judged not worth the added surface for a single advisory card.\n */\nobject BatteryOptimizationHelper {\n\n    /**\n     * True when the OS reports BitLut is currently *not* exempt from\n     * battery optimizations and the advisory is relevant on this API\n     * level. False on API < 31 (the hint isn\'t shown there) so callers can\n     * gate the whole card on this one check.\n     */\n    fun shouldShowHint(context: Context): Boolean {\n        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return false\n        val powerManager = context.getSystemService(Context.POWER_SERVICE) as? PowerManager\n            ?: return false\n        return !powerManager.isIgnoringBatteryOptimizations(context.packageName)\n    }\n\n    /**\n     * Opens the general "Ignore battery optimizations" list (Settings >\n     * Apps > Special app access > Battery optimization on stock Android;\n     * the OEM equivalent on EMUI/MIUI/etc.) rather than\n     * ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS\' direct one-tap grant\n     * dialog. The direct dialog needs the REQUEST_IGNORE_BATTERY_OPTIMIZATIONS\n     * permission and is meant for apps whose core function requires it\n     * (e.g. VPNs, alarm clocks); BitLut\'s periodic sync is exactly the kind\n     * of best-effort background work Android\'s own developer guidance\n     * says should NOT use that permission. Landing on the list keeps this\n     * a plain, review-safe settings deep link with no extra permission\n     * declaration, at the cost of the person needing to find BitLut in the\n     * list themselves instead of a single tap.\n     */\n    fun settingsIntent(): Intent =\n        Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)\n}\n'
OLD_WRITE_BATCH_BLOCK = '    private suspend fun writeDistanceBatch(records: List<DistanceData>): Boolean {\n        val valid = records\n            .filter { it.meters > 0.0 && it.startTimeMs < it.endTimeMs }\n            .map {\n                val start = Instant.ofEpochMilli(it.startTimeMs)\n                val end = Instant.ofEpochMilli(it.endTimeMs)\n                DistanceRecord(\n                    distance = Length.meters(it.meters),\n                    startTime = start,\n                    endTime = end,\n                    startZoneOffset = offset(start),\n                    endZoneOffset = offset(end),\n                    metadata = bitlutMetadata("distance", start.toEpochMilli(), end.toEpochMilli())\n                )\n            }\n\n        return replaceRecords("distance", valid, DistanceRecord::class)\n    }\n\n    private suspend fun writeFloorsBatch(records: List<FloorsData>): Boolean {\n        val valid = records\n            .filter { it.floors > 0.0 && it.startTimeMs < it.endTimeMs }\n            .map {\n                val start = Instant.ofEpochMilli(it.startTimeMs)\n                val end = Instant.ofEpochMilli(it.endTimeMs)\n                FloorsClimbedRecord(\n                    floors = it.floors,\n                    startTime = start,\n                    endTime = end,\n                    startZoneOffset = offset(start),\n                    endZoneOffset = offset(end),\n                    metadata = bitlutMetadata("floors", start.toEpochMilli(), end.toEpochMilli())\n                )\n            }\n\n        return replaceRecords("floors", valid, FloorsClimbedRecord::class)\n    }\n\n    private suspend fun writeElevationBatch(records: List<ElevationData>): Boolean {\n        val valid = records\n            .filter { it.meters > 0.0 && it.startTimeMs < it.endTimeMs }\n            .map {\n                val start = Instant.ofEpochMilli(it.startTimeMs)\n                val end = Instant.ofEpochMilli(it.endTimeMs)\n                ElevationGainedRecord(\n                    elevation = Length.meters(it.meters),\n                    startTime = start,\n                    endTime = end,\n                    startZoneOffset = offset(start),\n                    endZoneOffset = offset(end),\n                    metadata = bitlutMetadata("elevation", start.toEpochMilli(), end.toEpochMilli())\n                )\n            }\n\n        return replaceRecords("elevation", valid, ElevationGainedRecord::class)\n    }\n\n    private suspend fun writeActiveCaloriesBatch(records: List<ActiveCaloriesData>): Boolean {\n        val valid = records\n            .filter { it.kilocalories > 0.0 && it.startTimeMs < it.endTimeMs }\n            .map {\n                val start = Instant.ofEpochMilli(it.startTimeMs)\n                val end = Instant.ofEpochMilli(it.endTimeMs)\n                ActiveCaloriesBurnedRecord(\n                    energy = Energy.kilocalories(it.kilocalories),\n                    startTime = start,\n                    endTime = end,\n                    startZoneOffset = offset(start),\n                    endZoneOffset = offset(end),\n                    metadata = bitlutMetadata("active_calories", start.toEpochMilli(), end.toEpochMilli())\n                )\n            }\n\n        return replaceRecords("activeCalories", valid, ActiveCaloriesBurnedRecord::class)\n    }\n'
NEW_WRITE_BATCH_BLOCK = '    /**\n     * Shared filter -> map -> replaceRecords shape used by the four simple\n     * continuous-metric writers below (distance/floors/elevation/active\n     * calories). Each of those record types differs only in which field\n     * counts as "present" (a positive value) and how to construct its own\n     * Health Connect record; both are supplied by the caller so this stays\n     * a plain helper rather than a new abstraction layer (2026-09 DRY pass\n     * -- the four call sites were previously hand-duplicated).\n     */\n    private suspend fun <T> writeContinuousMetricBatch(\n        label: String,\n        records: List<T>,\n        recordType: KClass<out Record>,\n        hasValue: (T) -> Boolean,\n        startTimeMs: (T) -> Long,\n        endTimeMs: (T) -> Long,\n        toRecord: (T, Instant, Instant) -> Record\n    ): Boolean {\n        val valid = records\n            .filter { hasValue(it) && startTimeMs(it) < endTimeMs(it) }\n            .map {\n                val start = Instant.ofEpochMilli(startTimeMs(it))\n                val end = Instant.ofEpochMilli(endTimeMs(it))\n                toRecord(it, start, end)\n            }\n\n        return replaceRecords(label, valid, recordType)\n    }\n\n    private suspend fun writeDistanceBatch(records: List<DistanceData>): Boolean =\n        writeContinuousMetricBatch(\n            label = "distance",\n            records = records,\n            recordType = DistanceRecord::class,\n            hasValue = { it.meters > 0.0 },\n            startTimeMs = { it.startTimeMs },\n            endTimeMs = { it.endTimeMs },\n            toRecord = { data, start, end ->\n                DistanceRecord(\n                    distance = Length.meters(data.meters),\n                    startTime = start,\n                    endTime = end,\n                    startZoneOffset = offset(start),\n                    endZoneOffset = offset(end),\n                    metadata = bitlutMetadata("distance", start.toEpochMilli(), end.toEpochMilli())\n                )\n            }\n        )\n\n    private suspend fun writeFloorsBatch(records: List<FloorsData>): Boolean =\n        writeContinuousMetricBatch(\n            label = "floors",\n            records = records,\n            recordType = FloorsClimbedRecord::class,\n            hasValue = { it.floors > 0.0 },\n            startTimeMs = { it.startTimeMs },\n            endTimeMs = { it.endTimeMs },\n            toRecord = { data, start, end ->\n                FloorsClimbedRecord(\n                    floors = data.floors,\n                    startTime = start,\n                    endTime = end,\n                    startZoneOffset = offset(start),\n                    endZoneOffset = offset(end),\n                    metadata = bitlutMetadata("floors", start.toEpochMilli(), end.toEpochMilli())\n                )\n            }\n        )\n\n    private suspend fun writeElevationBatch(records: List<ElevationData>): Boolean =\n        writeContinuousMetricBatch(\n            label = "elevation",\n            records = records,\n            recordType = ElevationGainedRecord::class,\n            hasValue = { it.meters > 0.0 },\n            startTimeMs = { it.startTimeMs },\n            endTimeMs = { it.endTimeMs },\n            toRecord = { data, start, end ->\n                ElevationGainedRecord(\n                    elevation = Length.meters(data.meters),\n                    startTime = start,\n                    endTime = end,\n                    startZoneOffset = offset(start),\n                    endZoneOffset = offset(end),\n                    metadata = bitlutMetadata("elevation", start.toEpochMilli(), end.toEpochMilli())\n                )\n            }\n        )\n\n    private suspend fun writeActiveCaloriesBatch(records: List<ActiveCaloriesData>): Boolean =\n        writeContinuousMetricBatch(\n            label = "activeCalories",\n            records = records,\n            recordType = ActiveCaloriesBurnedRecord::class,\n            hasValue = { it.kilocalories > 0.0 },\n            startTimeMs = { it.startTimeMs },\n            endTimeMs = { it.endTimeMs },\n            toRecord = { data, start, end ->\n                ActiveCaloriesBurnedRecord(\n                    energy = Energy.kilocalories(data.kilocalories),\n                    startTime = start,\n                    endTime = end,\n                    startZoneOffset = offset(start),\n                    endZoneOffset = offset(end),\n                    metadata = bitlutMetadata("active_calories", start.toEpochMilli(), end.toEpochMilli())\n                )\n            }\n        )\n'
OLD_BUTTONS_BLOCK = '@Composable\nprivate fun PrimaryButton(\n    text: String,\n    enabled: Boolean = true,\n    compact: Boolean = false,\n    modifier: Modifier = Modifier.fillMaxWidth(),\n    onClick: () -> Unit\n) {\n    val interactionSource = remember { MutableInteractionSource() }\n    val pressed by interactionSource.collectIsPressedAsState()\n    val focused by interactionSource.collectIsFocusedAsState()\n    val scale by animateFloatAsState(\n        targetValue = if (pressed) 0.985f else 1f,\n        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),\n        label = "primaryButtonScale"\n    )\n    val shape = RoundedCornerShape(AugustRadius.Pill)\n\n    Button(\n        onClick = onClick,\n        enabled = enabled,\n        interactionSource = interactionSource,\n        modifier = modifier\n            .heightIn(min = 48.dp)\n            .graphicsLayer {\n                scaleX = scale\n                scaleY = scale\n            },\n        shape = shape,\n        colors = ButtonDefaults.buttonColors(\n            containerColor = AugustColor.Lime,\n            contentColor = AugustColor.LimeInk,\n            disabledContainerColor = AugustColor.Soft,\n            disabledContentColor = AugustColor.Muted\n        ),\n        border = if (focused) BorderStroke(2.dp, AugustColor.Purple) else null,\n        elevation = ButtonDefaults.buttonElevation(\n            defaultElevation = 0.dp,\n            pressedElevation = 0.dp,\n            disabledElevation = 0.dp\n        ),\n        contentPadding = if (compact) {\n            PaddingValues(horizontal = 14.dp, vertical = 10.dp)\n        } else {\n            PaddingValues(horizontal = 20.dp, vertical = 12.dp)\n        }\n    ) {\n        Text(\n            text = text,\n            fontWeight = FontWeight.Bold,\n            fontSize = if (compact) 12.sp else 14.sp,\n            maxLines = 1,\n            overflow = TextOverflow.Ellipsis\n        )\n    }\n}\n\n/** Quiet secondary action: flat neutral fill, pill shape, Purple focus. */\n@Composable\nprivate fun SecondaryButton(\n    text: String,\n    palette: BitPalette,\n    enabled: Boolean = true,\n    compact: Boolean = false,\n    modifier: Modifier = Modifier.fillMaxWidth(),\n    onClick: () -> Unit\n) {\n    val interactionSource = remember { MutableInteractionSource() }\n    val pressed by interactionSource.collectIsPressedAsState()\n    val focused by interactionSource.collectIsFocusedAsState()\n    val scale by animateFloatAsState(\n        targetValue = if (pressed) 0.985f else 1f,\n        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),\n        label = "secondaryButtonScale"\n    )\n    val shape = RoundedCornerShape(AugustRadius.Pill)\n\n    Button(\n        onClick = onClick,\n        enabled = enabled,\n        interactionSource = interactionSource,\n        modifier = modifier\n            .heightIn(min = 48.dp)\n            .graphicsLayer {\n                scaleX = scale\n                scaleY = scale\n            },\n        shape = shape,\n        colors = ButtonDefaults.buttonColors(\n            containerColor = if (palette.dark) AugustColor.NavySoft else AugustColor.Soft,\n            contentColor = if (palette.dark) AugustColor.Surface else AugustColor.Ink,\n            disabledContainerColor = if (palette.dark) AugustColor.NavySoft.copy(alpha = 0.55f) else AugustColor.Soft.copy(alpha = 0.65f),\n            disabledContentColor = if (palette.dark) AugustColor.DarkSecondaryText.copy(alpha = 0.70f) else AugustColor.Muted.copy(alpha = 0.75f)\n        ),\n        border = BorderStroke(\n            width = if (focused) 2.dp else 1.dp,\n            color = if (focused) AugustColor.Purple else palette.stroke\n        ),\n        elevation = ButtonDefaults.buttonElevation(\n            defaultElevation = 0.dp,\n            pressedElevation = 0.dp,\n            disabledElevation = 0.dp\n        ),\n        contentPadding = if (compact) {\n            PaddingValues(horizontal = 14.dp, vertical = 10.dp)\n        } else {\n            PaddingValues(horizontal = 20.dp, vertical = 12.dp)\n        }\n    ) {\n        Text(\n            text = text,\n            fontWeight = FontWeight.Bold,\n            fontSize = if (compact) 12.sp else 14.sp,\n            maxLines = 1,\n            overflow = TextOverflow.Ellipsis\n        )\n    }\n}\n'
NEW_BUTTONS_BLOCK = '/**\n * Shared pill-button core for PrimaryButton and SecondaryButton below, which\n * previously duplicated this entire interaction-source/press-scale-\n * animation/shape/elevation/content-padding/text block, differing only in\n * colors and border (2026-09 DRY pass). Kept private and un-exported: call\n * sites should keep using the two named wrappers below, not this directly,\n * so "which button style am I using" stays a one-word decision at the call\n * site rather than requiring callers to assemble ButtonColors themselves.\n */\n@Composable\nprivate fun PillActionButton(\n    text: String,\n    colors: ButtonColors,\n    border: BorderStroke?,\n    enabled: Boolean,\n    compact: Boolean,\n    modifier: Modifier,\n    animationLabel: String,\n    onClick: () -> Unit\n) {\n    val interactionSource = remember { MutableInteractionSource() }\n    val pressed by interactionSource.collectIsPressedAsState()\n    val scale by animateFloatAsState(\n        targetValue = if (pressed) 0.985f else 1f,\n        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),\n        label = animationLabel\n    )\n    val shape = RoundedCornerShape(AugustRadius.Pill)\n\n    Button(\n        onClick = onClick,\n        enabled = enabled,\n        interactionSource = interactionSource,\n        modifier = modifier\n            .heightIn(min = 48.dp)\n            .graphicsLayer {\n                scaleX = scale\n                scaleY = scale\n            },\n        shape = shape,\n        colors = colors,\n        border = border,\n        elevation = ButtonDefaults.buttonElevation(\n            defaultElevation = 0.dp,\n            pressedElevation = 0.dp,\n            disabledElevation = 0.dp\n        ),\n        contentPadding = if (compact) {\n            PaddingValues(horizontal = 14.dp, vertical = 10.dp)\n        } else {\n            PaddingValues(horizontal = 20.dp, vertical = 12.dp)\n        }\n    ) {\n        Text(\n            text = text,\n            fontWeight = FontWeight.Bold,\n            fontSize = if (compact) 12.sp else 14.sp,\n            maxLines = 1,\n            overflow = TextOverflow.Ellipsis\n        )\n    }\n}\n\n@Composable\nprivate fun PrimaryButton(\n    text: String,\n    enabled: Boolean = true,\n    compact: Boolean = false,\n    modifier: Modifier = Modifier.fillMaxWidth(),\n    onClick: () -> Unit\n) {\n    val interactionSource = remember { MutableInteractionSource() }\n    val focused by interactionSource.collectIsFocusedAsState()\n    PillActionButton(\n        text = text,\n        colors = ButtonDefaults.buttonColors(\n            containerColor = AugustColor.Lime,\n            contentColor = AugustColor.LimeInk,\n            disabledContainerColor = AugustColor.Soft,\n            disabledContentColor = AugustColor.Muted\n        ),\n        border = if (focused) BorderStroke(2.dp, AugustColor.Purple) else null,\n        enabled = enabled,\n        compact = compact,\n        modifier = modifier,\n        animationLabel = "primaryButtonScale",\n        onClick = onClick\n    )\n}\n\n/** Quiet secondary action: flat neutral fill, pill shape, Purple focus. */\n@Composable\nprivate fun SecondaryButton(\n    text: String,\n    palette: BitPalette,\n    enabled: Boolean = true,\n    compact: Boolean = false,\n    modifier: Modifier = Modifier.fillMaxWidth(),\n    onClick: () -> Unit\n) {\n    val interactionSource = remember { MutableInteractionSource() }\n    val focused by interactionSource.collectIsFocusedAsState()\n    PillActionButton(\n        text = text,\n        colors = ButtonDefaults.buttonColors(\n            containerColor = if (palette.dark) AugustColor.NavySoft else AugustColor.Soft,\n            contentColor = if (palette.dark) AugustColor.Surface else AugustColor.Ink,\n            disabledContainerColor = if (palette.dark) AugustColor.NavySoft.copy(alpha = 0.55f) else AugustColor.Soft.copy(alpha = 0.65f),\n            disabledContentColor = if (palette.dark) AugustColor.DarkSecondaryText.copy(alpha = 0.70f) else AugustColor.Muted.copy(alpha = 0.75f)\n        ),\n        border = BorderStroke(\n            width = if (focused) 2.dp else 1.dp,\n            color = if (focused) AugustColor.Purple else palette.stroke\n        ),\n        enabled = enabled,\n        compact = compact,\n        modifier = modifier,\n        animationLabel = "secondaryButtonScale",\n        onClick = onClick\n    )\n}\n'

def main() -> None:
    print("=== 1/8: config/WorkoutFilterPrefs.kt -- remove unused setters (YAGNI) ===")
    apply_edit(
        WORKOUT_FILTER_PREFS_FILE,
        old=WORKOUT_FILTER_PREFS_OLD,
        new=WORKOUT_FILTER_PREFS_NEW,
        expected_old_count=1,
        expected_new_count=1,
        description="WorkoutFilterPrefs.kt: remove setMinDurationMinutes/setExcludedExerciseTypes/MIN_DURATION_PRESETS_MINUTES (zero callers)",
    )

    print("=== 2/8: SyncApplication.kt -- schedule periodic sync on every process start ===")
    apply_edit(
        SYNC_APPLICATION_FILE,
        old=SYNC_APPLICATION_OLD,
        new=SYNC_APPLICATION_NEW,
        expected_old_count=1,
        expected_new_count=1,
        description="SyncApplication.kt: call BackgroundSyncScheduler.schedulePeriodic()/scheduleEveningReminder() from onCreate()",
    )

    print("=== 3/8: util/BatteryOptimizationHelper.kt (new file) ===")
    create_new_file(
        BATTERY_HELPER_FILE,
        BATTERY_HELPER_CONTENT,
        description="util/BatteryOptimizationHelper.kt: create Android 12+ battery-optimization check + settings intent helper",
    )

    print("=== 4/8: MainActivity.kt -- battery hint state, onResume recheck, drop redundant scheduling ===")
    apply_insertion(
        MAIN_ACTIVITY_FILE,
        anchor=(
            "    private val syncOrchestrator: SyncOrchestrator by lazy {\n"
            "        SyncOrchestrator(this, syncViewModel.googleManager)\n"
            "    }\n"
        ),
        new_with_anchor=(
            "    private val syncOrchestrator: SyncOrchestrator by lazy {\n"
            "        SyncOrchestrator(this, syncViewModel.googleManager)\n"
            "    }\n"
            "\n"
            "    // 2026-09: read by FinalBitLutShell/SettingsScreen to show/hide\n"
            "    // BatteryOptimizationCard. Backed by a mutableStateOf (not a plain var)\n"
            "    // so Compose recomposes the moment onResume() updates it -- e.g. right\n"
            "    // after the person returns from granting the exemption in system\n"
            "    // settings. androidx.compose.runtime.mutableStateOf is used directly\n"
            "    // (matching the existing hasSeenOnboarding pattern in setContent)\n"
            "    // rather than adding this to a ViewModel: it's pure OS state with no\n"
            "    // persistence or business logic of its own.\n"
            "    private var showBatteryHint by androidx.compose.runtime.mutableStateOf(false)\n"
            "\n"
            "    private fun refreshBatteryHintState() {\n"
            "        showBatteryHint = com.openhealth.sync.util.BatteryOptimizationHelper.shouldShowHint(this)\n"
            "    }\n"
            "\n"
            "    private fun openBatteryOptimizationSettings() {\n"
            "        try {\n"
            "            startActivity(com.openhealth.sync.util.BatteryOptimizationHelper.settingsIntent())\n"
            "        } catch (e: Exception) {\n"
            "            AppLogger.e(\"MainActivity\", \"Failed to open battery optimization settings: ${e.message}\", e)\n"
            "            Toast.makeText(this, getString(R.string.toast_battery_settings_launch_failed), Toast.LENGTH_LONG).show()\n"
            "        }\n"
            "    }\n"
        ),
        unique_marker="private fun refreshBatteryHintState()",
        description="MainActivity.kt: add showBatteryHint state + refresh/open helpers",
    )
    apply_insertion(
        MAIN_ACTIVITY_FILE,
        anchor=(
            "                        onboardingPrefs.markPermissionsRationaleSeen()\n"
            "                        hasSeenOnboarding = true\n"
            "                    },\n"
            "                    importViewModel = importViewModel\n"
            "                )\n"
        ),
        new_with_anchor=(
            "                        onboardingPrefs.markPermissionsRationaleSeen()\n"
            "                        hasSeenOnboarding = true\n"
            "                    },\n"
            "                    showBatteryHint = showBatteryHint,\n"
            "                    onOpenBatterySettings = { openBatteryOptimizationSettings() },\n"
            "                    importViewModel = importViewModel\n"
            "                )\n"
        ),
        unique_marker="onOpenBatterySettings = { openBatteryOptimizationSettings() }",
        description="MainActivity.kt: pass showBatteryHint/onOpenBatterySettings into FinalBitLutShell(...)",
    )
    apply_insertion(
        MAIN_ACTIVITY_FILE,
        anchor=(
            "    override fun onResume() {\n"
            "        super.onResume()\n"
            "        refreshUiStatusOnLaunch()\n"
            "        if (awaitingSystemResult) {\n"
        ),
        new_with_anchor=(
            "    override fun onResume() {\n"
            "        super.onResume()\n"
            "        refreshUiStatusOnLaunch()\n"
            "        refreshBatteryHintState()\n"
            "        if (awaitingSystemResult) {\n"
        ),
        unique_marker="refreshBatteryHintState()\n        if (awaitingSystemResult)",
        description="MainActivity.kt: recheck battery-hint state on every onResume",
    )
    apply_edit(
        MAIN_ACTIVITY_FILE,
        old=(
            "    private fun setupPeriodicSync() {\n"
            "        syncOrchestrator.schedulePeriodic()\n"
            "        com.openhealth.sync.data.worker.BackgroundSyncScheduler.scheduleEveningReminder(this)\n"
            "        requestNotificationPermissionIfNeeded()\n"
            "    }\n"
        ),
        new=(
            "    // 2026-09: periodic-sync and evening-reminder scheduling moved to\n"
            "    // SyncApplication.onCreate() (runs on every process start, not just\n"
            "    // when this Activity is created); this now only requests the\n"
            "    // notification permission, which needs an Activity/launcher.\n"
            "    private fun setupPeriodicSync() {\n"
            "        requestNotificationPermissionIfNeeded()\n"
            "    }\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="MainActivity.kt: setupPeriodicSync() no longer duplicates SyncApplication's scheduling",
    )

    print("=== 5/8: data/GoogleHealthManager.kt -- consolidate the four write*Batch functions (DRY) ===")
    apply_edit(
        GOOGLE_HEALTH_MANAGER_FILE,
        old=OLD_WRITE_BATCH_BLOCK,
        new=NEW_WRITE_BATCH_BLOCK,
        expected_old_count=1,
        expected_new_count=1,
        description="GoogleHealthManager.kt: extract shared writeContinuousMetricBatch() helper",
    )

    print("=== 6/8: ui/screens/FinalBitLutShell.kt -- battery card, imports, button consolidation ===")
    apply_insertion(
        FINAL_SHELL_FILE,
        anchor="import androidx.compose.material.icons.rounded.Schedule\n",
        new_with_anchor=(
            "import androidx.compose.material.icons.rounded.Schedule\n"
            "import androidx.compose.material.icons.rounded.BatteryAlert\n"
        ),
        unique_marker="import androidx.compose.material.icons.rounded.BatteryAlert",
        description="FinalBitLutShell.kt: import BatteryAlert icon",
    )
    apply_edit(
        FINAL_SHELL_FILE,
        old=(
            "import androidx.compose.material3.Button\n"
            "import androidx.compose.material3.ButtonDefaults\n"
        ),
        new=(
            "import androidx.compose.material3.Button\n"
            "import androidx.compose.material3.ButtonColors\n"
            "import androidx.compose.material3.ButtonDefaults\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="FinalBitLutShell.kt: import ButtonColors (needed by the new shared PillActionButton)",
    )
    apply_insertion(
        FINAL_SHELL_FILE,
        anchor=(
            "/** One row in the exclusive source selector. A selected switch cannot\n"
            " *  be turned off by itself, which guarantees there is never a zero-source\n"
            " *  state; enabling the other row atomically deselects this one. */\n"
            "@Composable\n"
            "private fun DataSourceToggleRow(\n"
        ),
        new_with_anchor=(
            "/**\n"
            " * Android 12+ (API 31) advisory: warns when the OS reports BitLut is not\n"
            " * exempt from battery optimization, since OEM battery managers (Huawei\n"
            " * EMUI/Magic UI \"Protected Apps\", Xiaomi MIUI/HyperOS autostart/battery\n"
            " * saver, and similar) can force-stop the app well before its 30-minute\n"
            " * background sync would otherwise run again. See\n"
            " * util/BatteryOptimizationHelper.kt's doc comment for why this only opens\n"
            " * the general settings list rather than requesting the exemption directly.\n"
            " * Re-evaluated by the caller on every return to Settings (see\n"
            " * SettingsScreen's showBatteryHint parameter), so this card disappears as\n"
            " * soon as the person grants the exemption and comes back -- it does not\n"
            " * poll or observe on its own.\n"
            " */\n"
            "@Composable\n"
            "private fun BatteryOptimizationCard(palette: BitPalette, onOpenBatterySettings: () -> Unit) {\n"
            "    SoftCard(palette = palette) {\n"
            "        Row(verticalAlignment = Alignment.Top) {\n"
            "            Icon(\n"
            "                Icons.Rounded.BatteryAlert,\n"
            "                contentDescription = null,\n"
            "                tint = HealthAccent.activity(),\n"
            "                modifier = Modifier.size(20.dp)\n"
            "            )\n"
            "            Spacer(Modifier.width(10.dp))\n"
            "            Column {\n"
            "                Text(\n"
            "                    text = stringResource(R.string.battery_optimization_title),\n"
            "                    color = palette.text,\n"
            "                    fontWeight = FontWeight.ExtraBold,\n"
            "                    fontSize = 15.sp\n"
            "                )\n"
            "                Spacer(Modifier.height(4.dp))\n"
            "                Text(\n"
            "                    text = stringResource(R.string.battery_optimization_body),\n"
            "                    color = palette.secondaryText,\n"
            "                    fontWeight = FontWeight.Medium,\n"
            "                    fontSize = 13.sp,\n"
            "                    lineHeight = 18.sp\n"
            "                )\n"
            "                Spacer(Modifier.height(10.dp))\n"
            "                val interactionSource = remember { MutableInteractionSource() }\n"
            "                Box(\n"
            "                    modifier = Modifier\n"
            "                        .pressScale(interactionSource)\n"
            "                        .clip(RoundedCornerShape(AugustRadius.Button))\n"
            "                        .background(AugustColor.Lime)\n"
            "                        .clickable(interactionSource = interactionSource, indication = null) { onOpenBatterySettings() }\n"
            "                        .padding(horizontal = 16.dp, vertical = 9.dp)\n"
            "                ) {\n"
            "                    Text(\n"
            "                        text = stringResource(R.string.battery_optimization_button),\n"
            "                        color = AugustColor.LimeInk,\n"
            "                        fontWeight = FontWeight.Black,\n"
            "                        fontSize = 13.sp\n"
            "                    )\n"
            "                }\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "}\n"
            "\n"
            "/** One row in the exclusive source selector. A selected switch cannot\n"
            " *  be turned off by itself, which guarantees there is never a zero-source\n"
            " *  state; enabling the other row atomically deselects this one. */\n"
            "@Composable\n"
            "private fun DataSourceToggleRow(\n"
        ),
        unique_marker="private fun BatteryOptimizationCard(palette: BitPalette, onOpenBatterySettings: () -> Unit)",
        description="FinalBitLutShell.kt: add BatteryOptimizationCard composable",
    )
    apply_edit(
        FINAL_SHELL_FILE,
        old=(
            "    onDataSourceSelected: (HealthDataSource) -> Unit,\n"
            "    stepsGoal: Long,\n"
            "    onStepsGoalChanged: (Long) -> Unit\n"
            ") {"
        ),
        new=(
            "    onDataSourceSelected: (HealthDataSource) -> Unit,\n"
            "    stepsGoal: Long,\n"
            "    onStepsGoalChanged: (Long) -> Unit,\n"
            "    showBatteryHint: Boolean,\n"
            "    onOpenBatterySettings: () -> Unit\n"
            ") {"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="FinalBitLutShell.kt: add showBatteryHint/onOpenBatterySettings params to SettingsScreen(...)",
    )
    apply_insertion(
        FINAL_SHELL_FILE,
        anchor=(
            "        val huaweiFailureReason = syncState.lastHuaweiAuthFailureReason\n"
            "        if (!syncState.isHuaweiAuthorized && huaweiFailureReason != null) {\n"
            "            HuaweiAuthIssueCard(palette = palette, reason = huaweiFailureReason, onRetryConnect = onRequestHuawei)\n"
            "        }\n"
        ),
        new_with_anchor=(
            "        val huaweiFailureReason = syncState.lastHuaweiAuthFailureReason\n"
            "        if (!syncState.isHuaweiAuthorized && huaweiFailureReason != null) {\n"
            "            HuaweiAuthIssueCard(palette = palette, reason = huaweiFailureReason, onRetryConnect = onRequestHuawei)\n"
            "        }\n"
            "\n"
            "        // Android 12+ battery-optimization advisory (2026-09): see\n"
            "        // BatteryOptimizationCard's doc comment. showBatteryHint is\n"
            "        // re-evaluated by the caller on every onResume, so this\n"
            "        // disappears immediately once the person grants the exemption.\n"
            "        if (showBatteryHint) {\n"
            "            BatteryOptimizationCard(palette = palette, onOpenBatterySettings = onOpenBatterySettings)\n"
            "        }\n"
        ),
        unique_marker="BatteryOptimizationCard(palette = palette, onOpenBatterySettings = onOpenBatterySettings)\n        }\n",
        description="FinalBitLutShell.kt: render BatteryOptimizationCard in SettingsScreen",
    )
    apply_edit(
        FINAL_SHELL_FILE,
        old=(
            "    hasSeenPermissionsOnboarding: Boolean = true,\n"
            "    onPermissionsOnboardingSeen: () -> Unit = {},\n"
            "    importViewModel: ImportViewModel) {"
        ),
        new=(
            "    hasSeenPermissionsOnboarding: Boolean = true,\n"
            "    onPermissionsOnboardingSeen: () -> Unit = {},\n"
            "    showBatteryHint: Boolean = false,\n"
            "    onOpenBatterySettings: () -> Unit = {},\n"
            "    importViewModel: ImportViewModel) {"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="FinalBitLutShell.kt: add showBatteryHint/onOpenBatterySettings params to top-level FinalBitLutShell(...)",
    )
    apply_edit(
        FINAL_SHELL_FILE,
        old=(
            "                    stepsGoal = dashboardState.stepsGoal,\n"
            "                    onStepsGoalChanged = onStepsGoalChanged)\n"
        ),
        new=(
            "                    stepsGoal = dashboardState.stepsGoal,\n"
            "                    onStepsGoalChanged = onStepsGoalChanged,\n"
            "                    showBatteryHint = showBatteryHint,\n"
            "                    onOpenBatterySettings = onOpenBatterySettings)\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="FinalBitLutShell.kt: pass showBatteryHint/onOpenBatterySettings through to SettingsScreen(...) call site",
    )
    apply_edit(
        FINAL_SHELL_FILE,
        old=OLD_BUTTONS_BLOCK,
        new=NEW_BUTTONS_BLOCK,
        expected_old_count=1,
        expected_new_count=1,
        description="FinalBitLutShell.kt: extract shared PillActionButton core from PrimaryButton/SecondaryButton",
    )

    print("=== 7/8: strings.xml (EN + RU) -- battery hint strings ===")
    apply_insertion(
        STRINGS_EN_FILE,
        anchor='    <string name="toast_hc_launch_failed">Couldn\\\'t open the Health Connect permissions screen. Please try again.</string>\n',
        new_with_anchor=(
            '    <string name="toast_hc_launch_failed">Couldn\\\'t open the Health Connect permissions screen. Please try again.</string>\n'
            '    <string name="toast_battery_settings_launch_failed">Couldn\\\'t open battery settings. Please try again.</string>\n'
        ),
        unique_marker="toast_battery_settings_launch_failed",
        description="strings.xml (EN): add toast_battery_settings_launch_failed",
    )
    apply_insertion(
        STRINGS_EN_FILE,
        anchor='    <string name="health_connect_data_sources_button">Open Health Connect settings</string>\n',
        new_with_anchor=(
            '    <string name="health_connect_data_sources_button">Open Health Connect settings</string>\n'
            '    <string name="battery_optimization_title">Keep background sync reliable</string>\n'
            '    <string name="battery_optimization_body">Your phone\\\'s battery settings may stop BitLut from syncing in the background unless it\\\'s allowed to ignore battery optimization. This is a one-time setting on your device, not in the app.</string>\n'
            '    <string name="battery_optimization_button">Open battery settings</string>\n'
        ),
        unique_marker="battery_optimization_title",
        description="strings.xml (EN): add battery_optimization_title/body/button",
    )
    apply_insertion(
        STRINGS_RU_FILE,
        anchor='    <string name="toast_hc_launch_failed">Не удалось открыть экран разрешений Health Connect. Попробуйте ещё раз.</string>\n',
        new_with_anchor=(
            '    <string name="toast_hc_launch_failed">Не удалось открыть экран разрешений Health Connect. Попробуйте ещё раз.</string>\n'
            '    <string name="toast_battery_settings_launch_failed">Не удалось открыть настройки батареи. Попробуйте ещё раз.</string>\n'
        ),
        unique_marker="toast_battery_settings_launch_failed",
        description="strings.xml (RU): add toast_battery_settings_launch_failed",
    )
    apply_insertion(
        STRINGS_RU_FILE,
        anchor='    <string name="health_connect_data_sources_button">Открыть настройки Health Connect</string>\n',
        new_with_anchor=(
            '    <string name="health_connect_data_sources_button">Открыть настройки Health Connect</string>\n'
            '    <string name="battery_optimization_title">Сделайте фоновую синхронизацию надёжнее</string>\n'
            '    <string name="battery_optimization_body">Настройки батареи вашего телефона могут мешать BitLut синхронизироваться в фоне, если приложению не разрешено игнорировать оптимизацию батареи. Это одноразовая настройка устройства, не самого приложения.</string>\n'
            '    <string name="battery_optimization_button">Открыть настройки батареи</string>\n'
        ),
        unique_marker="battery_optimization_title",
        description="strings.xml (RU): add battery_optimization_title/body/button",
    )

    validate_strings_xml_parity()

    print("=== 8/8: Running compile gate ===")
    run_compile_gate()

    print("=== Compile gate passed. Committing and pushing. ===")
    git_commit_and_push()

    print("Done.")


if __name__ == "__main__":
    main()
