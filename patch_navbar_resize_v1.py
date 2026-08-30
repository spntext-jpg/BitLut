#!/usr/bin/env python3
"""
patch_navbar_resize_v1.py

Bottom navbar sizing pass (2026-08-29):
  - Today / Settings destination buttons shrink ~20%.
  - Center Refresh (sync) button grows ~20%.
  - Proportions/symmetry preserved: both destination buttons share the same
    AugustDestination composable and Modifier.weight(1f) (unchanged), so
    they stay identical to each other; the icon-tile-to-button-height ratio
    and icon-tile corner-radius-to-size ratio are kept close to their
    original values instead of scaling only one dimension.

Exact scale applied (nearest clean dp value to +/-20%):
  destination height        58dp -> 46dp   (-20.7%)
  destination icon selected 21dp -> 17dp   (-19.0%)
  destination icon unselect 20dp -> 16dp   (-20.0%)
  icon tile size             30dp -> 24dp   (-20.0%)
  icon tile corner radius    12dp -> 10dp   (-16.7%, keeps tile shape close
                                              to the original ~0.40 ratio)
  refresh button size         60dp -> 72dp   (+20.0%)
  refresh icon size            28dp -> 34dp   (+21.4%)

Touches only app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt.
No Health Connect / Huawei permission, sync-window, or data-contract changes.

Usage (run from repo root, inside GitHub Codespaces):
    python3 patch_navbar_resize_v1.py
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
NAV_FILE = REPO_ROOT / "app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt"
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"


def die(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def backup(path: Path) -> None:
    if not path.exists():
        die(f"Expected file not found: {path}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    target = BACKUP_DIR / (path.name + ".bak_navbar_resize_v1")
    if not target.exists():
        shutil.copy2(path, target)
        print(f"Backed up {path} -> {target}")


def apply_edit(path: Path, old: str, new: str, expected_old_count: int, expected_new_count: int, description: str) -> bool:
    """Genuine replacement. Idempotent: if `old` is already absent and `new`
    is present the expected number of times, skip. Fails closed on any other
    mismatch rather than guessing."""
    text = path.read_text(encoding="utf-8")
    old_count = text.count(old)
    new_count = text.count(new)

    if old_count == 0 and new_count >= expected_new_count:
        print(f"SKIP (already applied): {description}")
        return False

    if old_count != expected_old_count:
        die(
            f"Anchor count mismatch for '{description}': expected {expected_old_count} "
            f"occurrence(s) of old text, found {old_count}. Refusing to guess."
        )

    text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print(f"APPLIED: {description}")
    return True


def main() -> None:
    backup(NAV_FILE)
    changed = False

    edits = [
        (
            "val iconShape = remember { RoundedCornerShape(12.dp) }",
            "val iconShape = remember { RoundedCornerShape(10.dp) }",
            "destination icon tile corner radius 12dp -> 10dp",
        ),
        (
            "targetValue = if (selected) 21.dp else 20.dp,",
            "targetValue = if (selected) 17.dp else 16.dp,",
            "destination icon size 21/20dp -> 17/16dp",
        ),
        (
            "    Column(\n        modifier = modifier\n            .height(58.dp)",
            "    Column(\n        modifier = modifier\n            .height(46.dp)",
            "destination button height 58dp -> 46dp",
        ),
        (
            "        Box(\n            modifier = Modifier\n                .size(30.dp)\n                .clip(iconShape)",
            "        Box(\n            modifier = Modifier\n                .size(24.dp)\n                .clip(iconShape)",
            "destination icon tile size 30dp -> 24dp",
        ),
        (
            "    Box(\n        modifier = Modifier\n            .size(60.dp)",
            "    Box(\n        modifier = Modifier\n            .size(72.dp)",
            "refresh button size 60dp -> 72dp",
        ),
        (
            "            modifier = Modifier\n                .size(28.dp)\n                .graphicsLayer { rotationZ = rotation }",
            "            modifier = Modifier\n                .size(34.dp)\n                .graphicsLayer { rotationZ = rotation }",
            "refresh icon size 28dp -> 34dp",
        ),
    ]

    for old, new, description in edits:
        if apply_edit(NAV_FILE, old, new, expected_old_count=1, expected_new_count=1, description=description):
            changed = True

    if not changed:
        print("Nothing to do: GlassNavigation.kt already at target sizes.")
    else:
        print("All navbar edits applied.")

    # Structural sanity: brace balance as a cheap corruption check before
    # handing off to the real compiler.
    text = NAV_FILE.read_text(encoding="utf-8")
    if text.count("{") != text.count("}"):
        die("Brace mismatch detected in GlassNavigation.kt after patch -- aborting before build.")

    print("patch_navbar_resize_v1.py: structural checks passed.")


if __name__ == "__main__":
    main()
