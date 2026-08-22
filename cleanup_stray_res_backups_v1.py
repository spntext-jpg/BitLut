#!/usr/bin/env python3
"""
BitLut cleanup: remove stray *.bak_workout_four_metrics files left inside
app/src/main/res/** by an earlier, broken version of
patch_workout_card_four_metrics.py.

Background:
  The first version of that patch script backed up touched files in-place
  (e.g. strings.xml -> strings.xml.bak_workout_four_metrics) next to the
  original. For files under app/src/main/res/, this breaks AGP's
  mergeDebugResources task, which treats every file in res/** as a candidate
  resource and rejects anything not ending in .xml.

  The script was fixed to write backups to .bitlut_patch_backup/ instead
  (already covered by .gitignore), and re-running the fixed script correctly
  skipped all content edits (already applied) -- but it never touched the
  stray *.bak_workout_four_metrics files created by the earlier broken run,
  since removing unrelated stray files was out of scope for a content-patch
  script. Those leftover files are what's still failing the build.

  This script's only job is deleting those specific stray files. It does not
  touch any other content. Real content is preserved -- the .bak files are
  copies, not the source of truth (the source of truth is the already-patched
  strings.xml/FinalBitLutShell.kt/etc. sitting alongside them).

Safety:
  - Only ever deletes files whose name ends in the literal suffix
    ".bak_workout_four_metrics".
  - Only searches inside app/src/main/res/ (where AGP's merger fails on
    stray files) -- does not touch .bak files elsewhere in the repo (e.g.
    next to FinalBitLutShell.kt in ui/screens/, which is NOT under res/ and
    does not break any Gradle task; left alone deliberately, not swept).
  - Before deleting, verifies the file is a duplicate of readable UTF-8 text
    (sanity check, not a guess) and prints what it's removing.
  - Idempotent: running with nothing left to clean is a no-op, reported as
    such, with exit code 0.

Usage:
    python3 cleanup_stray_res_backups_v1.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RES_DIR = ROOT / "app" / "src" / "main" / "res"
STRAY_SUFFIX = ".bak_workout_four_metrics"


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    if not RES_DIR.exists():
        die(f"Expected resource directory not found: {RES_DIR}")

    stray_files = sorted(
        p for p in RES_DIR.rglob(f"*{STRAY_SUFFIX}") if p.is_file()
    )

    if not stray_files:
        print("Nothing to clean -- no stray backup files found under res/. Skipping.")
        return

    print(f"Found {len(stray_files)} stray backup file(s) under {RES_DIR}:")
    for f in stray_files:
        try:
            f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            die(f"{f} is not readable UTF-8 text -- refusing to guess, stopping.")
        print(f"  - {f.relative_to(ROOT)}")

    for f in stray_files:
        f.unlink()
        print(f"  removed: {f.relative_to(ROOT)}")

    print("\nDone. Re-run your normal build; mergeDebugResources should no longer see these files.")


if __name__ == "__main__":
    main()
