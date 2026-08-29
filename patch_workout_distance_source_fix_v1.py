#!/usr/bin/env python3
"""
patch_workout_distance_source_fix_v1.py

Fixes a real, confirmed distance/average-speed bug: a 28 km, ~2 hour bike
ride was showing as 0.7 km on the BitLut dashboard (average speed wrong by
the same factor, since it is derived from distance / duration).

Root cause (confirmed from real diagnostic logs, 2026-08-28): workout
distance was never read from Huawei's own per-activity sample data at all.
Instead, GoogleHealthManager tried to reconstruct it after the fact from
Health Connect, two ways: (1) an aggregate() over the exact session time
window, and (2) a time-overlap-fraction split of nearby DistanceRecords
when (1) returned nothing. Both approaches assume Huawei's continuous
distance-delta stream reports samples whose own time window lines up with
the actual movement -- false for Huawei's coarse background delta samples,
which can report a real distance total over a window much wider than the
workout itself. When such a sample partially overlapped the session
window, the overlap-fraction math credited only a tiny sliver of the real
distance to that specific workout -- consistent with the exact ~40x
undercount reported.

Fix, in two parts:

1. HuaweiHealthManager.readActivitySessions() now requests per-activity
   distance detail directly from Huawei's ActivityRecordsController, via
   ActivityRecordReadOptions.Builder.read(DataType) (already used for
   steps-delta) and ActivityRecordReply.getSampleSet(record) (confirmed via
   Huawei's own hms-health-demo-java sample code) -- data scoped exactly to
   that one activity record, not a separate generic query needing manual
   time-window reconciliation. ActivitySessionData.distanceMeters is now
   populated with this real, correctly-scoped value.

2. GoogleHealthManager.enrichDisplayedWorkoutMetrics() previously let the
   Health Connect aggregate win over this session-level value whenever the
   aggregate returned any non-null number, even a wrong tiny one. Priority
   is now: real per-session Huawei data first, then the Health Connect
   aggregate, then the raw-overlap fallback -- both fallbacks preserved for
   workouts Huawei didn't report per-activity distance for.

One piece of part 1 is inferred rather than directly confirmed from a
Huawei-specific multi-type example: whether calling
ActivityRecordReadOptions.Builder.read(DataType) a second time (for
distance, alongside the pre-existing steps-delta call) accumulates both
types rather than replacing the first. Google Fit's near-identical
SessionReadRequest.Builder.read(DataType) is documented as callable
multiple times to accumulate types, and this codebase's own existing
comment already treats Huawei's .read(...) as an additive detail-type
request on the same builder, so the pattern is used here on that basis --
but this is exactly the kind of real Kotlin/HMS-SDK behavior a sandbox
cannot verify. Paulo's real assembleDebug is the actual compile gate.
getSampleSet itself is called via reflection (not a typed import) since
ActivityRecordReply's exact import path was not independently confirmed
with the same certainty as SamplePoint/SampleSet/DataType/Field, which are
already imported directly elsewhere in this file.

Not touched, and explicitly out of scope: the corporate wellness app's own
refusal to import BitLut-sourced Health Connect workouts. That investigation
concluded it is very likely a source-identity/allowlist policy on the
corporate app's own side (same pattern as Fitbit excluding third-party step
sources from challenges), which BitLut's write path cannot influence. This
patch only fixes BitLut's own dashboard distance/speed display, which was a
real, independent, confirmed bug regardless of that separate issue.

Usage:
    python3 patch_workout_distance_source_fix_v1.py

Behavior:
    1. Backs up every touched file to .bitlut_patch_backup/
    2. Applies text-anchored edits to HuaweiHealthManager.kt and
       GoogleHealthManager.kt
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
HUAWEI_HEALTH_KT = REPO_ROOT / "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt"
GOOGLE_HEALTH_KT = REPO_ROOT / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt"
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
    only). Returns True if applied, False if already applied (idempotent
    skip). Dies on any other state. Does not cross-check new_str's
    occurrence count, since some edits in this project have old_str as a
    substring of new_str, which makes a new_str-based pre-patch check
    unreliable.
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
    Pure-insertion helper: use when anchor survives unchanged as a
    substring of new_with_anchor. Idempotency is keyed on unique_marker (a
    substring that exists ONLY inside the newly added text), not on
    anchor's own occurrence count, since anchor stays present after the
    insertion and a count-based check on it alone would reapply forever.
    """
    text = path.read_text(encoding="utf-8")
    if text.count(unique_marker) >= 1:
        return False

    anchor_count = text.count(anchor)
    if anchor_count == 1:
        text = text.replace(anchor, new_with_anchor, 1)
        path.write_text(text, encoding="utf-8")
        return True

    die(
        "Unexpected file state for insertion.\n"
        f"  unique_marker occurrences: {text.count(unique_marker)} (expected 0 pre-patch)\n"
        f"  anchor occurrences: {anchor_count} (expected exactly 1 pre-patch)\n"
        f"  file: {path}\n"
        "Refusing to guess; inspect the file manually."
    )


