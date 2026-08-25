#!/usr/bin/env python3
"""
BitLut patch v9: fix Health Connect records so third-party reader apps
recognize them as trustworthy, real activity data.

Context (2026-08-25 sprint):
  BitLut's core job is HUAWEI Health -> BitLut -> Google Health Connect.
  A corporate fitness app that reads from Health Connect was not importing
  BitLut-synced workouts (e.g. a cycling session), even though the same
  workout displayed correctly in Google Fit / Health Connect's own UI after
  passing through the full Huawei -> BitLut -> Health Connect chain.

Root cause:
  Every record BitLut writes (steps, distance, floors, elevation, active
  calories, exercise sessions) got its Metadata via `bitlutDailyStepMetadata()`
  or `bitlutMetadata()` in GoogleHealthManager.kt. Both called the raw
  `Metadata(clientRecordId = ..., clientRecordVersion = ...)` constructor
  without a recording method. Health Connect's own Metadata contract
  (see androidx.health.connect:connect-client's Metadata requirements docs)
  defaults `recordingMethod` to `RECORDING_METHOD_UNKNOWN` unless one of the
  factory methods (`Metadata.manualEntry()`, `Metadata.autoRecorded()`,
  `Metadata.activelyRecorded()`) is used instead.

  Health Connect's own UI and Google Fit display RECORDING_METHOD_UNKNOWN
  records without filtering by recording method, which is exactly why the
  cycling workout looked fine there. A third-party reader app is free to
  filter or distrust RECORDING_METHOD_UNKNOWN data as a data-quality signal,
  which matches the reported symptom precisely: visible in Google Fit,
  invisible in the corporate app, same underlying Health Connect record.

Fix:
  Both metadata factory functions now call `Metadata.autoRecorded(...)`
  instead of the raw constructor, setting `recordingMethod =
  RECORDING_METHOD_AUTOMATICALLY_RECORDED`. This is the semantically correct
  category: BitLut relays activity data that a device (phone or wearable)
  already recorded via Huawei Health -- it is not user-typed (manualEntry)
  and BitLut is not itself the live-recording sensor (activelyRecorded).
  `Device(type = Device.TYPE_UNKNOWN)` is used deliberately rather than a
  guessed manufacturer/model, since BitLut runs on the phone relaying data
  Huawei Health already attributed to whichever device actually recorded it
  -- BitLut has no reliable device-type signal of its own to add.

  This is a data-correctness fix, not a UI change: no new Health Connect or
  Huawei permissions are added, no historical-sync window is touched, and
  the existing clientRecordId/clientRecordVersion upsert/dedup strategy is
  unchanged -- only the recording method + device fields are added to the
  same Metadata objects already being written.

Verified against Health Connect Jetpack SDK docs for the exact dependency
version already pinned in app/build.gradle.kts (connect-client:1.1.0-alpha11):
Metadata.autoRecorded(clientRecordId, clientRecordVersion, device) and the
Device class (with Device.TYPE_UNKNOWN) are both public in this version --
this is not a version bump, just switching from the deprecated raw
constructor to the documented factory method already available.

Files touched:
  - app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt
    (adds Device import; adds a shared bitlutRecordingDevice constant;
    bitlutDailyStepMetadata() and bitlutMetadata() now call
    Metadata.autoRecorded(...) instead of the raw Metadata(...) constructor)

Usage:
    python3 patch_hc_recording_method_v9.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / "hc_recording_method_v9"


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
    manager_path = ROOT / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt"

    if not manager_path.exists():
        die(f"Required file missing: {manager_path}")

    print("== Step 1/3: GoogleHealthManager.kt -- import Device ==")
    apply_edit(
        manager_path,
        old="import androidx.health.connect.client.records.metadata.DataOrigin\n"
            "import androidx.health.connect.client.records.metadata.Metadata",
        new="import androidx.health.connect.client.records.metadata.DataOrigin\n"
            "import androidx.health.connect.client.records.metadata.Device\n"
            "import androidx.health.connect.client.records.metadata.Metadata",
    )

    print("== Step 2/3: GoogleHealthManager.kt -- bitlutDailyStepMetadata() uses autoRecorded ==")
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
     * Connect's own `Metadata(...)` constructor defaults `recordingMethod` to
     * `RECORDING_METHOD_UNKNOWN` unless a factory method says otherwise, and
     * that was the value every BitLut record carried before this fix (see
     * [bitlutDailyStepMetadata] and [bitlutMetadata] below, which previously
     * called the raw constructor). Health Connect's own UI and Google Fit
     * display RECORDING_METHOD_UNKNOWN records without filtering, which is
     * why they showed up correctly there -- but a third-party reader app is
     * free to treat RECORDING_METHOD_UNKNOWN as untrustworthy and skip
     * importing it, which matches a real corporate-app report of BitLut's
     * synced workouts being invisible there despite being visible in Google
     * Fit. `Device(type = Device.TYPE_UNKNOWN)` is used rather than guessing
     * a manufacturer/model: BitLut runs on the phone relaying data that
     * Huawei Health already attributed to whatever wearable or phone
     * actually recorded it, so BitLut has no reliable device-type signal of
     * its own to report.
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

    print("== Step 3/3: verify recordingMethod fix is present ==")
    text = read(manager_path)
    import re

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
    print("  verified: no raw Metadata(...) constructor calls remain")

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
            "Fix Health Connect records missing recording method so third-party "
            "readers recognize BitLut-synced activity data",
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
