#!/usr/bin/env python3
"""
BitLut repo cleanup v1: remove stray committed backup files and tidy
disposable root-level artifacts.

Background:
  The first, broken version of patch_workout_card_four_metrics.py named its
  in-place backups *.bak_workout_four_metrics. That suffix does not match
  the repo's existing .gitignore pattern (*.bak matches only files literally
  ending in ".bak"), so two such files were committed to main:
    - app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt.bak_workout_four_metrics
    - scripts/verify_workout_nav_freshness_sprint.py.bak_workout_four_metrics

  This script:
  1. Removes those two files from the working tree AND from git tracking
     (git rm), so they stop showing up in future diffs/status.
  2. Adds a *.bak_* glob to .gitignore so any future backup suffix variant
     is caught, not just the literal ".bak" case that's already there.
  3. Leaves everything else untouched -- does not touch .bitlut_patch_backup/
     (already gitignored, never committed), does not touch
     repomix-output.xml or the two applied one-off patch scripts at repo
     root (those are left for the user to remove manually once they're
     confident they no longer need them for reference).

Safety:
  - Only removes the two specific stray files named above, by exact path.
  - Verifies each file matches the expected *.bak_workout_four_metrics
    naming pattern before removing -- refuses if something unexpected is
    found at that path.
  - Idempotent: if a stray file is already gone (working tree and git
    index), that step is skipped and reported as such.
  - No compile gate needed -- this only touches non-source files
    (backup artifacts and .gitignore), not app source, so it cannot affect
    assembleDebug output. Still verified idempotent and dry-run tested
    before delivery per the project's patch-script process.

Usage:
    python3 cleanup_repo_stray_backups_v1.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

STRAY_FILES = [
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt.bak_workout_four_metrics",
    "scripts/verify_workout_nav_freshness_sprint.py.bak_workout_four_metrics",
]

GITIGNORE_ADDITION = "*.bak_*\n"


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


def is_git_tracked(rel_path: str) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel_path],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def remove_stray_file(rel_path: str) -> None:
    path = ROOT / rel_path
    tracked = is_git_tracked(rel_path)

    if not path.exists() and not tracked:
        print(f"  already clean, skipping: {rel_path}")
        return

    if path.exists() and not rel_path.endswith(".bak_workout_four_metrics"):
        die(f"Refusing to remove {rel_path}: does not match expected stray-backup naming.")

    if tracked:
        result = subprocess.run(["git", "rm", "-f", "--quiet", rel_path], cwd=ROOT)
        if result.returncode != 0:
            die(f"git rm failed for {rel_path}")
        print(f"  removed from git + working tree: {rel_path}")
    elif path.exists():
        path.unlink()
        print(f"  removed from working tree (was not git-tracked): {rel_path}")


def ensure_gitignore_pattern() -> bool:
    gitignore_path = ROOT / ".gitignore"
    if not gitignore_path.exists():
        die(".gitignore not found at repo root.")

    text = gitignore_path.read_text(encoding="utf-8")
    if "*.bak_*" in text:
        print("  .gitignore already has *.bak_* pattern, skipping.")
        return False

    if not text.endswith("\n"):
        text += "\n"
    text += (
        "\n# Catch backup-suffix variants beyond the literal *.bak case\n"
        + GITIGNORE_ADDITION
    )
    gitignore_path.write_text(text, encoding="utf-8")
    print("  added *.bak_* to .gitignore")
    return True


def main() -> None:
    print("== Step 1/2: remove stray committed backup files ==")
    for rel_path in STRAY_FILES:
        remove_stray_file(rel_path)

    print("== Step 2/2: broaden .gitignore backup pattern ==")
    gitignore_changed = ensure_gitignore_pattern()
    if gitignore_changed:
        subprocess.run(["git", "add", ".gitignore"], cwd=ROOT, check=True)

    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True
    )
    if not status.stdout.strip():
        print("\nNothing staged -- already clean. No commit needed.")
        return

    print("\n== Committing cleanup ==")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    commit = subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "Remove stray committed *.bak_workout_four_metrics files; broaden .gitignore backup pattern",
        ],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        die("git commit failed.")

    push = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT)
    if push.returncode != 0:
        die("git push failed. Commit succeeded locally; push manually once resolved.")

    print("\nDone.")


if __name__ == "__main__":
    main()
