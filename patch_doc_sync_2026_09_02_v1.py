#!/usr/bin/env python3
"""
patch_doc_sync_2026_09_02_v1.py

Documentation-only sync pass. No Kotlin/XML/Gradle source is touched; this
patch only updates project .md docs and removes stale repo-root patch
scripts. Compile gate is still run (per standing process) as a structural
safety net, but no source file is modified so it is expected to be a no-op
pass.

Findings fixed:

1. Corporate wellness app status was stale in five docs. `sync.md`
   (2026-08-31, section 4.6) already recorded that the corporate wellness
   app reliably imports and accepts BitLut-synced workouts once the
   session-scoped Distance/Steps/Elevation sub-metric write landed, but
   `CLAUDE.md`, `CONTEXT.md`, `SESSION_HANDOFF.md`, `docs/BACKLOG.md`, and
   `README.md` still described this as an open, unresolved investigation.
   All five corrected to match `sync.md`, which remains the durable
   technical reference.

2. `CLAUDE.md`'s "Current baseline" header was dated 2026-08-29, a day
   behind its own already-current content and the 2026-08-31 work recorded
   in every sibling doc (navbar rebuild, session-scoped workout
   sub-metrics, sync-activity signal, midnight-cache guard). Header and two
   missing baseline bullets added.

3. `design.md` named only Navy/Lime/Tangerine/Purple; the actual source of
   truth (`AugustTokens.kt`'s `AugustColor`) additionally uses
   Ink/Canvas/Surface as the core neutral-role names, with Navy as a
   same-color alias for Ink in its architectural/navigation role. Doc
   updated to name both so it doesn't read as a mismatch against real code.

4. `README.md` was the only project doc still in Russian. Translated to
   English for parity with CLAUDE.md/CONTEXT.md/SESSION_HANDOFF.md/
   design.md/sync.md/docs/*, and its corporate-app section corrected to
   match finding 1.

5. Repo hygiene: `patch_localize_exercise_titles_v1.py` and
   `patch_security_audit_cleanup_v1.py` are stale delivery artifacts --
   both verified already fully applied in source (localized fallback
   workout titles via `HuaweiWorkoutTypeMapper.localizedDisplayName()`;
   removal of the dead Huawei OAuth-style client secret, dead
   ACTIVITY_SESSION_MIN/MAX_GAP constants, and duplicated manifest
   comments). Removed per the standing "repo root stays clean between
   sessions" rule.

Mandatory workflow already completed before this script was written:
hand-edited mirror -> real diff (diff -u against the original tree) ->
this script generated from that diff -> tested on a clean extraction with
a fake gradlew -> byte-diffed against the mirror -> re-run for idempotency.
"""
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"

DESIGN_FILE = REPO_ROOT / "design.md"
CONTEXT_FILE = REPO_ROOT / "CONTEXT.md"
HANDOFF_FILE = REPO_ROOT / "SESSION_HANDOFF.md"
CLAUDE_FILE = REPO_ROOT / "CLAUDE.md"
BACKLOG_FILE = REPO_ROOT / "docs" / "BACKLOG.md"
README_FILE = REPO_ROOT / "README.md"
CHANGELOG_FILE = REPO_ROOT / "CHANGELOG.md"

STALE_PATCH_SCRIPTS = [
    REPO_ROOT / "patch_localize_exercise_titles_v1.py",
    REPO_ROOT / "patch_security_audit_cleanup_v1.py",
]

