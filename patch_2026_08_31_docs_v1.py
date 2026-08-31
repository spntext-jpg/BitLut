#!/usr/bin/env python3
"""
patch_2026_08_31_docs_v1.py

Documentation-only patch. Updates CHANGELOG.md, SESSION_HANDOFF.md, and
CONTEXT.md to reflect the three code patches delivered this session:

1. patch_navbar_rebuild_sync_status_steps_diag_v1.py -- navbar rebuild
   (shared height, width-based hierarchy), "Syncing..." alpha-only
   fixed-height fix, steps-undercount diagnostic logging.
2. patch_workout_session_scoped_metrics_v1.py -- session-scoped
   Distance/Steps/Elevation/ActiveCalories Health Connect records for
   every workout, gated by exercise type.
3. patch_sync_activity_signal_and_midnight_cache_v1.py -- SYNC_ACTIVITY_TAG
   background-sync-activity signal for the "Syncing..." indicator;
   refreshFromCache() midnight-staleness guard.

Per this project's standing process, session-end documentation updates to
CHANGELOG.md, SESSION_HANDOFF.md, and CONTEXT.md happen together in one
patch batch so a fresh session's read of these three files is internally
consistent. This script makes no code changes -- it only edits the three
.md files.

Mandatory workflow already completed before this script was written:
hand-edited mirror -> real diff -> this script generated from that diff
-> tested on a clean extraction -> byte-diffed against the mirror ->
re-run for idempotency. No compile gate applies (no Kotlin touched), but
the same commit/push discipline is used.
"""
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"

CHANGELOG_FILE = REPO_ROOT / "CHANGELOG.md"
HANDOFF_FILE = REPO_ROOT / "SESSION_HANDOFF.md"
CONTEXT_FILE = REPO_ROOT / "CONTEXT.md"


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


