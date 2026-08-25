#!/usr/bin/env python3
"""
BitLut patch v10: fix Health Connect records so third-party reader apps
recognize them as trustworthy, real activity data.

Supersedes patch_hc_recording_method_v9.py, which failed the real
:app:compileDebugKotlin build with:

    e: ... GoogleHealthManager.kt:1385:25 Unresolved reference 'autoRecorded'.
    e: ... GoogleHealthManager.kt:1398:28 Unresolved reference 'autoRecorded'.

v9's root-cause diagnosis (BitLut's records carry RECORDING_METHOD_UNKNOWN,
which a third-party reader app is free to distrust/skip) was correct and is
unchanged here. What was wrong in v9 was the assumption that
`Metadata.autoRecorded(...)` already existed on connect-client:1.1.0-alpha11,
this project's pinned version at the time. It does not: per Android's own
Health Connect Jetpack release notes and "Metadata requirements" guide,
`Metadata.autoRecorded()` / `.manualEntry()` / `.activelyRecorded()` /
`.unknownRecordingMethod()` and the mandatory-device-type requirement were
all introduced in connect-client 1.1.0-alpha12, not alpha11. alpha11's
Metadata has no recordingMethod-related factory methods at all, which is
exactly why the real compiler reported an unresolved reference -- v9's
sandbox-only verification (a codelab page that mentioned alpha11 in one line
while showing later-SDK API in its examples) missed this; the real Gradle
build caught what that check didn't.

Root cause (unchanged from v9):
  Every record BitLut writes (steps, distance, floors, elevation, active
  calories, exercise sessions) got its Metadata via `bitlutDailyStepMetadata()`
  or `bitlutMetadata()` in GoogleHealthManager.kt. Both called the raw
  `Metadata(clientRecordId = ..., clientRecordVersion = ...)` constructor,
  which leaves `recordingMethod` at `RECORDING_METHOD_UNKNOWN`. Health
  Connect's own UI and Google Fit display RECORDING_METHOD_UNKNOWN records
  without filtering by recording method (why the cycling workout looked fine
  there), but a third-party reader app is free to filter or distrust
  RECORDING_METHOD_UNKNOWN data -- matching the reported symptom precisely.

Fix (this version):
  1. Bump androidx.health.connect:connect-client from 1.1.0-alpha11 to
     1.1.0-alpha12 in app/build.gradle.kts -- the minimum version where
     Metadata.autoRecorded(...) and the Device-type requirement exist.
  2. Both metadata factory functions now call `Metadata.autoRecorded(...)`
     instead of the raw constructor, setting `recordingMethod =
     RECORDING_METHOD_AUTOMATICALLY_RECORDED` and a mandatory
     `Device(type = Device.TYPE_UNKNOWN)`. This is the semantically correct
     category: BitLut relays activity data a device already recorded via
     Huawei Health -- not user-typed (manualEntry) and not BitLut itself
     live-recording (activelyRecorded). TYPE_UNKNOWN is used deliberately
     rather than a guessed manufacturer/model, since BitLut runs on the
     phone relaying data Huawei Health already attributed to whichever
     device actually recorded it.

Verified against Health Connect's own "Metadata requirements" and Jetpack
release-notes pages, which explicitly state the 1.1.0-alpha12 boundary and
warn that upgrading past it requires exactly this Metadata-factory-method
change or the build will fail with a "Constructor internal error." The other
alpha12 changelog entries (blood-pressure validation, feature-availability
annotation, workout-planning doc fixes) do not touch the six record types
this file constructs (StepsRecord, DistanceRecord, FloorsClimbedRecord,
ElevationGainedRecord, ActiveCaloriesBurnedRecord, ExerciseSessionRecord) or
their field signatures -- the only relevant change at this version boundary
is the Metadata one already handled here.

Caveat that remains genuinely unverifiable in this sandbox: there is no real
Android SDK/Gradle/Kotlin compiler here, so this cannot be proven to compile
before your machine's real assembleDebug runs it (which this script gates
on). A dependency-version bump is a real, non-trivial change; if
assembleDebug fails, do not treat this diagnosis as wrong on that basis
alone -- send the new compiler output back before we try a third version.

This is a data-correctness + dependency-version fix, not a UI change: no new
Health Connect or Huawei *permissions* are added, no historical-sync window
is touched, and the existing clientRecordId/clientRecordVersion upsert/dedup
strategy is unchanged -- only the recording method + device fields are added
to the same Metadata objects already being written.

Files touched:
  - app/build.gradle.kts
    (connect-client 1.1.0-alpha11 -> 1.1.0-alpha12)
  - app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt
    (adds Device import; adds a shared bitlutRecordingDevice constant;
    bitlutDailyStepMetadata() and bitlutMetadata() now call
    Metadata.autoRecorded(...) instead of the raw Metadata(...) constructor)

Note: if you already ran patch_hc_recording_method_v9.py and it failed the
build (as reported), your working tree's GoogleHealthManager.kt is still in
its original, unpatched state -- v9 died before committing anything. This
script re-applies both anchor edits from that original state; it is not
designed to be layered on top of a partially-applied v9.

Usage:
    python3 patch_hc_recording_method_v10.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / "hc_recording_method_v10"


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


def backup(path: Path) -> None:
    relative = path.relative_to(ROOT)
    backup_path = BACKUP_DIR / relative
    if not backup_path.exists():
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_path)
        print(f"  backed up -> {backup_path.relative_to(ROOT)}")


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
            f"{path}: expected {expected_count} occurrence(s) of anchor, "
            f"found {count_old}. Refusing to apply (ambiguous or stale)."
        )

    backup(path)
    write(path, text.replace(old, new, expected_count))
    print(f"  applied: {path.name}")
    return True


def main() -> None:
    gradle_path = ROOT / "app/build.gradle.kts"
    manager_path = ROOT / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt"

    if not gradle_path.exists():
        die(f"Required file missing: {gradle_path}")
    if not manager_path.exists():
        die(f"Required file missing: {manager_path}")

    print("== Step 1/4: app/build.gradle.kts -- bump connect-client to 1.1.0-alpha12 ==")
    apply_edit(
        gradle_path,
        old='implementation("androidx.health.connect:connect-client:1.1.0-alpha11")',
        new='implementation("androidx.health.connect:connect-client:1.1.0-alpha12")',
    )

    print("== Step 2/4: GoogleHealthManager.kt -- import Device ==")
    apply_edit(
        manager_path,
        old="import androidx.health.connect.client.records.metadata.DataOrigin\n"
            "import androidx.health.connect.client.records.metadata.Metadata",
        new="import androidx.health.connect.client.records.metadata.DataOrigin\n"
            "import androidx.health.connect.client.records.metadata.Device\n"
            "import androidx.health.connect.client.records.metadata.Metadata",
    )

    print("== Step 3/4: GoogleHealthManager.kt -- bitlutDailyStepMetadata()/bitlutMetadata() use autoRecorded ==")
    apply_edit(
        manager_path,
        old='''    private fun bitlutDailyStepMetadata(sourceId: String, version: Long): Metadata {
        val safeSourceId = sourceId
            .replace(Regex("[^A-Za-z0-9_-]"), "_")
            .take(64)
        return Metadata(
            clientRecordId = "bitlut_steps_daily_$safeSourceId",
            clientRecordVersion = version
        )
    }

    private fun bitlutMetadata(
        type: String,
        startTimeMs: Long,
        endTimeMs: Long,
        discriminator: String = "",
        version: Long = 1L
    ): Metadata = Metadata(
        clientRecordId = generateRecordId(type, startTimeMs, endTimeMs, discriminator),
        clientRecordVersion = version
    )''',
        new='''    /**
     * Sprint 2026-08-25: every BitLut-written record is device-sourced Huawei
     * activity data relayed automatically -- never typed in by the user, and
     * never actively recorded by BitLut itself as a live sensor. Health
     * Connect's own `Metadata(...)` constructor (as used on connect-client
     * 1.1.0-alpha11, this project's previous version) left `recordingMethod`
     * at its default of `RECORDING_METHOD_UNKNOWN`, which is the value every
     * BitLut record carried before this fix (see [bitlutDailyStepMetadata]
     * and [bitlutMetadata] below, which previously called the raw
     * constructor). Health Connect's own UI and Google Fit display
     * RECORDING_METHOD_UNKNOWN records without filtering, which is why they
     * showed up correctly there -- but a third-party reader app is free to
     * treat RECORDING_METHOD_UNKNOWN as untrustworthy and skip importing it,
     * which matches a real corporate-app report of BitLut's synced workouts
     * being invisible there despite being visible in Google Fit.
     *
     * `Metadata.autoRecorded(...)` (and the mandatory device-type field it
     * requires) is only available starting connect-client 1.1.0-alpha12 --
     * see the accompanying build.gradle.kts version bump in this same patch.
     * `Device(type = Device.TYPE_UNKNOWN)` is used rather than guessing a
     * manufacturer/model: BitLut runs on the phone relaying data that Huawei
     * Health already attributed to whatever wearable or phone actually
     * recorded it, so BitLut has no reliable device-type signal of its own
     * to report.
     */
    private val bitlutRecordingDevice = Device(type = Device.TYPE_UNKNOWN)

    private fun bitlutDailyStepMetadata(sourceId: String, version: Long): Metadata {
        val safeSourceId = sourceId
            .replace(Regex("[^A-Za-z0-9_-]"), "_")
            .take(64)
        return Metadata.autoRecorded(
            clientRecordId = "bitlut_steps_daily_$safeSourceId",
            clientRecordVersion = version,
            device = bitlutRecordingDevice
        )
    }

    private fun bitlutMetadata(
        type: String,
        startTimeMs: Long,
        endTimeMs: Long,
        discriminator: String = "",
        version: Long = 1L
    ): Metadata = Metadata.autoRecorded(
        clientRecordId = generateRecordId(type, startTimeMs, endTimeMs, discriminator),
        clientRecordVersion = version,
        device = bitlutRecordingDevice
    )''',
    )

    print("== Step 4/4: verify recordingMethod fix is present ==")
    text = read(manager_path)
    # Match a real raw-constructor call: "Metadata(" preceded by neither an
    # identifier character (so "bitlutMetadata(" doesn't match) nor a "."
    # (so "Metadata.autoRecorded(" doesn't match), and not inside the
    # backtick-quoted doc-comment prose that mentions "Metadata(...)" as text.
    raw_ctor_pattern = re.compile(r"(?<![\w.`])Metadata\(")
    residual = [
        line for line in text.splitlines()
        if raw_ctor_pattern.search(line) and "`Metadata(" not in line
    ]
    if residual:
        die(
            "A raw Metadata(...) constructor call still exists in "
            f"{manager_path.name} after the patch -- investigate before building:\n"
            + "\n".join(residual)
        )
    if "Metadata.autoRecorded(" not in text:
        die(f"Expected Metadata.autoRecorded(...) not found in {manager_path.name} after patch.")
    gradle_text = read(gradle_path)
    if "connect-client:1.1.0-alpha12" not in gradle_text:
        die(f"Expected connect-client:1.1.0-alpha12 not found in {gradle_path.name} after patch.")
    print("  verified: no raw Metadata(...) constructor calls remain")
    print("  verified: connect-client pinned to 1.1.0-alpha12")

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
        die(
            "assembleDebug failed. No commit, no push. Fix the build and re-run this "
            "script, or send the new compiler output back before trying a third version -- "
            "see this script's module docstring for why a dependency-version bump can't be "
            "fully verified outside a real Gradle build."
        )

    print("\n== assembleDebug succeeded. Committing and pushing. ==")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    commit = subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "Bump Health Connect to 1.1.0-alpha12 and set recording method so "
            "third-party readers recognize BitLut-synced activity data",
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