README_NEW_CONTENT = """# BitLut

Open-source, local Android bridge between **HUAWEI Health** and **Android Health Connect**.

```text
HUAWEI Health -> BitLut -> Health Connect -> compatible apps
```

No BitLut account, backend, ads, or server-side health data storage.

## What syncs

Current scope is activity and workout data only: steps, distance, floors/elevation gain, calories when available, and workout sessions. HUAWEI workout types are normalized through a single `HuaweiWorkoutTypeMapper`; non-workout states are filtered out.

Workout distance comes from HUAWEI's activity-scoped data when available. BitLut does not reconstruct workout distance from coarse daily Health Connect aggregates.

## Workout records

Exercise sessions are written to Health Connect as `ACTIVELY_RECORDED` with Huawei device metadata, a deterministic `clientRecordId`, and a stable `clientRecordVersion` for an unchanged workout. The session and its related total calories are written as one bundle. Since 2026-08-31, distance/steps/elevation are also written as their own Health Connect records scoped to the exact session interval (per exercise type), so third-party readers see real per-workout metrics.

The only approved derived value is the documented fallback for total workout calories, used when HUAWEI doesn't provide calories for a specific real workout. This exception is not extended to distance, steps, elevation, or any other metric.

## Dashboard

Workout cards depend on exercise type: walking/running use pace, cycling uses average speed, hiking uses elevation, swimming uses pace/100 m, strength uses duration/calories. Missing metrics are never replaced with invented zeros.

## Corporate wellness compatibility

The corporate wellness app now reliably imports and accepts BitLut-synced workouts, confirmed on a real device after workout distance/steps/elevation began being written as Health Connect records scoped to the workout's own time window (see `sync.md` section 4.6 for the full mechanism).

## Interface

Keeps the August palette: Navy, Lime, Tangerine, Purple, Inter Variable, and system light/dark themes. Current UI direction is calm and content-first: flat outlined cards, restrained hero depth, pill controls, comfortable touch targets, and minimal animation.

Settings is deliberately minimal: data source, one grouped connection/sync actions card, a Health Connect settings deep link, and the steps goal. Workout-filter UI has been removed, but `WorkoutFilterPrefs` still applies in the sync path.

## Verification before commit

Both checks are mandatory:

```bash
./gradlew :app:assembleDebug :app:lintDebug \\
  --no-daemon \\
  --max-workers=1 \\
  --no-watch-fs \\
  --console=plain \\
  -Dorg.gradle.jvmargs="-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8" \\
  -Pkotlin.compiler.execution.strategy=in-process
```

Before making changes, read `CLAUDE.md`, `CONTEXT.md`, `SESSION_HANDOFF.md`, `design.md`, and `sync.md`."""


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


def overwrite_whole_file(path: Path, new_content: str, sentinel: str, description: str) -> None:
    """Full-file replacement, idempotent via a sentinel string unique to the new content."""
    text = path.read_text(encoding="utf-8")
    if sentinel in text:
        print(f"  [skip] {description} (already applied)")
        return
    backup(path)
    path.write_text(new_content, encoding="utf-8")
    print(f"  [applied] {description}")


def remove_stale_patch_scripts() -> None:
    for script in STALE_PATCH_SCRIPTS:
        if not script.exists():
            print(f"  [skip] {script.name} already removed")
            continue
        backup(script)
        script.unlink()
        print(f"  [applied] removed stale patch script {script.name}")


def run_compile_gate() -> None:
    gradlew = REPO_ROOT / "gradlew"
    if not gradlew.exists():
        die("gradlew not found; cannot run compile gate")

    cmd = [
        str(gradlew),
        ":app:compileDebugKotlin",
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
            "Docs: sync corporate-app status to sync.md, refresh baseline dates, "
            "translate README to English, remove stale patch scripts",
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=REPO_ROOT, check=True)