def main() -> None:
    for f in (CHANGELOG_FILE, HANDOFF_FILE, CONTEXT_FILE):
        if not f.exists():
            die(f"Expected file not found: {f}")

    print("== 1/3: CHANGELOG.md ==")
    apply_edit(
        CHANGELOG_FILE,
        old="# Changelog\n\n## 2026-08-30 -- repo cleanup, handoff consolidation",
        new=(
            "# Changelog\n"
            "\n"
            "## 2026-08-31 -- navbar rebuild, workout Health Connect sub-records, "
            "Syncing indicator + midnight-cache fixes\n"
            "\n"
            "- **Navbar rebuild.** The 2026-08-29 (b) resize had shrunk "
            "`AugustDestination`'s\n"
            "  fixed *height* (58->46dp) to make Today/Settings read as secondary next to\n"
            "  Refresh, but a `Row.weight(1f)` child's height has nothing to do with\n"
            "  relative prominence -- only width does -- and 46dp was too short for a\n"
            "  24dp icon + spacer + 10sp label to lay out without clipping (confirmed\n"
            "  real-device report: labels invisible). Fix: every navbar control now\n"
            "  shares one common height (64dp); Refresh reads as primary via width\n"
            "  (84dp pill) instead of height. Both destination buttons remain identical\n"
            "  to each other.\n"
            "- **\"Syncing...\" layout jump fixed.** `AnimatedVisibility(fadeIn/fadeOut)`\n"
            "  collapsed the status line's layout height to zero the instant it became\n"
            "  invisible, yanking the subtitle text upward when a sync finished. Fixed\n"
            "  by keeping the line's `Column` always present at a fixed reserved height\n"
            "  and animating only `alpha` via `graphicsLayer`.\n"
            "- **Walking-steps undercount: diagnostics only, not yet fixed.** The\n"
            "  2026-08-29 (c) sum-across-points fix is confirmed correct for what it\n"
            "  does, but a real-device log still shows some walking activities summing\n"
            "  to zero/low steps from Huawei's own `ActivitySummary.dataSummary` (see\n"
            "  \"Steps: still under investigation\" below for the follow-up evidence).\n"
            "  Added per-point diagnostic logging (type name + every field name/value,\n"
            "  matched or not) plus a final match-count summary log, so the real cause\n"
            "  can be found from evidence instead of a third blind guess. Zero\n"
            "  behavior change.\n"
            "- **Workout session-scoped Health Connect records (real interoperability\n"
            "  fix).** `session.distanceMeters`/`steps`/`elevationMeters` were computed\n"
            "  correctly by `HuaweiHealthManager` but only ever used for BitLut's own\n"
            "  dashboard display -- never written to Health Connect as records scoped\n"
            "  to the workout's own time window. Per Health Connect's documented\n"
            "  pattern (a session's own metrics are read back by querying\n"
            "  Distance/Steps/Elevation records over the *same time range* as the\n"
            "  exercise session -- there is no explicit link), any third-party reader\n"
            "  had nothing trustworthy to find for a workout's own distance/steps/\n"
            "  elevation: only the separate, coarser background daily aggregate\n"
            "  existed in that window, and its sample windows are already documented\n"
            "  below as not lining up cleanly with an exact workout interval. Fixed:\n"
            "  `writeActivitySessionsBatch()` now bundles `DistanceRecord`,\n"
            "  `StepsRecord`, `ElevationGainedRecord` (plus a forward-compatible\n"
            "  `ActiveCaloriesBurnedRecord`, currently always null in practice) into\n"
            "  the same `insertRecords` call as the exercise session, scoped to its\n"
            "  exact interval -- but only for exercise types that can plausibly\n"
            "  produce each metric (new `sessionSubMetricsFor()`, mirroring\n"
            "  `workoutMetricDisplays()`'s existing per-type contract exactly, so\n"
            "  strength/weightlifting/HIIT/yoga/pilates never get a fabricated\n"
            "  distance or step count). Applies to every workout regardless of source\n"
            "  (live sync and archive import share this one write path). No new\n"
            "  Health Connect permissions required.\n"
            "- **\"Syncing...\" indicator never appeared (real device log, not a\n"
            "  guess).** Root cause: `SyncUiState.isSyncing` was wired only to\n"
            "  `SyncViewModel.markSyncStarted()`/`markSyncCompleted()`, called only\n"
            "  from `MainActivity`'s two UI-triggered sync paths (manual refresh,\n"
            "  auto-sync-on-launch). `SyncWorker` -- whether running as the periodic\n"
            "  30-minute job or a one-time manual job -- is a plain `CoroutineWorker`\n"
            "  with no path to that flag. The supplied log showed the periodic\n"
            "  background worker winning the sync-run lease race and doing the real\n"
            "  ~10-second sync, while the UI-triggered attempt lost the race and its\n"
            "  own started->completed pair collapsed to under a second -- too fast to\n"
            "  ever render. Fixed with a new `HuaweiConfig.SYNC_ACTIVITY_TAG`, applied\n"
            "  only to `SyncWorker`'s two enqueue sites (not the unrelated\n"
            "  `EveningReminderWorker`, which shares the older generic\n"
            "  `SYNC_WORKER_TAG`). `MainActivity` now observes\n"
            "  `WorkManager.getWorkInfosByTagLiveData(SYNC_ACTIVITY_TAG)` and feeds\n"
            "  \"any tagged work RUNNING/ENQUEUED/BLOCKED\" into a new\n"
            "  `SyncViewModel.setBackgroundSyncActive()`. `SyncUiState.isSyncing` is\n"
            "  now a computed property: `isUiTriggeredSyncing || isBackgroundSyncActive`.\n"
            "- **Yesterday's steps flashed before clearing at midnight (real device\n"
            "  log).** `DashboardViewModel.buildInitialState()` already zeroed daily\n"
            "  totals when the on-disk cache predates today (2026-08-26 fix), but\n"
            "  `refreshFromCache()` -- called both on a sync's own completion and on\n"
            "  `SyncOrchestrator`'s lease-collision retry timer (8s/12s after the\n"
            "  *deferred* sync's own result, independent of when the *winning* sync's\n"
            "  cache write actually lands) -- applied the cached snapshot\n"
            "  unconditionally. The retry can read the on-disk cache in the narrow\n"
            "  window before the winning sync's fresh write for the new day lands,\n"
            "  re-applying yesterday's still-cached real numbers over the\n"
            "  correctly-zeroed initial state. Fixed by extracting the zeroing logic\n"
            "  into a shared `zeroedDailyTotals()` helper and applying the identical\n"
            "  cache-predates-today check in `refreshFromCache()`.\n"
            "- Delivered as `patch_navbar_rebuild_sync_status_steps_diag_v1.py`,\n"
            "  `patch_workout_session_scoped_metrics_v1.py`, and\n"
            "  `patch_sync_activity_signal_and_midnight_cache_v1.py`; all removed\n"
            "  after verification per standing process.\n"
            "\n"
            "## 2026-08-30 -- repo cleanup, handoff consolidation"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="add 2026-08-31 CHANGELOG entry",
    )

    print("== 2/3: SESSION_HANDOFF.md ==")

    apply_edit(
        HANDOFF_FILE,
        old="Current handoff date: 2026-08-30.",
        new="Current handoff date: 2026-08-31.",
        expected_old_count=1,
        expected_new_count=1,
        description="bump handoff date",
    )

    apply_edit(
        HANDOFF_FILE,
        old=(
            "- `readActivityRecordSummary()` sums steps/calories/elevation across ALL matching Huawei sample points for an activity, not just the first. Do not revert to `firstOrNull()` for these fields -- Huawei can and does split them across multiple points per activity (confirmed on-device: a real walk showed 2.5 km distance but only 250 steps before this fix, because distance already summed via its fallback path while steps took only the first point).\n"
            "- BitLut writes workout sessions as `ACTIVELY_RECORDED`"
        ),
        new=(
            "- `readActivityRecordSummary()` sums steps/calories/elevation across ALL matching Huawei sample points for an activity, not just the first. Do not revert to `firstOrNull()` for these fields -- Huawei can and does split them across multiple points per activity (confirmed on-device: a real walk showed 2.5 km distance but only 250 steps before this fix, because distance already summed via its fallback path while steps took only the first point).\n"
            "  - **2026-08-31 update: steps are still sometimes wrong after the sum fix** (real-device log showed a walking activity with `stepsTotalPointsMatched=0` -- Huawei's own `dataSummary` apparently emitted zero matching `steps.total` points for that activity, a different failure mode than the one the sum fix addressed). A raw-stream fallback (mirroring the distance fix's `getSampleSet(record)` approach) was considered and rejected: this file's own prior lesson already found raw `DT_CONTINUOUS_STEPS_DELTA` samples unreliable/absent for Huawei step totals during a daily read (see `readDailyStepTotals()`), so blindly reusing that approach for the per-activity case would repeat a category of fix already flagged unsafe, without real per-point evidence for this specific failure. Per-point diagnostic logging was added instead (type name + every field/value, matched or not, plus a final match-count summary) -- **do not attempt a structural fix here without a fresh real-device log showing what `dataSummary` actually contains for a failing activity.**\n"
            "- **2026-08-31: workout metrics are now also written to Health Connect as session-scoped records, not just used for dashboard display.** `writeActivitySessionsBatch()` bundles `DistanceRecord`/`StepsRecord`/`ElevationGainedRecord` (plus a currently-always-null `ActiveCaloriesBurnedRecord`) into the same `insertRecords` call as the exercise session and its calorie total, scoped to the exact session interval -- gated by `sessionSubMetricsFor()`, which mirrors `workoutMetricDisplays()`'s per-type contract exactly (walk/run/treadmill get distance+steps; hiking adds elevation; biking gets distance+elevation, no steps; stationary biking gets distance only; swimming gets distance only; strength/weightlifting/HIIT/yoga/pilates get none of the three). This closes a real interoperability gap: previously, any third-party Health Connect reader querying a workout's own distance/steps/elevation (Health Connect has no explicit session<->metric link; readers query by time-range overlap) found only the separate, coarser background daily aggregate, not anything scoped to the workout itself. **Write ordering in `writeSnapshot()` is load-bearing**: `writeStepsBatch` (which can delete-then-reinsert a whole day's `StepsRecord`s during \"complete daily summation\" reconciliation) must keep running before `writeActivitySessionsBatch`, or that reconciliation will silently wipe the new workout-scoped `StepsRecord`s. This is currently true only because these are sequential suspend calls in one list literal; if that list is ever parallelized, this ordering must be preserved explicitly.\n"
            "- BitLut writes workout sessions as `ACTIVELY_RECORDED`"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="add steps-diagnostic and session-scoped-records notes",
    )

    apply_edit(
        HANDOFF_FILE,
        old=(
            "Never show `0` as a substitute for a missing workout metric; omit the slot or show the established no-data UI where applicable.\n"
            "\n"
            "### Corporate wellness app investigation"
        ),
        new=(
            "Never show `0` as a substitute for a missing workout metric; omit the slot or show the established no-data UI where applicable.\n"
            "\n"
            "**2026-08-31 note:** if a walking/running activity's Steps slot is missing despite the workout clearly having steps, this is very likely the still-open Huawei `dataSummary` steps issue noted above under \"Workout import and Health Connect\" -- not a display-layer bug. Check the diagnostic log line `Huawei activity summary steps diagnostic` for that activity's `stepsTotalPointsMatched` before assuming the display logic is at fault.\n"
            "\n"
            "### Corporate wellness app investigation"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="add steps-missing dashboard note",
    )

    apply_edit(
        HANDOFF_FILE,
        old=(
            "Next useful test is on the corporate app side: confirm whether it accepts third-party Health Connect writer origins. Do not keep changing BitLut metadata blindly without new evidence.\n"
            "\n"
            "## UI decisions"
        ),
        new=(
            "Next useful test is on the corporate app side: confirm whether it accepts third-party Health Connect writer origins. Do not keep changing BitLut metadata blindly without new evidence.\n"
            "\n"
            "### Dashboard cache and midnight rollover\n"
            "\n"
            "- `DashboardViewModel.buildInitialState()` zeroes daily-total fields (steps/distance/calories/workout minutes/active hours/elevation/floors) when the on-disk `DashboardSnapshotCache` predates today -- a new calendar day has genuinely started with zero activity so far, and showing yesterday's numbers as today's is misleading. `recentWorkouts` is untouched by this: a workout from yesterday is still real history.\n"
            "- **2026-08-31: `refreshFromCache()` now applies the identical check** (extracted into a shared `zeroedDailyTotals()` helper). It previously applied the cached snapshot unconditionally, which was safe when called right after a sync's own completion (the cache is fresh by then) but not when called from `SyncOrchestrator`'s lease-collision retry timer (8s/12s after the *deferred* sync's own \"already running\" result -- independent of when the *winning* sync's cache write actually lands). A real device log showed the exact race: right after midnight, that retry could read the still-stale, pre-sync on-disk cache and re-apply yesterday's real numbers over the already-correctly-zeroed dashboard, for the few seconds until a later refresh corrected it again. Do not reintroduce an unconditional cache apply on any new cache-consuming code path -- always go through (or replicate) `zeroedDailyTotals()`'s guard.\n"
            "\n"
            "## UI decisions"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="add dashboard cache/midnight rollover subsection",
    )

    apply_edit(
        HANDOFF_FILE,
        old=(
            "- Bottom navbar: Today/Settings destination buttons are ~20% smaller than the center Refresh button (button height 46dp vs Refresh 72dp; destination icon 17/16dp vs Refresh icon 34dp). Both destination buttons remain identical to each other; do not resize one without the other.\n"
            "- Today header shows an animated \"Syncing...\" / \"Синхронизация...\" status line under the last-sync trailing text while `SyncUiState.isSyncing` is true (fades in/out via `AnimatedVisibility`, not a snap toggle). Driven entirely by existing `SyncViewModel.markSyncStarted()`/`markSyncCompleted()` state.\n"
            "- Settings screen ends with a small wood-carved-style signature"
        ),
        new=(
            "- Bottom navbar: all controls (Today, Refresh, Settings) share one common height (64dp, was 46/72dp mismatched). Refresh reads as the primary action via width (84dp pill) instead of height -- the 2026-08-29 (b) height-based resize clipped the Today/Settings labels (confirmed real-device report) because a `Row.weight(1f)` child's height doesn't control its relative visual prominence, only width does. Both destination buttons remain identical to each other; do not resize one without the other. Do not resize navbar controls by height again for visual hierarchy -- use width.\n"
            "- Today header shows an animated \"Syncing...\" / \"Синхронизация...\" status line under the last-sync trailing text while `SyncUiState.isSyncing` is true. The line's container is always present at a fixed reserved height; only its alpha animates (`graphicsLayer`), never `AnimatedVisibility`'s presence/layout toggle -- the latter collapsed the line's height to zero on exit and yanked the subtitle text upward (confirmed real-device report). `isSyncing` itself is now a computed property (`isUiTriggeredSyncing || isBackgroundSyncActive`), not a single stored flag -- see \"Sync activity signal\" below for why.\n"
            "- **2026-08-31: \"Syncing...\" indicator visibility now also depends on real background sync activity, not just UI-triggered sync state.** `SyncViewModel.markSyncStarted()`/`markSyncCompleted()` alone were insufficient: they only fire from `MainActivity`'s two UI-triggered sync call sites, so a periodic background `SyncWorker` run that wins the sync-run lease race (confirmed on a real device log: the UI-triggered attempt's own started->completed pair collapsed to under a second while the periodic worker did the real ~10-second sync) never showed the indicator at all. `HuaweiConfig.SYNC_ACTIVITY_TAG` is now applied only to `SyncWorker`'s two enqueue sites (not `EveningReminderWorker`, which shares the older, broader `SYNC_WORKER_TAG` and is unrelated to health-data syncing) and observed via `WorkManager.getWorkInfosByTagLiveData()` in `MainActivity`, feeding `SyncViewModel.setBackgroundSyncActive()`.\n"
            "- Settings screen ends with a small wood-carved-style signature"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="update navbar/sync-status UI decisions, add sync-activity-signal note",
    )

    apply_insertion(
        HANDOFF_FILE,
        anchor="6. `patch_huawei_workout_summary_sum_v1.py` / `patch_settings_engraved_signature_v1.py` / `patch_sync_status_wording_and_docs_v1.py`: Huawei summary-metric sum fix, Settings signature, sync-status wording tightening (full detail in `CHANGELOG.md` 2026-08-29 (c)).\n",
        new_with_anchor=(
            "6. `patch_huawei_workout_summary_sum_v1.py` / `patch_settings_engraved_signature_v1.py` / `patch_sync_status_wording_and_docs_v1.py`: Huawei summary-metric sum fix, Settings signature, sync-status wording tightening (full detail in `CHANGELOG.md` 2026-08-29 (c)).\n"
            "7. `patch_navbar_rebuild_sync_status_steps_diag_v1.py`: navbar rebuild (shared height, width-based hierarchy), \"Syncing...\" alpha-only fixed-height fix, steps-undercount diagnostic logging.\n"
            "8. `patch_workout_session_scoped_metrics_v1.py`: session-scoped Distance/Steps/Elevation/ActiveCalories Health Connect records for every workout, gated by exercise type.\n"
            "9. `patch_sync_activity_signal_and_midnight_cache_v1.py`: `SYNC_ACTIVITY_TAG` background-sync-activity signal for the \"Syncing...\" indicator; `refreshFromCache()` midnight-staleness guard.\n"
            "\n"
            "(Full detail for 7-9 in `CHANGELOG.md` 2026-08-31.)\n"
        ),
        unique_marker="patch_sync_activity_signal_and_midnight_cache_v1.py`: `SYNC_ACTIVITY_TAG`",
        description="add delivered-scripts entries 7-9",
    )

    print("== 3/3: CONTEXT.md ==")

    apply_edit(
        CONTEXT_FILE,
        old="Updated: 2026-08-30",
        new="Updated: 2026-08-31",
        expected_old_count=1,
        expected_new_count=1,
        description="bump updated date",
    )

    apply_edit(
        CONTEXT_FILE,
        old=(
            "- Per-session Huawei distance has priority; steps/calories/elevation summary metrics are summed across all matching Huawei sample points, not just the first.\n"
            "- Workouts written `ACTIVELY_RECORDED` with Huawei device manufacturer.\n"
            "- Session + related calories written as a bundle.\n"
        ),
        new=(
            "- Per-session Huawei distance has priority; steps/calories/elevation summary metrics are summed across all matching Huawei sample points, not just the first. Steps can still be missing for some activities (Huawei-side `dataSummary` gap under investigation; diagnostic logging in place, no fix yet -- see `SESSION_HANDOFF.md`).\n"
            "- Workouts written `ACTIVELY_RECORDED` with Huawei device manufacturer.\n"
            "- Session + related calories written as a bundle; distance/steps/elevation (when the exercise type plausibly has them) are also written as their own Health Connect records scoped to the exact session interval, so third-party readers see real per-workout metrics rather than only a bare session plus an unrelated background aggregate.\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="update workout interoperability baseline",
    )

    apply_edit(
        CONTEXT_FILE,
        old=(
            "## UI baseline\n"
            "\n"
            "August colors remain unchanged. UI direction is quieter/content-first: flat outlined cards, restrained hero depth, pill buttons, 48 dp targets, restrained tween motion, one primary Settings action, no fake press animation on non-clickable cards. Bottom navbar: destination buttons ~20% smaller than the center Refresh button (46dp vs 72dp), symmetric between Today/Settings. Today header shows a fade in/out \"Syncing...\" line while a sync is in progress. Settings ends with a small engraved-style signature (no new font asset).\n"
            "\n"
            "## Do not regress"
        ),
        new=(
            "## UI baseline\n"
            "\n"
            "August colors remain unchanged. UI direction is quieter/content-first: flat outlined cards, restrained hero depth, pill buttons, 48 dp targets, restrained tween motion, one primary Settings action, no fake press animation on non-clickable cards. Bottom navbar: all controls share one common height (64dp); Refresh reads as primary via width (84dp pill), not height. Today header shows a fixed-height, alpha-only fade \"Syncing...\" line while `SyncUiState.isSyncing` (now `isUiTriggeredSyncing || isBackgroundSyncActive`) is true. Settings ends with a small engraved-style signature (no new font asset).\n"
            "\n"
            "## Dashboard cache\n"
            "\n"
            "`DashboardSnapshotCache` reads (both `buildInitialState()` on cold launch and `refreshFromCache()` after any sync completion or retry) zero daily-total fields when the cached snapshot predates today's calendar date, via a shared `zeroedDailyTotals()` helper. Recent-workout history is never zeroed by this.\n"
            "\n"
            "## Do not regress"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="update UI baseline, add dashboard cache section",
    )

    apply_insertion(
        CONTEXT_FILE,
        anchor="- Never output `git diff -- ...` in delivery instructions.",
        new_with_anchor=(
            "- Never output `git diff -- ...` in delivery instructions.\n"
            "- Do not resize navbar controls by height for visual hierarchy; use width. All navbar controls share one height.\n"
            "- `writeSnapshot()`'s write order (steps before activitySessions) is load-bearing: the daily steps reconciliation's delete-then-reinsert must fully complete before workout-scoped `StepsRecord`s are written, or it silently deletes them. Preserve this ordering explicitly if these writes are ever parallelized.\n"
            "- Do not apply a cached dashboard snapshot unconditionally on any code path; always guard against the cache predating today (see `zeroedDailyTotals()`)."
        ),
        unique_marker="Do not apply a cached dashboard snapshot unconditionally",
        description="add three new do-not-regress rules",
    )

    print("== Checking for changes to commit. ==")
    subprocess.run(["git", "add", "-A"], cwd=str(REPO_ROOT), check=True)

    status_result = subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(REPO_ROOT), capture_output=True, text=True
    )
    if not status_result.stdout.strip():
        print("Nothing staged to commit (all steps already applied on a prior run). Skipping commit/push.")
        print("Done.")
        return

    commit_msg = (
        "docs: record navbar rebuild, session-scoped metrics, sync-activity + "
        "midnight-cache fixes\n\n"
        "Updates CHANGELOG.md, SESSION_HANDOFF.md, and CONTEXT.md to reflect the "
        "three code patches delivered 2026-08-31:\n"
        "patch_navbar_rebuild_sync_status_steps_diag_v1.py,\n"
        "patch_workout_session_scoped_metrics_v1.py, and\n"
        "patch_sync_activity_signal_and_midnight_cache_v1.py.\n"
        "No code changes -- documentation only.\n"
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
