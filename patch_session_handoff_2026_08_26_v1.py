#!/usr/bin/env python3
"""
BitLut patch: update SESSION_HANDOFF.md with this session's changes,
decisions, and established facts (2026-08-26).

This is a documentation-only change -- no Kotlin, XML, or Gradle source is
touched. It records, for the next session:

  1. The five patches shipped this session and why, in order:
     - Health Connect recording-method fix (Metadata.autoRecorded, alpha12
       bump) -- root cause of the corporate app not importing workouts that
       looked fine in Google Fit.
     - Estimated workout calories (MET-formula TotalCaloriesBurnedRecord) --
       a bare ExerciseSessionRecord with nothing attached is a documented
       reason third-party readers skip a workout.
     - The manifest permission bug that blocked the resulting new Health
       Connect permission dialog from appearing at all.
     - The stale-daily-totals-across-midnight cold-launch bug.
     - The strength-training workout card metric fix (Duration + Calories
       only, shared WorkoutCalorieEstimator).
  2. The "estimated workout calories" policy as a deliberate, scoped,
     user-approved exception to the project's "never synthesize fake health
     data" rule -- including exactly what is and isn't covered by it.
  3. Two patch-script process lessons from real failures this session (a
     fragile multi-line anchor breaking idempotency detection; an XML
     comment containing an illegal "--").
  4. A revised workout metric contract reflecting the strength-training
     special case.
  5. An updated next-session rule, including that the corporate-app fix is
     not yet confirmed on a real device as of this handoff.

The previous end-of-session baseline (2026-08-22) is condensed rather than
deleted outright, and the now-stale, fully-superseded 2026-08-22 "Workout
metric contract" section is removed rather than left as a duplicate that
would contradict the revised 2026-08-26 version above it.

Usage:
    python3 patch_session_handoff_2026_08_26_v1.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / "session_handoff_2026_08_26_v1"


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


_backed_up_paths: set = set()


def backup_once(path: Path) -> None:
    if path in _backed_up_paths:
        return
    relative = path.relative_to(ROOT)
    backup_path = BACKUP_DIR / relative
    if not backup_path.exists():
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_path)
        print(f"  backed up -> {backup_path.relative_to(ROOT)}")
    _backed_up_paths.add(path)


def read(path: Path) -> str:
    if not path.exists():
        die(f"Expected file not found: {path}")
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def apply_edit(path: Path, old: str, new: str, expected_count: int = 1) -> bool:
    """Text-anchored replacement for genuine changes (old text disappears)."""
    text = read(path)
    count_old = text.count(old)
    count_new = text.count(new)

    if count_old == 0 and count_new >= expected_count:
        print(f"  already applied, skipping: {path.name} ({new[:40]!r}...)")
        return False

    if count_old != expected_count:
        die(
            f"{path}: expected {expected_count} occurrence(s) of anchor in "
            f"{path.name}, found {count_old}. Refusing to apply (ambiguous or stale)."
        )

    backup_once(path)
    write(path, text.replace(old, new, expected_count))
    print(f"  applied: {path.name}")
    return True


NEW_OPENING_AND_BASELINE = '''Current handoff date: 2026-08-26.

Read `CLAUDE.md` and this file before changing code. Source code plus a fresh
successful build are the final authority if an older historical note conflicts.

## Product

BitLut is a local-first Kotlin + Jetpack Compose Android bridge:

```text
HUAWEI Health -> BitLut -> Android Health Connect
```

Current product scope is activity-only. BitLut must never synthesize missing
health data, **except** the one explicit, user-approved exception recorded
in "Estimated workout calories" below.

## End-of-session baseline (2026-08-26)

Root problem this session: workouts synced correctly through the whole
Huawei -> BitLut -> Health Connect -> Google Fit chain (confirmed on a real
cycling workout), but a separate corporate fitness app reading the same
Health Connect data was not importing them. Five patches shipped this
session, in this order, each gated on a real `assembleDebug`:

1. **Recording method fix.** Every record BitLut wrote used the raw
   `Metadata(...)` constructor, leaving `recordingMethod` at
   `RECORDING_METHOD_UNKNOWN`. Health Connect's own UI and Google Fit
   display `RECORDING_METHOD_UNKNOWN` records without filtering; a
   third-party reader is free to distrust/skip them -- this is why the
   corporate app couldn't see workouts that looked fine in Google Fit.
   Fixed by switching to `Metadata.autoRecorded(...)` with
   `Device(type = Device.TYPE_UNKNOWN)`. This required bumping
   `connect-client` from `1.1.0-alpha11` to `1.1.0-alpha12` -- that factory
   method does not exist on alpha11. (Two failed attempts before this
   landed: v9 used `autoRecorded` before confirming it needed alpha12; v10's
   fix was correct but its own idempotency check used one large fragile
   multi-line anchor that silently broke on a partially-applied prior
   state -- see "Patch script lessons" below.)

2. **Estimated workout calories.** Even with the recording-method fix, a
   bare `ExerciseSessionRecord` with no attached calorie or distance data is
   a documented reason real third-party Health Connect readers (MyFitnessPal
   requires calories; other apps require distance) decline to import a
   workout. Huawei's real `activeCalories` is permanently denied (error
   50005) for this individual-developer account, so BitLut had never had a
   real number to attach. Fixed by writing a MET-formula calorie *estimate*
   (Compendium of Physical Activities, 70 kg reference weight) as a
   `TotalCaloriesBurnedRecord` -- deliberately not `ActiveCaloriesBurnedRecord`,
   to avoid conflating an estimate with "measured by a real sensor." See
   "Estimated workout calories" section below for the full policy.

3. **Manifest permission bug.** Step 2 required a new Health Connect
   permission (`TotalCaloriesBurnedRecord` read+write) that was added to
   `HealthPermissionPolicy.kt`'s runtime request set but never declared in
   `AndroidManifest.xml`. Health Connect requires permissions to be declared
   in the manifest before it will show any request dialog for them --
   omitting it made the whole batched permission request silently return an
   empty grant set instead of prompting, even for previously-working
   permissions. Fixed by adding the missing `<uses-permission>` entries.
   (One failed attempt first: the fix's own new XML comment used a literal
   `--`, which is illegal inside an XML comment body per the XML spec --
   caught by `processDebugMainManifest`'s `SAXParseException`, not by this
   project's own sandbox tooling. See "Patch script lessons" below.)

4. **Stale daily totals across midnight.** Unrelated UX bug found during
   this session: `DashboardViewModel.buildInitialState()` applied whatever
   was in `DashboardSnapshotCache` unconditionally on cold launch, with no
   check for whether the cache was written on a previous calendar day.
   Opening the app the next morning showed yesterday's steps/distance/
   calories until the next sync completed. Fixed by comparing the cache's
   saved timestamp's local calendar date against today's; if the cache
   predates today, daily-total fields (steps, distance, calories, workout
   minutes, active hours, elevation, floors) reset to zero until the
   already-existing auto-sync-on-launch (`MainActivity.onResume()` ->
   `triggerAutomaticSyncOnLaunch()`) replaces them. `recentWorkouts` is
   deliberately left untouched -- a workout from yesterday is still valid
   history for the "previous workout" card regardless of what day it is now.

5. **Strength-training workout metrics.** The four-metric-slot contract
   (Duration, Distance, Avg speed, Steps/Elevation) doesn't make sense for
   strength training -- distance, speed, and steps are not meaningful for
   that exercise type. Fixed by special-casing
   `EXERCISE_TYPE_STRENGTH_TRAINING` in `workoutMetricDisplays()` to show
   only Duration + Calories, with calories preferring real
   `activeCaloriesKcal` and falling back to the same MET estimate from
   patch 2. The MET table/formula was extracted out of `GoogleHealthManager`
   into a new shared `com.openhealth.sync.util.WorkoutCalorieEstimator`
   object so the Health Connect write path and this display can never
   silently drift onto two different formulas.

Also still true from before this session (2026-08-22 baseline, condensed):

- HUAWEI -> Health Connect synchronization working on a real device.
- August v3 dark theme, system-driven; `HealthAccent` is `@Composable`.
- Manual and periodic WorkManager synchronization; sync lease/reuse
  protection; partial Huawei scope denial handled per category.
- Health Connect request-storm protection and bounded dashboard reads.
- Haze removed; no blur dependency/toolchain migration.
- Settings daily goals reduced to steps only.
- See the "Dark theme," "August v3," and "Health Connect quota rules"
  sections below -- unchanged this session.

## Estimated workout calories (new, 2026-08-25/26)

**This is a deliberate, explicit, user-approved exception** to this
project's "never synthesize fake health data" rule -- raised directly with
the user mid-session before implementation, not assumed. Scope, exactly as
agreed:

- Only `TotalCaloriesBurnedRecord` is estimated. No other record type
  should be synthesized under this exception.
- The formula: `kcal = MET * 3.5 * 70kg * minutes / 200`, MET values from
  the Compendium of Physical Activities, "general/moderate" variant per
  exercise type (see `WorkoutCalorieEstimator.kt`'s own doc comment for the
  full table). 70 kg is a fixed reference weight -- BitLut has no access to
  real user weight, and adding that would itself be a new data category,
  out of scope for this fix.
- `ActivitySessionData.activeCaloriesKcal`, which powers BitLut's own
  dashboard, is **never** written to by the estimate. It stays real-or-null.
  BitLut's own UI continues to honestly show no calorie figure when Huawei
  hasn't provided one. The estimate exists only for (a) the
  `TotalCaloriesBurnedRecord` written to Health Connect for third-party
  readers, and (b) the strength-training workout card's calorie display,
  as an explicit fallback when real data is absent.
- Full rationale recorded in `docs/HEALTH_DATA_PERMISSION_MATRIX.md`'s
  "Documented exception: estimated workout calories" section -- read that
  before touching this again.
- Required a new Health Connect permission
  (`READ_TOTAL_CALORIES_BURNED`/`WRITE_TOTAL_CALORIES_BURNED`), itself an
  explicit, user-approved exception to "no new Health Connect/Huawei
  permissions." Declared in `AndroidManifest.xml` and requested via
  `HealthPermissionPolicy.kt`.

**Do not extend this exception to any other record type** (e.g. distance,
elevation, steps) without the same explicit conversation and the same kind
of documented, scoped write-up.

## Patch script lessons (new this session)

Two real failures this session, both worth remembering:

- **Don't use one large multi-line block as both the edit anchor and the
  idempotency check.** v10's Step 3 tried to match/replace a ~20-line
  function body in one anchor; on the user's real file (after a prior
  partial run left subtly different bytes) the match came back empty on
  both old and new text, and the script died rather than recognizing
  "already applied." Fixed in v11 by checking several small, independent,
  symptom-based facts (does this import exist, does this constant exist,
  does this specific line match a pattern) instead of one large anchor.
- **XML comments cannot contain a literal `--` anywhere in the body.** This
  is a hard XML well-formedness rule with no exception, unrelated to
  Android/Health Connect specifically. A patch script's own text-based
  idempotency testing (byte-diffing, running twice) cannot catch this --
  only real XML parsing (or the real Gradle manifest merger) can. Validate
  generated XML with a real parser (e.g. Python's
  `xml.etree.ElementTree.parse`) before delivering any patch that touches
  an `.xml` file, the same way Kotlin changes get a brace/paren balance
  check.
- Both failures were caught by the user's real `assembleDebug`/manifest
  merger, not by anything in the sandbox -- consistent with this project's
  standing rule that the sandbox cannot verify real compilation.

## Workout metric contract (revised 2026-08-26)

Every recent-workout card shows either three or four slots, or two slots
for strength training specifically:

- **Strength training** (`EXERCISE_TYPE_STRENGTH_TRAINING`): **Duration,
  Calories only** (2026-08-26 change -- see "Strength-training workout
  metrics" above). Calories prefers real `activeCaloriesKcal`, falls back
  to `WorkoutCalorieEstimator` when absent.
- **Biking** (`EXERCISE_TYPE_BIKING`): Duration, Distance, Avg speed (3
  slots -- the 4th slot/Elevation gain was removed for biking before this
  session; do not re-add a 4th slot for biking without discussion).
- **Every other exercise type**: Duration, Distance, Avg speed, Steps (4
  slots, unchanged from 2026-08-22).

Active calories and (for non-biking types) elevation gain were removed from
the general card display back on 2026-08-22 -- not hidden conditionally,
removed as a display contract -- because Huawei frequently scope-denies
`activeCalories` (50005) and elevation is rarely populated for the same
underlying reason. `ActivitySessionData.activeCaloriesKcal` /
`.elevationMeters` are still read/synced for CSV export and daily totals;
only general card display was narrowed. The strength-training card's new
Calories slot (2026-08-26) is a deliberate, narrow reintroduction of
calories to one specific card, not a reversal of that 2026-08-22 decision --
see "Estimated workout calories" above.

Data rules (unchanged from before, **except** the new calorie exception
above):

- Duration comes from the real ExerciseSessionRecord interval.
- Distance comes only from real imported/session/Health Connect distance data.
- Average speed is derived only when real distance exists.
- Steps come from real Health Connect step data overlapping the workout.
- Elevation comes only from real elevation data.
- Missing metrics render as `\u2014`.
- Never estimate distance from steps.
- Never estimate elevation or speed.
- Calories: real data preferred everywhere; the MET estimate is used
  **only** for (a) the Health Connect `TotalCaloriesBurnedRecord` write and
  (b) the strength-training card's calorie slot specifically -- see
  "Estimated workout calories" above for the full, deliberately narrow scope.

The current distance boundary fallback is deliberately conservative:

- it runs only when exact aggregate/session distance is missing;
- it queries a narrow window around the displayed workout;
- it attributes only exact temporal overlap;
- source records longer than three hours are rejected;
- if no real overlap exists, distance remains missing.

**Do not reopen this fallback logic.** Nothing this session touches it.

## Dark theme (2026-08-22)'''

OLD_OPENING_AND_BASELINE = '''Current handoff date: 2026-08-22.

Read `CLAUDE.md` and this file before changing code. Source code plus a fresh
successful build are the final authority if an older historical note conflicts.

## Product

BitLut is a local-first Kotlin + Jetpack Compose Android bridge:

```text
HUAWEI Health -> BitLut -> Android Health Connect
```

Current product scope is activity-only. BitLut must never synthesize missing
health data.

## End-of-session baseline

Four patches shipped and built successfully today (2026-08-22), in this order:

1. Workout cards narrowed from six metrics to four, for every exercise type
   (Duration, Distance, Avg speed, Steps).
2. August v3 dark theme activated -- system-driven (`isSystemInDarkTheme()`),
   not a manual in-app toggle. `BitPalette.dark()` already existed in the
   codebase but was unreachable; this activated it.
3. Steps Hero card given a two-value layout (Steps + Distance each as their
   own big number), new Tangerine accent color for Settings toggles and the
   navbar Refresh button, navbar narrowed slightly and Refresh button
   enlarged 15%.
4. Dark-mode follow-up fixes from real-device feedback: several icons/text
   were still gray/invisible in dark mode (root cause: `HealthAccent` was
   not theme-aware, now fixed -- see "Dark theme" below); navbar buttons
   given a light spring-based bounce on press; biking's 4th workout metric
   changed from Steps (illogical for cycling) to Elevation gain.

Also still true from before today:

- HUAWEI -> Health Connect synchronization working on a real device.
- Manual and periodic WorkManager synchronization.
- Sync lease/reuse protection against concurrent jobs.
- Partial Huawei scope denial handled per category instead of failing the whole sync.
- Health Connect request-storm protection and bounded dashboard reads.
- Last-known permission state preserved across transient Health Connect provider failures.
- Dashboard freshness timestamp tied to real data changes rather than app-open time.
- Haze removed; no blur dependency/toolchain migration.
- Settings daily goals reduced to the only currently used goal: steps.

## Dark theme (2026-08-22)'''


OLD_STALE_WORKOUT_CONTRACT = '''If something still looks gray/low-contrast in dark mode that wasn't covered
by today's fix, it is very likely another hardcoded `AugustColor.*`
reference that bypasses both `palette` and `HealthAccent` -- grep for direct
`AugustColor.InkSoft`/`AugustColor.Muted` usage in the same style as
`HealthAccent` had before today's fix.

## Workout metric contract (revised 2026-08-22)

Every recent-workout card shows four slots. The first three are the same for
every exercise type; the fourth is exercise-type-aware:

1. Duration
2. Distance
3. Average speed
4. **Steps** for most exercise types, **Elevation gain** specifically for
   `ExerciseSessionRecord.EXERCISE_TYPE_BIKING`

Data rules (unchanged from before):

- Duration comes from the real ExerciseSessionRecord interval.
- Distance comes only from real imported/session/Health Connect distance data.
- Average speed is derived only when real distance exists.
- Steps come from real Health Connect step data overlapping the workout.
- Elevation comes only from real elevation data.
- Missing metrics render as `\u2014`.
- Never estimate distance from steps.
- Never estimate calories from duration/body assumptions.
- Never invent elevation or speed.

Active calories and (for non-biking types) elevation gain were deliberately
removed from the card display entirely -- not hidden conditionally, removed
as a display contract -- because Huawei frequently scope-denies
`activeCalories` (50005) and elevation is rarely populated for the same
underlying reason, so the old six-slot layout mostly showed four real values
and two permanent dashes. `ActivitySessionData.activeCaloriesKcal` /
`.elevationMeters` are still read/synced for CSV export and daily totals;
only card display was narrowed.

The current distance boundary fallback is deliberately conservative:

- it runs only when exact aggregate/session distance is missing;
- it queries a narrow window around the displayed workout;
- it attributes only exact temporal overlap;
- source records longer than three hours are rejected;
- if no real overlap exists, distance remains missing.

**Do not reopen this fallback logic.** This is the same standing rule as
before today; nothing about today's four-metric-slot or biking-elevation
change touches this fallback at all.

## Health Connect quota rules'''

NEW_DARK_THEME_HEADER = '''If something still looks gray/low-contrast in dark mode that wasn't covered
by today's fix, it is very likely another hardcoded `AugustColor.*`
reference that bypasses both `palette` and `HealthAccent` -- grep for direct
`AugustColor.InkSoft`/`AugustColor.Muted` usage in the same style as
`HealthAccent` had before today's fix.

## Health Connect quota rules'''


OLD_NEXT_SESSION_RULE = '''## Next-session rule

Start from the working sync baseline. Do not reopen the workout-distance
problem by trying to force a number into a session that has no real distance
record. Do not revert the dark-theme `HealthAccent` fix back to a plain
non-composable object without an equally thorough audit of every call site's
theme-awareness. Focus future work on new explicitly scoped product
improvements.'''

NEW_NEXT_SESSION_RULE = '''## Next-session rule

Start from the working sync baseline. Do not reopen the workout-distance
problem by trying to force a number into a session that has no real distance
record. Do not revert the dark-theme `HealthAccent` fix back to a plain
non-composable object without an equally thorough audit of every call site's
theme-awareness.

**Awaiting real-device confirmation:** the user was waiting on a fresh
strength-training workout to confirm the full recording-method +
estimated-calories fix actually makes the corporate app import it -- this
was not yet confirmed as of this handoff. If it's still not importing on
the next session, check the corporate app's own logs/support docs before
assuming another BitLut-side gap; the two most likely remaining culprits it
does NOT yet address are (a) whether that app also requires
`ExerciseSegment` data on the session, and (b) whether it requires
`DistanceRecord` specifically rather than any calorie record, which would
not apply to strength training at all.

Do not extend the "estimated workout calories" exception to any other
record type without the same explicit user conversation this session had.
Do not use one large multi-line block as both a patch script's edit anchor
and its idempotency check -- see "Patch script lessons" above. Validate any
generated `.xml` with a real parser before delivering a patch that touches
one. Focus future work on new explicitly scoped product improvements.'''


def main() -> None:
    handoff_path = ROOT / "SESSION_HANDOFF.md"
    if not handoff_path.exists():
        die(f"Required file missing: {handoff_path}")

    print("== Step 1/3: replace opening + end-of-session baseline ==")
    apply_edit(handoff_path, OLD_OPENING_AND_BASELINE, NEW_OPENING_AND_BASELINE)

    print("== Step 2/3: remove stale 2026-08-22 workout metric contract (superseded above) ==")
    apply_edit(handoff_path, OLD_STALE_WORKOUT_CONTRACT, NEW_DARK_THEME_HEADER)

    print("== Step 3/3: update next-session rule ==")
    apply_edit(handoff_path, OLD_NEXT_SESSION_RULE, NEW_NEXT_SESSION_RULE)

    # ---------------------------------------------------------------
    # Verification
    # ---------------------------------------------------------------
    print("\n== Verification ==")
    text = read(handoff_path)
    headers = [line for line in text.splitlines() if line.startswith("## ")]
    if len(headers) != len(set(headers)):
        seen = set()
        dupes = []
        for h in headers:
            if h in seen:
                dupes.append(h)
            seen.add(h)
        die(f"Duplicate section header(s) found in {handoff_path.name} after patch: {dupes}")
    print(f"  verified: {len(headers)} section headers, all unique")

    if "Current handoff date: 2026-08-26." not in text:
        die(f"Expected updated handoff date not found in {handoff_path.name}.")
    if "## Estimated workout calories" not in text:
        die(f"Expected new 'Estimated workout calories' section not found in {handoff_path.name}.")
    if "## Patch script lessons" not in text:
        die(f"Expected new 'Patch script lessons' section not found in {handoff_path.name}.")
    if "Workout metric contract (revised 2026-08-22)" in text:
        die(f"Stale 2026-08-22 workout metric contract header still present in {handoff_path.name}.")
    print("  verified: date, new sections, and stale-section removal all correct")

    print("\n== Compile gate: :app:assembleDebug ==")
    gradlew = ROOT / "gradlew"
    if not gradlew.exists():
        die("gradlew not found at repo root -- run this script from the BitLut repo root.")

    result = subprocess.run(
        [
            str(gradlew),
            ":app:assembleDebug",
            "--no-daemon",
            "--max-workers=1",
            "--no-watch-fs",
            "--console=plain",
            "-Dorg.gradle.jvmargs=-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8",
            "-Pkotlin.compiler.execution.strategy=in-process",
        ],
        cwd=ROOT,
    )
    if result.returncode != 0:
        die("assembleDebug failed. No commit, no push. Fix the build and re-run this script.")

    print("\n== assembleDebug succeeded. Committing and pushing. ==")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    commit = subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "Update SESSION_HANDOFF.md with 2026-08-26 session: recording "
            "method fix, estimated workout calories, manifest permission "
            "bug, stale-cache-across-midnight fix, strength-training "
            "workout metrics",
        ],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("Nothing to commit (already applied) -- skipping push.")
        return

    push = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT)
    if push.returncode != 0:
        die("git push failed. Commit succeeded locally; push manually once resolved.")

    print("\nDone.")


if __name__ == "__main__":
    main()