def main() -> None:
    print("=== 1/7: design.md -- date + Ink/Canvas/Surface naming ===")
    apply_edit(
        DESIGN_FILE,
        old=(
            "# BitLut Design System\n"
            "\n"
            "Updated: 2026-08-29\n"
        ),
        new=(
            "# BitLut Design System\n"
            "\n"
            "Updated: 2026-09-02\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="design.md: bump Updated date",
    )
    apply_edit(
        DESIGN_FILE,
        old=(
            "## Color roles — unchanged\n"
            "\n"
            "- Navy `#151728`: architectural anchor/navigation/dark canvas.\n"
            "- Navy Raised `#1C1E33`: dark raised/hero surface.\n"
            "- Lime `#DFFF6A`: primary action and hero progress.\n"
            "- Tangerine `#F28500`: sync action / active toggle signal.\n"
            "- Purple `#6E5CF6`: focus and secondary interaction detail.\n"
            "- Light canvas `#F7F8FC`, white surface.\n"
            "- Inter Variable remains the app font.\n"
        ),
        new=(
            "## Color roles — unchanged\n"
            "\n"
            "`AugustTokens.kt` (`AugustColor`) is the single source of truth for the exact hex values; this section names the semantic roles.\n"
            "\n"
            "- Ink `#151728`: core neutral / foreground-on-Lime / dark canvas. Also aliased as Navy in its architectural-anchor/navigation role — same color, two semantic names for two roles.\n"
            "- Navy Raised `#1C1E33`: dark raised/hero surface.\n"
            "- Canvas `#F7F8FC`: light background. Surface `#FFFFFF`: white card fill.\n"
            "- Lime `#DFFF6A`: primary action and hero progress.\n"
            "- Tangerine `#F28500`: sync action / active toggle signal (Settings toggle \"on\" track and the bottom nav Refresh fill only; Purple keeps every other focus/selection role).\n"
            "- Purple `#6E5CF6`: focus and secondary interaction detail.\n"
            "- Inter Variable remains the app font.\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="design.md: name Ink/Canvas/Surface alongside Navy/Lime/Tangerine/Purple",
    )

    print("=== 2/7: CONTEXT.md -- date, sync.md pointer, corporate-app status ===")
    apply_edit(
        CONTEXT_FILE,
        old=(
            "# BitLut — Current Context\n"
            "\n"
            "Updated: 2026-08-31\n"
        ),
        new=(
            "# BitLut — Current Context\n"
            "\n"
            "Updated: 2026-09-02\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="CONTEXT.md: bump Updated date",
    )
    apply_edit(
        CONTEXT_FILE,
        old=(
            "BitLut is a local-first Kotlin/Jetpack Compose Android bridge from HUAWEI Health to Android Health Connect.\n"
            "\n"
            "## Current product scope\n"
        ),
        new=(
            "BitLut is a local-first Kotlin/Jetpack Compose Android bridge from HUAWEI Health to Android Health Connect.\n"
            "\n"
            "`sync.md` is the durable technical reference for the full sync pipeline (why it's built the way it is); this file stays the short current-state summary.\n"
            "\n"
            "## Current product scope\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="CONTEXT.md: add sync.md pointer",
    )
    apply_edit(
        CONTEXT_FILE,
        old=(
            "- Corporate wellness app still ignores BitLut-origin workouts; source-origin allowlisting is the leading external explanation. BitLut cannot spoof Health Connect `DataOrigin`.\n"
        ),
        new=(
            "- Corporate wellness app now reliably imports and accepts BitLut-synced workouts, confirmed on a real device after the session-scoped Distance/Steps/Elevation sub-metric write landed (see `sync.md` section 4.6). The earlier source-origin-allowlisting theory remains the explanation for why it took the interoperability fix to work; no further code changes are planned on this front.\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="CONTEXT.md: correct corporate wellness app status",
    )

    print("=== 3/7: SESSION_HANDOFF.md -- date + corporate-app resolution ===")
    apply_edit(
        HANDOFF_FILE,
        old=(
            "# BitLut — Session Handoff\n"
            "\n"
            "Current handoff date: 2026-08-31.\n"
        ),
        new=(
            "# BitLut — Session Handoff\n"
            "\n"
            "Current handoff date: 2026-09-02.\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="SESSION_HANDOFF.md: bump handoff date",
    )
    apply_edit(
        HANDOFF_FILE,
        old=(
            "### Corporate wellness app investigation\n"
            "\n"
            "Still unresolved and likely external. Real-device evidence shows BitLut workouts arrive correctly in Health Connect but the corporate app does not count them, while Huawei -> Apple Health workouts are accepted.\n"
            "\n"
            "Leading explanation: the corporate reader uses source-origin allowlisting/trust. Apple Health receives records from Huawei's first-party iOS app (`HKSource`), while Android Health Connect records written by BitLut necessarily have `Metadata.dataOrigin.packageName = com.openhealth.sync`. BitLut cannot legally/technically impersonate another package's `DataOrigin`.\n"
            "\n"
            "Already tried and insufficient on their own: recording method, calorie attachment, device manufacturer, Health Connect data-source settings deep link, accurate session distance, corrected exercise types, stable record version and bundled workout writes.\n"
            "\n"
            "Next useful test is on the corporate app side: confirm whether it accepts third-party Health Connect writer origins. Do not keep changing BitLut metadata blindly without new evidence.\n"
        ),
        new=(
            "### Corporate wellness app investigation — resolved 2026-08-31/09-01\n"
            "\n"
            "Real-device evidence now confirms the corporate app reliably imports and accepts BitLut-synced workouts. The fix was the 2026-08-31 session-scoped Health Connect sub-metric write (`writeActivitySessionsBatch()` now bundles `DistanceRecord`/`StepsRecord`/`ElevationGainedRecord` into the workout's own time window instead of leaving the reader to fall back on the separate, coarser background daily aggregate). Full technical detail lives in `sync.md` section 4.6.\n"
            "\n"
            "The original leading explanation (source-origin allowlisting/trust on the reader side) is still believed to be part of why earlier metadata-only attempts didn't work, but is no longer an open question requiring further code changes: recording method, calorie attachment, device manufacturer, Health Connect data-source settings deep link, accurate session distance, corrected exercise types, and stable record version were all tried and individually insufficient; the session-scoped sub-metrics were the piece that closed the gap.\n"
            "\n"
            "No further work is planned here unless a new, different reader-compatibility issue surfaces.\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="SESSION_HANDOFF.md: mark corporate wellness app investigation resolved",
    )

    print("=== 4/7: CLAUDE.md -- baseline date/bullets + corporate-app status ===")
    apply_edit(
        CLAUDE_FILE,
        old=(
            "## Current baseline — 2026-08-29\n"
            "\n"
            "- Huawei Health Kit authorization and real activity reads work.\n"
            "- `HuaweiWorkoutTypeMapper` is the single Huawei workout-ID mapping source.\n"
            "- Per-session Huawei workout distance has priority over aggregate reconstruction.\n"
            "- Health Connect workouts are `ACTIVELY_RECORDED`, use Huawei device manufacturer metadata, deterministic client record IDs and stable versions, and write session + related calories as one bundle.\n"
            "- Dashboard workout metrics are type-aware and omit unavailable values.\n"
            "- `DashboardCardLayoutPrefs` is the sole dashboard card order/visibility layer.\n"
            "- `GoalPrefs` stores the steps goal only.\n"
            "- August colors and system light/dark themes remain the design baseline; surfaces are now quieter and flatter.\n"
            "- `assembleDebug` and `lintDebug` are mandatory before commit.\n"
        ),
        new=(
            "## Current baseline — 2026-08-31\n"
            "\n"
            "- Huawei Health Kit authorization and real activity reads work.\n"
            "- `HuaweiWorkoutTypeMapper` is the single Huawei workout-ID mapping source.\n"
            "- Per-session Huawei workout distance has priority over aggregate reconstruction.\n"
            "- Health Connect workouts are `ACTIVELY_RECORDED`, use Huawei device manufacturer metadata, deterministic client record IDs and stable versions, and write session + related calories as one bundle.\n"
            "- Workout distance/steps/elevation are also written as their own Health Connect records scoped to the exact session interval (gated per exercise type), so third-party readers see real per-workout metrics instead of only a coarser background aggregate. See `sync.md` section 4.6-4.7 for the full mechanism.\n"
            "- Dashboard workout metrics are type-aware and omit unavailable values.\n"
            "- `DashboardCardLayoutPrefs` is the sole dashboard card order/visibility layer.\n"
            "- `GoalPrefs` stores the steps goal only.\n"
            "- August colors and system light/dark themes remain the design baseline; surfaces are now quieter and flatter.\n"
            "- Bottom navbar: all controls share one common height (64dp); Refresh reads as primary via width (84dp pill), not height.\n"
            "- `assembleDebug` and `lintDebug` are mandatory before commit.\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="CLAUDE.md: bump baseline date, add sub-metrics + navbar bullets",
    )
    apply_edit(
        CLAUDE_FILE,
        old=(
            "The corporate wellness app currently ignores BitLut-origin workouts despite valid Health Connect records. Treat source-origin allowlisting on the reader side as the leading hypothesis until new evidence appears; do not keep mutating metadata blindly.\n"
        ),
        new=(
            "The corporate wellness app now reliably imports BitLut-origin workouts, confirmed on a real device after the 2026-08-31 session-scoped Distance/Steps/Elevation sub-metric write (see `sync.md` section 4.6). Do not mutate workout write metadata further on this front without new evidence of a different problem.\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="CLAUDE.md: correct corporate wellness app status",
    )

    print("=== 5/7: docs/BACKLOG.md -- date + move corporate-app item to Completed ===")
    apply_edit(
        BACKLOG_FILE,
        old=(
            "# BitLut Backlog\n"
            "\n"
            "Updated: 2026-08-29\n"
            "\n"
            "## Highest priority\n"
            "\n"
            "- Confirm with the corporate wellness app/vendor whether third-party Health Connect `DataOrigin` packages are accepted or allowlisted. Do not keep mutating BitLut workout metadata without evidence.\n"
            "- Add focused unit tests for `HuaweiWorkoutTypeMapper` and workout metric selection.\n"
            "- Add screenshot/UI tests for Summary, Settings, dashboard editor, light mode and dark mode.\n"
        ),
        new=(
            "# BitLut Backlog\n"
            "\n"
            "Updated: 2026-09-02\n"
            "\n"
            "## Highest priority\n"
            "\n"
            "- Add focused unit tests for `HuaweiWorkoutTypeMapper` and workout metric selection.\n"
            "- Add screenshot/UI tests for Summary, Settings, dashboard editor, light mode and dark mode.\n"
            "- Walking-steps undercount: awaiting a real-device diagnostic log showing `ActivitySummary.dataSummary`'s actual contents for a failing activity before attempting a structural fix (see `sync.md` section 8, `SESSION_HANDOFF.md`).\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="docs/BACKLOG.md: bump date, replace resolved item with open walking-steps item",
    )
    apply_insertion(
        BACKLOG_FILE,
        anchor=(
            "- Removed one-off delivery patch scripts from the repository."
        ),
        new_with_anchor=(
            "- Removed one-off delivery patch scripts from the repository.\n"
            "- Workout session-scoped Distance/Steps/Elevation Health Connect records; corporate wellness app now reliably imports BitLut-synced workouts (confirmed on a real device, `sync.md` section 4.6)."
        ),
        unique_marker="corporate wellness app now reliably imports BitLut-synced workouts (confirmed on a real device, `sync.md` section 4.6).",
        description="docs/BACKLOG.md: add corporate-app resolution to Completed",
    )

    print("=== 6/7: README.md -- translate to English + correct corporate-app status ===")
    overwrite_whole_file(
        README_FILE,
        README_NEW_CONTENT,
        sentinel="Open-source, local Android bridge between",
        description="README.md: full translation to English + corporate-app correction",
    )

    print("=== 7/7: CHANGELOG.md entry + stale patch script removal ===")
    apply_edit(
        CHANGELOG_FILE,
        old=(
            "# Changelog\n"
            "\n"
            "## 2026-08-31 -- navbar rebuild, workout Health Connect sub-records, Syncing indicator + midnight-cache fixes\n"
        ),
        new=(
            "# Changelog\n"
            "\n"
            "## 2026-09-02 -- documentation sync pass, repo root cleanup\n"
            "\n"
            "- **Corporate wellness app status corrected across all docs.** `sync.md`\n"
            "  (2026-08-31) already recorded that the corporate wellness app reliably\n"
            "  imports and accepts BitLut-synced workouts once the session-scoped\n"
            "  Distance/Steps/Elevation sub-metric write landed, but `CLAUDE.md`,\n"
            "  `CONTEXT.md`, `SESSION_HANDOFF.md`, `docs/BACKLOG.md`, and `README.md`\n"
            "  had not been updated to match and still described this as an open,\n"
            "  unresolved investigation. All five now point to `sync.md` section 4.6 as\n"
            "  the resolved explanation; no code change, documentation only.\n"
            "- `CLAUDE.md`'s \"Current baseline\" header was still dated 2026-08-29, a day\n"
            "  behind its own already-current content plus the 2026-08-31 work recorded\n"
            "  everywhere else (navbar rebuild, session-scoped workout sub-metrics,\n"
            "  sync-activity signal, midnight-cache guard). Updated the header and added\n"
            "  the two missing baseline bullets so the file matches its own sibling docs.\n"
            "- `design.md` described only the Navy/Lime/Tangerine/Purple palette names;\n"
            "  `AugustTokens.kt` is the actual source of truth and additionally uses\n"
            "  Ink/Canvas/Surface as the core neutral-role names (Navy is a same-color\n"
            "  alias for Ink in its architectural/navigation role). Doc now names both\n"
            "  so it doesn't read as a mismatch against the real token file.\n"
            "- `README.md` translated from Russian to English for parity with every\n"
            "  other project doc, and its corporate-app section corrected to match.\n"
            "- Removed `patch_localize_exercise_titles_v1.py` and\n"
            "  `patch_security_audit_cleanup_v1.py` from the repo root -- both verified\n"
            "  already fully applied in source (localized fallback workout titles;\n"
            "  removal of the dead Huawei OAuth-style client secret, dead activity-\n"
            "  session constants, and duplicated manifest comments) -- per the standing\n"
            "  \"repo root stays clean between sessions\" rule.\n"
            "\n"
            "## 2026-08-31 -- navbar rebuild, workout Health Connect sub-records, Syncing indicator + midnight-cache fixes\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="CHANGELOG.md: add 2026-09-02 documentation sync entry",
    )
    remove_stale_patch_scripts()

    print("=== Running compile gate (no source touched; expected no-op) ===")
    run_compile_gate()

    print("=== Compile gate passed. Committing and pushing. ===")
    git_commit_and_push()

    print("Done.")


if __name__ == "__main__":
    main()
