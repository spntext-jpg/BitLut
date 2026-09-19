#!/usr/bin/env python3
"""
patch_english_fallback_titles_2026_09_16_v3.py

Experiment: force fallback workout titles written to Health Connect to
always be English, regardless of device/app locale, as a candidate fix
for the corporate wellness reader's "binder died" import failures
(open investigation, docs/BACKLOG.md).

Trigger (Paulo's own observation, 2026-09-16): BitLut's fallback workout
titles -- used only when Huawei's own ActivityRecord supplies no name --
switched from English to Russian text around the same time the corporate
reader started failing to import BitLut-synced workouts. This has not
been confirmed by any corporate-app-side log; it is one candidate
explanation (a reader with non-Unicode-safe title/string handling)
alongside the still-open payload-churn investigation already documented
in docs/BACKLOG.md and sync.md. Explicitly scoped as an experiment: if a
real-device retest with the corporate reader does not resolve the
failures, this is designed to be a two-call-site revert (see each
change's own comment below).

Root mechanism (verified by reading the real, current source before
writing this script -- HuaweiWorkoutTypeMapper.kt,
HuaweiHealthManager.kt, HuaweiExportParser.kt, and both
values/values-ru strings.xml files):

- `HuaweiWorkoutTypeMapper.localizedDisplayName(context, exerciseType)`
  calls `context.getString(resId)`, which Android resolves against the
  app's *currently active* Configuration/locale at call time -- not a
  fixed language. `values-ru/strings.xml` genuinely has different text
  for every `exercise_type_*` key (e.g. exercise_type_yoga: "Yoga" vs
  "Йога"), confirmed by direct inspection, not assumed.
- This function has exactly two call sites in the whole codebase
  (confirmed by grep across every file in a fresh repomix export, not
  a partial search): `HuaweiHealthManager.kt`'s live-sync activity
  mapping, and `HuaweiExportParser.kt`'s archive/CSV import mapping.
  Both use it purely as a fallback (`?:`) when Huawei's own `rawName`/
  `explicitName` is blank or synthetic. Both fallback titles end up as
  `ActivitySessionData.title`, which flows straight into
  `ExerciseSessionRecord.title` in `GoogleHealthManager.kt`'s
  `writeActivitySessionsBatch()` -- i.e. this is exactly the text a
  third-party Health Connect reader (the corporate app) receives for
  any workout Huawei didn't itself name.
- `localizedDisplayName()` is NOT called anywhere in the UI/dashboard
  layer (confirmed: zero occurrences in FinalBitLutShell.kt or any
  other UI file across the whole repo). So this change cannot affect
  what Paulo sees in BitLut's own dashboard -- only what third-party
  readers receive via Health Connect.

Fix: a new `HuaweiWorkoutTypeMapper.exportDisplayName(context,
exerciseType)` resolves the exact same `displayNameRes` string table,
but pinned to `Locale.ENGLISH` via the standard, verified
`createConfigurationContext` pattern (Android's documented way to
resolve a resource in a specific locale regardless of device locale;
available since API 17, comfortably within this project's minSdk 26).
Deliberately reuses the existing string table instead of adding a
second hardcoded English name map, so it cannot drift out of sync with
values/strings.xml if that file is ever edited. `localizedDisplayName()`
itself is left completely unchanged -- it has no callers touched by
this script, and is kept in case any future UI feature needs a
locale-aware exercise-type label.

Documentation updated to reflect this experiment: sync.md section 4.6
(title is no longer "possibly localized" for the write path),
SESSION_HANDOFF.md (new entry in Sync hardening), docs/BACKLOG.md (new
candidate cause appended to the existing open investigation item, not
a new item -- this is additional evidence for the same incident, not a
separate one), and CHANGELOG.md (new dated entry).

No Health Connect permission, schema, or record-type change. No new
Huawei scope. Historical sync window and no-fabricated-data rules are
unaffected -- this only changes which *language* an already-existing,
already-approved fallback string is rendered in.

Mandatory workflow already completed before this script was written:
read the real current file content directly from a fresh repomix
export (1789818271799_repomix-output.xml, uploaded this session, not
reused from an earlier stale export) -> hand-edited a mirror copy of
each real file -> verified every anchor's exact-occurrence count
against that real content before drafting the mirror edit -> this
script generated from those verified mirror diffs -> tested on a clean
extraction with a fake gradlew -> byte-diffed against the mirrors ->
re-run for idempotency.
"""
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"

