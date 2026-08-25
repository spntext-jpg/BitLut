#!/usr/bin/env python3
"""
BitLut patch v11: fix Health Connect records so third-party reader apps
recognize them as trustworthy, real activity data.

Supersedes patch_hc_recording_method_v10.py.

What actually happened across v9 -> v10 -> this version:

  v9 correctly diagnosed the root cause (BitLut's records carry
  RECORDING_METHOD_UNKNOWN, which a third-party reader is free to distrust
  and skip) but used Metadata.autoRecorded(...), which doesn't exist on
  connect-client:1.1.0-alpha11 -- it was introduced in 1.1.0-alpha12.
  v9's edits landed on disk (Device import, the doc comment, the
  bitlutRecordingDevice constant, both functions rewritten to call
  Metadata.autoRecorded(...)) *before* v9 hit its own compile gate and died
  -- v9's die() correctly skipped commit/push, but by design it does not
  roll back file writes that already succeeded.

  v10 bumped build.gradle.kts to 1.1.0-alpha12 (correctly, and this landed),
  then tried to re-apply the same GoogleHealthManager.kt rewrite v9 already
  made. v10's Step 2 (Device import) correctly detected "already applied"
  and skipped. v10's Step 3 used one large ~20-line old/new anchor pair to
  both perform the edit *and* detect whether it was already applied; on the
  user's real file this large-block match came back as 0 occurrences of
  *both* the old and the new text, which should be structurally impossible
  if the visible content truly matches -- the most likely explanation is an
  invisible byte-level difference (trailing whitespace, line-ending
  variation, or similar) introduced somewhere in that ~20-line span,
  possibly during v9's partial run. A single large fragile anchor used for
  both idempotency-detection and editing is exactly the kind of thing that
  breaks silently this way, and it was a mistake to build Step 3 that way.

  This version (v11) does not try to guess or fix invisible bytes it cannot
  see. Instead it replaces the single large anchor with a set of small,
  independent, symptom-based checks -- each one verifying one fact about
  the file directly (does the raw constructor still exist for either
  function specifically, does autoRecorded already exist, does the device
  constant already exist) rather than requiring one exact multi-line match.
  Each fact is fixed independently if missing, and left alone if already
  correct. This is robust to whatever partial state v9/v10 left behind,
  without needing to know exactly what that state is byte-for-byte.

Root cause (unchanged, confirmed across three iterations now):
  bitlutDailyStepMetadata() and bitlutMetadata() in GoogleHealthManager.kt
  build every record's Metadata. If either still calls the raw
  Metadata(clientRecordId = ..., clientRecordVersion = ...) constructor,
  recordingMethod defaults to RECORDING_METHOD_UNKNOWN. Health Connect's own
  UI and Google Fit display RECORDING_METHOD_UNKNOWN records without
  filtering (why the cycling workout looked fine there), but a third-party
  reader app is free to filter or distrust RECORDING_METHOD_UNKNOWN data --
  matching the reported symptom precisely.

Fix (same end state as v10, reached more robustly):
  1. app/build.gradle.kts: connect-client 1.1.0-alpha11 -> 1.1.0-alpha12
     (the minimum version where Metadata.autoRecorded(...) and mandatory
     device-type exist). If v10 already applied this, this step no-ops.
  2. GoogleHealthManager.kt: ensure the Device import exists, ensure a
     shared `bitlutRecordingDevice` constant exists, and ensure both
     bitlutDailyStepMetadata() and bitlutMetadata() call
     Metadata.autoRecorded(..., device = bitlutRecordingDevice) rather than
     the raw Metadata(...) constructor. Each of these four facts is checked
     and fixed independently.

This is a data-correctness + dependency-version fix, not a UI change: no new
Health Connect or Huawei *permissions* are added, no historical-sync window
is touched, and the existing clientRecordId/clientRecordVersion upsert/dedup
strategy is unchanged.

Files touched:
  - app/build.gradle.kts
  - app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt

Usage:
    python3 patch_hc_recording_method_v11.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / "hc_recording_method_v11"


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


def backup_once(path: Path, already_backed_up: set) -> None:
    if path in already_backed_up:
        return
    relative = path.relative_to(ROOT)
    backup_path = BACKUP_DIR / relative
    if not backup_path.exists():
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_path)
        print(f"  backed up -> {backup_path.relative_to(ROOT)}")
    already_backed_up.add(path)


def read(path: Path) -> str:
    if not path.exists():
        die(f"Expected file not found: {path}")
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


_backed_up_paths: set = set()


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

    backup_once(path, _backed_up_paths)
    write(path, text.replace(old, new, expected_count))
    print(f"  applied: {path.name}")
    return True


def apply_insertion(path: Path, anchor: str, new_with_anchor: str) -> bool:
    """Pure insertion: anchor text itself is unchanged, something new sits
    next to it. Using apply_edit here would let the anchor survive as a
    substring of new_with_anchor, so a second run's exact-count check would
    still find it and re-insert -- apply_insertion checks for the *inserted*
    text's presence instead, independent of the anchor's own byte content.
    """
    text = read(path)
    if new_with_anchor in text:
        print(f"  already applied, skipping: {path.name} (insertion at anchor)")
        return False

    count_anchor = text.count(anchor)
    if count_anchor != 1:
        die(
            f"{path}: expected 1 occurrence of insertion anchor, found "
            f"{count_anchor}. Refusing to apply (ambiguous or stale)."
        )

    backup_once(path, _backed_up_paths)
    write(path, text.replace(anchor, new_with_anchor, 1))
    print(f"  applied: {path.name}")
    return True


def main() -> None:
    gradle_path = ROOT / "app/build.gradle.kts"
    manager_path = ROOT / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt"

    if not gradle_path.exists():
        die(f"Required file missing: {gradle_path}")
    if not manager_path.exists():
        die(f"Required file missing: {manager_path}")

    # ---- Step 1: gradle dependency bump ----
    print("== Step 1/5: app/build.gradle.kts -- bump connect-client to 1.1.0-alpha12 ==")
    gradle_text = read(gradle_path)
    if "connect-client:1.1.0-alpha12" in gradle_text:
        print("  already applied, skipping: build.gradle.kts (connect-client:1.1.0-alpha12)")
    elif "connect-client:1.1.0-alpha11" in gradle_text:
        apply_edit(
            gradle_path,
            old='implementation("androidx.health.connect:connect-client:1.1.0-alpha11")',
            new='implementation("androidx.health.connect:connect-client:1.1.0-alpha12")',
        )
    else:
        die(
            f"{gradle_path}: neither connect-client:1.1.0-alpha11 nor "
            "1.1.0-alpha12 found. Refusing to guess -- inspect the current "
            "dependency line manually."
        )

    # ---- Step 2: Device import ----
    print("== Step 2/5: GoogleHealthManager.kt -- import Device ==")
    text = read(manager_path)
    if re.search(r"^import androidx\.health\.connect\.client\.records\.metadata\.Device$", text, re.MULTILINE):
        print("  already applied, skipping: GoogleHealthManager.kt (Device import)")
    else:
        apply_insertion(
            manager_path,
            anchor="import androidx.health.connect.client.records.metadata.DataOrigin",
            new_with_anchor=(
                "import androidx.health.connect.client.records.metadata.DataOrigin\n"
                "import androidx.health.connect.client.records.metadata.Device"
            ),
        )

    # ---- Step 3: shared device constant ----
    print("== Step 3/5: GoogleHealthManager.kt -- bitlutRecordingDevice constant ==")
    text = read(manager_path)
    if "bitlutRecordingDevice" in text:
        print("  already applied, skipping: GoogleHealthManager.kt (bitlutRecordingDevice)")
    else:
        # Insert directly before bitlutDailyStepMetadata's function signature,
        # wherever that function currently starts -- independent of whatever
        # exact surrounding text/comments preceded it before this patch.
        anchor_match = re.search(
            r"( *)private fun bitlutDailyStepMetadata\(sourceId: String, version: Long\): Metadata \{",
            text,
        )
        if not anchor_match:
            die(
                f"{manager_path}: could not locate bitlutDailyStepMetadata() "
                "function signature to anchor the device-constant insertion."
            )
        indent = anchor_match.group(1)
        anchor_line = anchor_match.group(0)
        doc_and_const = (
            f"{indent}/**\n"
            f"{indent} * Sprint 2026-08-25: every BitLut-written record is device-sourced\n"
            f"{indent} * Huawei activity data relayed automatically -- never typed in by the\n"
            f"{indent} * user, and never actively recorded by BitLut itself as a live sensor.\n"
            f"{indent} * Health Connect's raw `Metadata(...)` constructor (as used on\n"
            f"{indent} * connect-client 1.1.0-alpha11, this project's previous version) left\n"
            f"{indent} * recordingMethod at its default of RECORDING_METHOD_UNKNOWN. Health\n"
            f"{indent} * Connect's own UI and Google Fit display RECORDING_METHOD_UNKNOWN\n"
            f"{indent} * records without filtering, which is why they showed up correctly\n"
            f"{indent} * there -- but a third-party reader app is free to treat\n"
            f"{indent} * RECORDING_METHOD_UNKNOWN as untrustworthy and skip importing it,\n"
            f"{indent} * matching a real corporate-app report of BitLut's synced workouts\n"
            f"{indent} * being invisible there despite being visible in Google Fit.\n"
            f"{indent} *\n"
            f"{indent} * `Metadata.autoRecorded(...)` (and the mandatory device-type field it\n"
            f"{indent} * requires) is only available starting connect-client 1.1.0-alpha12 --\n"
            f"{indent} * see the accompanying build.gradle.kts version bump in this same\n"
            f"{indent} * patch. `Device(type = Device.TYPE_UNKNOWN)` is used rather than\n"
            f"{indent} * guessing a manufacturer/model: BitLut runs on the phone relaying\n"
            f"{indent} * data that Huawei Health already attributed to whatever wearable or\n"
            f"{indent} * phone actually recorded it, so BitLut has no reliable device-type\n"
            f"{indent} * signal of its own to report.\n"
            f"{indent} */\n"
            f"{indent}private val bitlutRecordingDevice = Device(type = Device.TYPE_UNKNOWN)\n"
            f"\n"
            f"{anchor_line}"
        )
        apply_insertion(manager_path, anchor_line, doc_and_const)

    # ---- Step 4: bitlutDailyStepMetadata() uses autoRecorded ----
    print("== Step 4/5: bitlutDailyStepMetadata() -- use Metadata.autoRecorded ==")
    apply_edit(
        manager_path,
        old='''        return Metadata(
            clientRecordId = "bitlut_steps_daily_$safeSourceId",
            clientRecordVersion = version
        )''',
        new='''        return Metadata.autoRecorded(
            clientRecordId = "bitlut_steps_daily_$safeSourceId",
            clientRecordVersion = version,
            device = bitlutRecordingDevice
        )''',
    )

    # ---- Step 5: bitlutMetadata() uses autoRecorded ----
    print("== Step 5/5: bitlutMetadata() -- use Metadata.autoRecorded ==")
    apply_edit(
        manager_path,
        old='''    ): Metadata = Metadata(
        clientRecordId = generateRecordId(type, startTimeMs, endTimeMs, discriminator),
        clientRecordVersion = version
    )''',
        new='''    ): Metadata = Metadata.autoRecorded(
        clientRecordId = generateRecordId(type, startTimeMs, endTimeMs, discriminator),
        clientRecordVersion = version,
        device = bitlutRecordingDevice
    )''',
    )

    # ---- Verify end state (symptom-based, not anchor-based) ----
    print("\n== Verification: end state must have no raw Metadata(...) constructor calls ==")
    text = read(manager_path)
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
    if "bitlutRecordingDevice" not in text:
        die(f"Expected bitlutRecordingDevice constant not found in {manager_path.name} after patch.")
    if not re.search(r"^import androidx\.health\.connect\.client\.records\.metadata\.Device$", text, re.MULTILINE):
        die(f"Expected Device import not found in {manager_path.name} after patch.")
    gradle_text = read(gradle_path)
    if "connect-client:1.1.0-alpha12" not in gradle_text:
        die(f"Expected connect-client:1.1.0-alpha12 not found in {gradle_path.name} after patch.")
    print("  verified: no raw Metadata(...) constructor calls remain")
    print("  verified: Metadata.autoRecorded(...) is used")
    print("  verified: bitlutRecordingDevice constant present")
    print("  verified: Device import present")
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
        die("assembleDebug failed. No commit, no push. Fix the build and re-run this script.")

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