def run(cmd: list, cwd: Path) -> None:
    print(f"$ {chr(32).join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        die(f"Command failed ({result.returncode}): {chr(32).join(cmd)}")


IMPORT_OLD = "import com.huawei.hms.hihealth.data.SamplePoint\nimport com.huawei.hms.hihealth.data.Scopes"
IMPORT_NEW = "import com.huawei.hms.hihealth.data.SamplePoint\nimport com.huawei.hms.hihealth.data.SampleSet\nimport com.huawei.hms.hihealth.data.Scopes"

HUAWEI_FUNC_OLD = '    private suspend fun readActivitySessions(startTimeMs: Long, endTimeMs: Long): List<ActivitySessionData> {\n        // Exercise records are not continuous intensity samples. Huawei\'s\n        // supported API for workouts is ActivityRecordsController, covered by\n        // the already-requested HEALTHKIT_ACTIVITY_RECORD_READ scope.\n        val options = ActivityRecordReadOptions.Builder()\n            .setTimeInterval(startTimeMs, endTimeMs, TimeUnit.MILLISECONDS)\n            .readActivityRecordsFromAllApps()\n            // Carrying an approved detail type is required on some Huawei\n            // Health builds for the record list to be returned at all.\n            .read(DataType.DT_CONTINUOUS_STEPS_DELTA)\n            .build()\n\n        AppLogger.i(\n            TAG,\n            "Querying Huawei activity records with steps-delta detail: start=$startTimeMs end=$endTimeMs"\n        )\n\n        val reply = retryOnConnectionRace {\n            HuaweiHiHealth.getActivityRecordsController(context)\n                .getActivityRecord(options)\n                .awaitTask()\n        }\n        val records = reply.getActivityRecords().orEmpty()\n\n        AppLogger.i(TAG, "Huawei activity records read: ${records.size}")\n\n        return records.mapNotNull { record ->\n            val start = activityRecordTime(record, "getStartTime") ?: return@mapNotNull null\n            val end = activityRecordTime(record, "getEndTime") ?: return@mapNotNull null\n            if (start <= 0L || end <= start) return@mapNotNull null\n\n            val recordId = activityRecordString(record, "getId")\n            val rawType = activityRecordString(record, "getActivityTypeId", "getActivityType")\n            val rawName = activityRecordString(record, "getName")\n            val canonicalType = canonicalHuaweiActivityName(rawType)\n            val title = rawName\n                ?.trim()\n                ?.takeIf { it.isNotBlank() && !isSyntheticHuaweiActivityName(it, recordId) }\n                ?: canonicalType\n\n            val exerciseType = mapHuaweiExerciseType(canonicalType)\n            AppLogger.i(\n                TAG,\n                "Huawei activity mapped: type=${rawType ?: "unknown"} name=${rawName ?: "-"} canonical=$canonicalType start=$start end=$end"\n            )\n\n            ActivitySessionData(\n                startTimeMs = start,\n                endTimeMs = end,\n                title = title,\n                exerciseType = exerciseType\n            )\n        }.distinctBy { Pair(it.startTimeMs, it.endTimeMs) }\n    }'
HUAWEI_FUNC_NEW = '    /**\n     * Sprint 2026-08-28: previously, ActivitySessionData.distanceMeters was\n     * never set here at all -- every workout card\'s distance came entirely\n     * from GoogleHealthManager\'s post-hoc Health Connect matching (a strict\n     * aggregate() over the exact session window, falling back to a\n     * time-overlap-fraction split of nearby DistanceRecords). Both of those\n     * approaches implicitly assume Huawei\'s own DT_CONTINUOUS_DISTANCE_DELTA\n     * stream reports distance in samples whose own time window lines up with\n     * the actual movement, which is false for Huawei\'s coarse background\n     * delta samples: a real 28 km, ~2 hour bike ride was measured by a user\n     * report showing the dashboard displaying only 0.7 km for that same\n     * ride, a ~40x undercount consistent with a wide background sample\n     * (its own reported window several times longer than the actual ride)\n     * being credited only for the sliver of its window that happened to\n     * geometrically overlap the session\'s exact start/end -- an artifact of\n     * the overlap-fraction math, not of the underlying distance value itself\n     * (which was correct in total, just attributed to the wrong time span).\n     *\n     * Huawei\'s own ActivityRecordsController API supports exactly the right\n     * fix for this: `ActivityRecordReadOptions.Builder.read(DataType)` can\n     * request additional detail data types to be returned scoped to each\n     * individual ActivityRecord (this file already does this for\n     * DT_CONTINUOUS_STEPS_DELTA below, per the pre-existing comment on why a\n     * detail type is required for the record list to be returned at all),\n     * and `ActivityRecordReply.getSampleSet(record)` returns exactly the\n     * detail samples belonging to that one record -- not a separate\n     * generic query needing manual time-window reconciliation. Real,\n     * independently-confirmed Huawei sample code\n     * (HealthKitActivityRecordControllerActivity.java, part of Huawei\'s own\n     * hms-health-demo-java repository) shows this exact\n     * getSampleSet(activityRecord) -> sampleSet.getSamplePoints() pattern\n     * for reading per-record detail data.\n     *\n     * One piece of this is inferred rather than directly confirmed from a\n     * Huawei-specific multi-type example: whether calling `.read(DataType)`\n     * a second time (for distance, alongside the existing steps-delta call)\n     * accumulates both requested types rather than replacing the first.\n     * Google Fit\'s near-identical SessionReadRequest.Builder.read(DataType)\n     * is documented as callable multiple times to accumulate types, and\n     * this file\'s own existing comment already treats Huawei\'s `.read(...)`\n     * as an additive detail-type request, so the pattern is used here on\n     * that basis -- but this is exactly the kind of real Kotlin/HMS-SDK API\n     * behavior the project\'s own rules say a sandbox cannot verify.\n     * Paulo\'s real `assembleDebug` is the actual compile gate for this.\n     *\n     * Distance is summed per-record from real Huawei sample data scoped to\n     * that exact activity, not prorated or estimated. A record with no\n     * matching distance samples correctly yields null (displayed as "-"),\n     * per the locked six-slot contract\'s "real data only" rule.\n     */\n    private suspend fun readActivitySessions(startTimeMs: Long, endTimeMs: Long): List<ActivitySessionData> {\n        // Exercise records are not continuous intensity samples. Huawei\'s\n        // supported API for workouts is ActivityRecordsController, covered by\n        // the already-requested HEALTHKIT_ACTIVITY_RECORD_READ scope.\n        val distanceDetailType = firstDataType(\n            "DT_CONTINUOUS_DISTANCE_DELTA",\n            "DT_CONTINUOUS_DISTANCE_TOTAL",\n            "DT_INSTANTANEOUS_DISTANCE"\n        )\n        val distanceDetailFields = fields(\n            "FIELD_DISTANCE",\n            "FIELD_DISTANCE_DELTA",\n            "FIELD_DISTANCE_TOTAL"\n        )\n\n        val optionsBuilder = ActivityRecordReadOptions.Builder()\n            .setTimeInterval(startTimeMs, endTimeMs, TimeUnit.MILLISECONDS)\n            .readActivityRecordsFromAllApps()\n            // Carrying an approved detail type is required on some Huawei\n            // Health builds for the record list to be returned at all.\n            .read(DataType.DT_CONTINUOUS_STEPS_DELTA)\n\n        if (distanceDetailType != null) {\n            optionsBuilder.read(distanceDetailType)\n        } else {\n            AppLogger.w(TAG, "Skipping per-activity distance detail: Huawei SDK does not expose a supported distance DataType")\n        }\n\n        val options = optionsBuilder.build()\n\n        AppLogger.i(\n            TAG,\n            "Querying Huawei activity records with steps-delta detail: start=$startTimeMs end=$endTimeMs"\n        )\n\n        val reply = retryOnConnectionRace {\n            HuaweiHiHealth.getActivityRecordsController(context)\n                .getActivityRecord(options)\n                .awaitTask()\n        }\n        val records = reply.getActivityRecords().orEmpty()\n\n        AppLogger.i(TAG, "Huawei activity records read: ${records.size}")\n\n        return records.mapNotNull { record ->\n            val start = activityRecordTime(record, "getStartTime") ?: return@mapNotNull null\n            val end = activityRecordTime(record, "getEndTime") ?: return@mapNotNull null\n            if (start <= 0L || end <= start) return@mapNotNull null\n\n            val recordId = activityRecordString(record, "getId")\n            val rawType = activityRecordString(record, "getActivityTypeId", "getActivityType")\n            val rawName = activityRecordString(record, "getName")\n            val canonicalType = canonicalHuaweiActivityName(rawType)\n            val title = rawName\n                ?.trim()\n                ?.takeIf { it.isNotBlank() && !isSyntheticHuaweiActivityName(it, recordId) }\n                ?: canonicalType\n\n            val exerciseType = mapHuaweiExerciseType(canonicalType)\n            val recordDistanceMeters = readActivityRecordDistance(reply, record, distanceDetailFields)\n            AppLogger.i(\n                TAG,\n                "Huawei activity mapped: type=${rawType ?: "unknown"} name=${rawName ?: "-"} canonical=$canonicalType " +\n                    "start=$start end=$end distanceMeters=${recordDistanceMeters ?: "missing"}"\n            )\n\n            ActivitySessionData(\n                startTimeMs = start,\n                endTimeMs = end,\n                title = title,\n                exerciseType = exerciseType,\n                distanceMeters = recordDistanceMeters\n            )\n        }.distinctBy { Pair(it.startTimeMs, it.endTimeMs) }\n    }\n\n    /**\n     * Sums real Huawei sample-point distance values scoped specifically to\n     * [record], via ActivityRecordReply.getSampleSet(record) ->\n     * SampleSet.samplePoints. Reuses the existing, already-working\n     * SamplePoint.firstNumericValue(fields) extension (defined below,\n     * proven in readMetric\'s own generic-stream distance reading) rather\n     * than inventing new reflection for value extraction.\n     *\n     * getSampleSet itself is called via reflection rather than a typed\n     * call: this file already imports SamplePoint, SampleSet, DataType,\n     * and Field directly from com.huawei.hms.hihealth.data (confirmed\n     * real, stable import paths, used elsewhere in this file), but\n     * ActivityRecordReply\'s own import path was not independently\n     * confirmed with the same certainty during this fix, so [reply] stays\n     * untyped (Any) here rather than risk a wrong import breaking the\n     * whole file. This mirrors activityRecordTime/activityRecordString\'s\n     * existing reflection style for the same class of uncertainty.\n     */\n    private fun readActivityRecordDistance(\n        reply: Any,\n        record: Any,\n        distanceFields: List<Field>\n    ): Double? {\n        if (distanceFields.isEmpty()) return null\n\n        val sampleSets = try {\n            @Suppress("UNCHECKED_CAST")\n            reply.javaClass.methods\n                .firstOrNull { it.name == "getSampleSet" && it.parameterCount == 1 }\n                ?.invoke(reply, record) as? List<SampleSet>\n        } catch (e: Exception) {\n            AppLogger.w(TAG, "getSampleSet failed for activity record: ${e.message}")\n            null\n        } ?: return null\n\n        var totalMeters = 0.0\n        var matchedAny = false\n\n        sampleSets.forEach { sampleSet ->\n            sampleSet.samplePoints.forEach { point ->\n                val value = point.firstNumericValue(distanceFields)\n                if (value != null && value > 0.0) {\n                    totalMeters += value\n                    matchedAny = true\n                }\n            }\n        }\n\n        return totalMeters.takeIf { matchedAny && it > 0.0 }\n    }'

GOOGLE_EDIT_OLD = '            val recoveredDistanceMeters = if (\n                aggregateDistanceMeters == null && workout.distanceMeters == null\n            ) {\n                recoverWorkoutDistanceFromRawRecords(client, workout)\n            } else {\n                null\n            }\n            val distanceMeters = aggregateDistanceMeters ?: recoveredDistanceMeters ?: workout.distanceMeters\n\n            AppLogger.i(\n                TAG,\n                "Workout metrics resolved: type=${workout.exerciseType} " +\n                    "start=${workout.startTimeMs} end=${workout.endTimeMs} " +\n                    "distanceMeters=${distanceMeters ?: 0.0} " +\n                    "distanceSource=${when {\n                        aggregateDistanceMeters != null -> "aggregate"\n                        recoveredDistanceMeters != null -> "raw_overlap"\n                        workout.distanceMeters != null -> "session"\n                        else -> "missing"\n                    }} " +'
GOOGLE_EDIT_NEW = '            val recoveredDistanceMeters = if (\n                aggregateDistanceMeters == null && workout.distanceMeters == null\n            ) {\n                recoverWorkoutDistanceFromRawRecords(client, workout)\n            } else {\n                null\n            }\n            // Sprint 2026-08-28: workout.distanceMeters (now populated by\n            // HuaweiHealthManager directly from Huawei\'s own per-activity\n            // sample data, scoped exactly to this session -- see the doc\n            // comment on readActivitySessions there) is trusted FIRST, ahead\n            // of the Health Connect aggregate. Previously the aggregate won\n            // whenever it returned any non-null value, even a wrong one: a\n            // real 28 km bike ride showed as 0.7 km on the dashboard because\n            // a coarse, wide-window DistanceRecord partially overlapped the\n            // session and the aggregate briefly returned a small non-null\n            // total for that narrow overlap, before session-level data was\n            // ever provided as a competing, more trustworthy source. The\n            // aggregate and raw-overlap paths remain as fallbacks for\n            // sessions Huawei didn\'t report per-activity distance for (e.g.\n            // recorded by a different app, or an older/incomplete Huawei\n            // record), where they\'re still better than nothing.\n            val distanceMeters = workout.distanceMeters ?: aggregateDistanceMeters ?: recoveredDistanceMeters\n\n            AppLogger.i(\n                TAG,\n                "Workout metrics resolved: type=${workout.exerciseType} " +\n                    "start=${workout.startTimeMs} end=${workout.endTimeMs} " +\n                    "distanceMeters=${distanceMeters ?: 0.0} " +\n                    "distanceSource=${when {\n                        workout.distanceMeters != null -> "session"\n                        aggregateDistanceMeters != null -> "aggregate"\n                        recoveredDistanceMeters != null -> "raw_overlap"\n                        else -> "missing"\n                    }} " +'


def main() -> None:
    changed = False

    if not HUAWEI_HEALTH_KT.exists():
        die(f"Target file not found: {HUAWEI_HEALTH_KT}")
    backup_file(HUAWEI_HEALTH_KT)

    applied = apply_insertion(HUAWEI_HEALTH_KT, IMPORT_OLD, IMPORT_NEW, "import com.huawei.hms.hihealth.data.SampleSet")
    print(f"  [HuaweiHealthManager.kt] add SampleSet import: {'applied' if applied else 'already applied, skipped'}")
    changed = changed or applied

    applied = apply_edit(HUAWEI_HEALTH_KT, HUAWEI_FUNC_OLD, HUAWEI_FUNC_NEW)
    print(f"  [HuaweiHealthManager.kt] read per-activity distance from Huawei sample data: {'applied' if applied else 'already applied, skipped'}")
    changed = changed or applied

    if not GOOGLE_HEALTH_KT.exists():
        die(f"Target file not found: {GOOGLE_HEALTH_KT}")
    backup_file(GOOGLE_HEALTH_KT)

    applied = apply_edit(GOOGLE_HEALTH_KT, GOOGLE_EDIT_OLD, GOOGLE_EDIT_NEW)
    print(f"  [GoogleHealthManager.kt] prioritize session-level distance over aggregate: {'applied' if applied else 'already applied, skipped'}")
    changed = changed or applied

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
            "Fix workout distance/avg speed: read per-activity distance from "
            "Huawei sample data, prioritize it over the Health Connect aggregate",
        ],
        cwd=REPO_ROOT,
    )
    run(["git", "push", "origin", "HEAD:main"], cwd=REPO_ROOT)
    print("Done.")


if __name__ == "__main__":
    main()