MAPPER_FILE = REPO_ROOT / "app" / "src" / "main" / "java" / "com" / "openhealth" / "sync" / "data" / "HuaweiWorkoutTypeMapper.kt"
HUAWEI_MANAGER_FILE = REPO_ROOT / "app" / "src" / "main" / "java" / "com" / "openhealth" / "sync" / "data" / "HuaweiHealthManager.kt"
EXPORT_PARSER_FILE = REPO_ROOT / "app" / "src" / "main" / "java" / "com" / "openhealth" / "sync" / "data" / "import" / "HuaweiExportParser.kt"
SYNC_FILE = REPO_ROOT / "sync.md"
HANDOFF_FILE = REPO_ROOT / "SESSION_HANDOFF.md"
BACKLOG_FILE = REPO_ROOT / "docs" / "BACKLOG.md"
CHANGELOG_FILE = REPO_ROOT / "CHANGELOG.md"


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
    if not path.exists():
        die(f"Cannot edit missing file: {path}")
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
    the edit, so idempotency cannot key on the anchor's occurrence count.
    Keys instead on unique_marker, a string that only exists after this
    insertion has been applied.
    """
    if not path.exists():
        die(f"Cannot edit missing file: {path}")
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
            "Experiment: always write English fallback workout titles to Health Connect",
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=REPO_ROOT, check=True)


# --- HuaweiWorkoutTypeMapper.kt: add exportDisplayName() ------------------

OLD_MAPPER_IMPORTS = (
    "import android.content.Context\n"
    "import androidx.health.connect.client.records.ExerciseSessionRecord\n"
)
NEW_MAPPER_IMPORTS = (
    "import android.content.Context\n"
    "import android.content.res.Configuration\n"
    "import androidx.health.connect.client.records.ExerciseSessionRecord\n"
)

OLD_MAPPER_TAIL = (
    "    fun localizedDisplayName(context: Context, exerciseType: Int): String {\n"
    "        val resId = displayNameRes[exerciseType] ?: R.string.exercise_type_other_workout\n"
    "        return context.getString(resId)\n"
    "    }\n"
    "}"
)
NEW_MAPPER_TAIL = (
    "    fun localizedDisplayName(context: Context, exerciseType: Int): String {\n"
    "        val resId = displayNameRes[exerciseType] ?: R.string.exercise_type_other_workout\n"
    "        return context.getString(resId)\n"
    "    }\n"
    "\n"
    "    /**\n"
    "     * English-only fallback title for a workout, used for the Health Connect\n"
    "     * write path instead of [localizedDisplayName] since 2026-09-16.\n"
    "     *\n"
    "     * Background: the fallback title written to `ExerciseSessionRecord.title`\n"
    "     * (used only when Huawei did not provide its own workout name) previously\n"
    "     * came from [localizedDisplayName], which resolves via the app's active\n"
    "     * device locale -- Russian on a Russian-locale device, English otherwise.\n"
    "     * A downstream corporate wellness-app reader started failing to import\n"
    "     * BitLut-synced workouts (\"binder died\") in a window that coincided with\n"
    "     * BitLut's workout titles switching from English to Cyrillic text on\n"
    "     * Paulo's own device. This is being tested as one candidate explanation\n"
    "     * (a reader with non-Unicode-safe title handling) alongside the other\n"
    "     * open investigation in docs/BACKLOG.md; it has not been confirmed by a\n"
    "     * corporate-app-side log. Explicit Huawei-provided names (`rawName`/\n"
    "     * `explicitName` at both call sites) are untouched by this change --\n"
    "     * they were never run through either display-name function and are\n"
    "     * already whatever text Huawei itself supplied.\n"
    "     *\n"
    "     * Resolves the same `displayNameRes` string table used by\n"
    "     * [localizedDisplayName], pinned to [Locale.ENGLISH] via\n"
    "     * `createConfigurationContext` regardless of the device's actual locale,\n"
    "     * so it can never drift out of sync with `values/strings.xml` by using a\n"
    "     * second hardcoded name table. [localizedDisplayName] itself is\n"
    "     * unchanged and still used for BitLut's own dashboard display, which\n"
    "     * has no bearing on this investigation and should keep following the\n"
    "     * user's language preference.\n"
    "     *\n"
    "     * To revert this experiment: change the two Health-Connect-write call\n"
    "     * sites (`HuaweiHealthManager.kt`, `HuaweiExportParser.kt`) back to\n"
    "     * calling [localizedDisplayName] instead of this function. Nothing else\n"
    "     * needs to change.\n"
    "     */\n"
    "    fun exportDisplayName(context: Context, exerciseType: Int): String {\n"
    "        val resId = displayNameRes[exerciseType] ?: R.string.exercise_type_other_workout\n"
    "        val englishConfig = Configuration(context.resources.configuration).apply {\n"
    "            setLocale(Locale.ENGLISH)\n"
    "        }\n"
    "        return context.createConfigurationContext(englishConfig).resources.getString(resId)\n"
    "    }\n"
    "}"
)


# --- HuaweiHealthManager.kt / HuaweiExportParser.kt: switch call sites ----

OLD_HHM_CALL = "                ?: HuaweiWorkoutTypeMapper.localizedDisplayName(context, exerciseType)"
NEW_HHM_CALL = "                ?: HuaweiWorkoutTypeMapper.exportDisplayName(context, exerciseType)"

OLD_PARSER_CALL = "            val title = explicitName ?: HuaweiWorkoutTypeMapper.localizedDisplayName(context, exerciseType)"
NEW_PARSER_CALL = "            val title = explicitName ?: HuaweiWorkoutTypeMapper.exportDisplayName(context, exerciseType)"


# --- sync.md section 4.6 ---------------------------------------------------

OLD_SYNC_TITLE = (
    "3. Build the `ExerciseSessionRecord` itself: `startTime`/`endTime` with\n"
    "   correct `ZoneOffset`s (via `zoneRules.getOffset(instant)`), the mapped\n"
    "   `exerciseType`, the (possibly localized) `title`, and\n"
    "   `bitlutWorkoutMetadata(\"exercise\", ...)` — `Metadata.activelyRecorded`\n"
)
NEW_SYNC_TITLE = (
    "3. Build the `ExerciseSessionRecord` itself: `startTime`/`endTime` with\n"
    "   correct `ZoneOffset`s (via `zoneRules.getOffset(instant)`), the mapped\n"
    "   `exerciseType`, the `title` (Huawei's own name when present, else an\n"
    "   **English-only** fallback since 2026-09-16 — see 4.8), and\n"
    "   `bitlutWorkoutMetadata(\"exercise\", ...)` — `Metadata.activelyRecorded`\n"
)


# --- SESSION_HANDOFF.md ----------------------------------------------------

HANDOFF_ANCHOR = (
    "- 2026-09-16 downstream-churn follow-up: removed the recurring 7-day "
    "`StepsRecord` time-range delete that was deleting/recreating "
    "workout-scoped Steps every 30 minutes; daily Huawei totals now keep "
    "stable per-day versions, and Health Connect binder/IPC failures abort "
    "remaining writes and wait for WorkManager backoff instead of three "
    "rapid full-pipeline retries. Workout session serialization/metadata "
    "is unchanged.\n"
)
HANDOFF_NEW_WITH_ANCHOR = (
    HANDOFF_ANCHOR +
    "- 2026-09-16 (b) fallback-title language experiment: workout titles "
    "written to Health Connect (fallback only, used when Huawei supplies "
    "no name of its own) now always resolve in English via "
    "`HuaweiWorkoutTypeMapper.exportDisplayName()`, instead of following "
    "the device/app locale via `localizedDisplayName()`. Trigger: Paulo "
    "observed BitLut's fallback workout titles switched from English to "
    "Russian around the same time the corporate reader's \"binder died\" "
    "import failures began. Not yet confirmed as the root cause -- see "
    "`docs/BACKLOG.md`. Revert by pointing the two call sites "
    "(`HuaweiHealthManager.kt`, `HuaweiExportParser.kt`) back at "
    "`localizedDisplayName()`. BitLut's own dashboard display is "
    "untouched; it never called either function.\n"
)
HANDOFF_UNIQUE_MARKER = "fallback-title language experiment"


# --- docs/BACKLOG.md --------------------------------------------------------

BACKLOG_ITEM_ANCHOR = (
    "- **Open verification: corporate wellness app sync failures (\"binder "
    "died\" / rate-limit errors after ~2 minutes), reported late "
    "August/early September 2026.** In addition to the Google Health 5.05 "
    "connection regression (fixed in 5.07), code review found a concrete "
    "BitLut churn amplifier: every 30-minute daily-step reconcile deleted "
    "all BitLut `StepsRecord`s across the 7-day Huawei window, including "
    "workout-scoped Steps introduced on 2026-08-30, then recreated them. "
    "The 2026-09-16 v2 fix removes that range delete, gives unchanged "
    "daily totals stable versions, and defers Health Connect binder "
    "failures to WorkManager backoff. Phone verification is still "
    "required before calling this incident resolved; do not change "
    "workout serialization/metadata meanwhile.\n"
)
BACKLOG_ITEM_NEW_WITH_ANCHOR = (
    BACKLOG_ITEM_ANCHOR +
    "- **New candidate cause added to the same open investigation "
    "(2026-09-16 (b)): fallback workout-title language.** Paulo observed "
    "the corporate reader's failures coincide with BitLut's fallback "
    "workout titles (used only when Huawei supplies no name) switching "
    "from English to Russian text. As an experiment, "
    "`HuaweiWorkoutTypeMapper.exportDisplayName()` now always writes "
    "English fallback titles to Health Connect regardless of device "
    "locale, while the existing `localizedDisplayName()` (dashboard-only) "
    "is unchanged. Not yet confirmed -- awaiting a real-device retest with "
    "the corporate reader. If this does not resolve the failures, revert "
    "the two call sites in `HuaweiHealthManager.kt`/`HuaweiExportParser.kt` "
    "back to `localizedDisplayName()`.\n"
)
BACKLOG_UNIQUE_MARKER = "fallback workout-title language"

OLD_BACKLOG_DATE = "# BitLut Backlog\n\nUpdated: 2026-09-16\n"
NEW_BACKLOG_DATE = "# BitLut Backlog\n\nUpdated: 2026-09-16 (b)\n"


# --- CHANGELOG.md -----------------------------------------------------------

CHANGELOG_ANCHOR = "# Changelog\n\n## 2026-09-16 -- Health Connect downstream change-churn hardening\n"
CHANGELOG_NEW_WITH_ANCHOR = (
    "# Changelog\n\n"
    "## 2026-09-16 (b) -- experiment: English-only fallback workout titles\n\n"
    "- **New candidate cause for the open corporate-reader \"binder died\" "
    "investigation** (`docs/BACKLOG.md`): fallback workout titles written "
    "to Health Connect -- used only when Huawei supplies no name of its "
    "own -- previously came from "
    "`HuaweiWorkoutTypeMapper.localizedDisplayName()`, which resolves via "
    "the app's active device locale (Russian on a Russian-locale device, "
    "English otherwise). Paulo observed the corporate reader's import "
    "failures coincide with BitLut's own fallback titles switching from "
    "English to Russian text.\n"
    "- **Added `HuaweiWorkoutTypeMapper.exportDisplayName()`**, which "
    "resolves the same `displayNameRes` string table pinned to "
    "`Locale.ENGLISH` via `createConfigurationContext`, regardless of "
    "device locale. `HuaweiHealthManager.kt` and `HuaweiExportParser.kt` "
    "(live sync and archive import, the two Health-Connect-write call "
    "sites) now call this instead of `localizedDisplayName()`.\n"
    "- **`localizedDisplayName()` itself is unchanged** and is not called "
    "anywhere in the UI layer -- BitLut's own dashboard display is "
    "unaffected by this change either way.\n"
    "- **This is an experiment, not a confirmed fix.** No corporate-app-side "
    "log yet confirms non-Latin `ExerciseSessionRecord.title` text as the "
    "actual cause. If a real-device retest with the corporate reader does "
    "not resolve the failures, revert by pointing both call sites back at "
    "`localizedDisplayName()`.\n\n"
    "## 2026-09-16 -- Health Connect downstream change-churn hardening\n"
)
CHANGELOG_UNIQUE_MARKER = "experiment: English-only fallback workout titles"


def main() -> None:
    print("=== 1/7: HuaweiWorkoutTypeMapper.kt -- add Configuration import ===")
    apply_edit(
        MAPPER_FILE,
        old=OLD_MAPPER_IMPORTS,
        new=NEW_MAPPER_IMPORTS,
        expected_old_count=1,
        expected_new_count=1,
        description="HuaweiWorkoutTypeMapper.kt: import android.content.res.Configuration",
    )

    print("=== 2/7: HuaweiWorkoutTypeMapper.kt -- add exportDisplayName() ===")
    apply_edit(
        MAPPER_FILE,
        old=OLD_MAPPER_TAIL,
        new=NEW_MAPPER_TAIL,
        expected_old_count=1,
        expected_new_count=1,
        description="HuaweiWorkoutTypeMapper.kt: add exportDisplayName() (English-pinned fallback title)",
    )

    print("=== 3/7: HuaweiHealthManager.kt -- switch call site ===")
    apply_edit(
        HUAWEI_MANAGER_FILE,
        old=OLD_HHM_CALL,
        new=NEW_HHM_CALL,
        expected_old_count=1,
        expected_new_count=1,
        description="HuaweiHealthManager.kt: use exportDisplayName() for live-sync fallback title",
    )

    print("=== 4/7: HuaweiExportParser.kt -- switch call site ===")
    apply_edit(
        EXPORT_PARSER_FILE,
        old=OLD_PARSER_CALL,
        new=NEW_PARSER_CALL,
        expected_old_count=1,
        expected_new_count=1,
        description="HuaweiExportParser.kt: use exportDisplayName() for archive-import fallback title",
    )

    print("=== 5/7: sync.md section 4.6 ===")
    apply_edit(
        SYNC_FILE,
        old=OLD_SYNC_TITLE,
        new=NEW_SYNC_TITLE,
        expected_old_count=1,
        expected_new_count=1,
        description="sync.md: correct 'possibly localized' title description in section 4.6",
    )

    print("=== 6/7: SESSION_HANDOFF.md, docs/BACKLOG.md, CHANGELOG.md ===")
    apply_insertion(
        HANDOFF_FILE,
        anchor=HANDOFF_ANCHOR,
        new_with_anchor=HANDOFF_NEW_WITH_ANCHOR,
        unique_marker=HANDOFF_UNIQUE_MARKER,
        description="SESSION_HANDOFF.md: document the fallback-title language experiment",
    )
    apply_insertion(
        BACKLOG_FILE,
        anchor=BACKLOG_ITEM_ANCHOR,
        new_with_anchor=BACKLOG_ITEM_NEW_WITH_ANCHOR,
        unique_marker=BACKLOG_UNIQUE_MARKER,
        description="docs/BACKLOG.md: add fallback-title candidate cause to the open investigation",
    )
    apply_edit(
        BACKLOG_FILE,
        old=OLD_BACKLOG_DATE,
        new=NEW_BACKLOG_DATE,
        expected_old_count=1,
        expected_new_count=1,
        description="docs/BACKLOG.md: bump Updated date",
    )
    apply_insertion(
        CHANGELOG_FILE,
        anchor=CHANGELOG_ANCHOR,
        new_with_anchor=CHANGELOG_NEW_WITH_ANCHOR,
        unique_marker=CHANGELOG_UNIQUE_MARKER,
        description="CHANGELOG.md: add 2026-09-16 (b) entry",
    )

    print("=== 7/7: compile gate ===")
    run_compile_gate()

    print("=== Compile gate passed. Committing and pushing. ===")
    git_commit_and_push()

    print("Done.")


if __name__ == "__main__":
    main()
