#!/usr/bin/env python3
"""
patch_navbar_sync_status_docs_v1.py

Documentation update for the 2026-08-29 navbar resize + animated
background-sync status indicator changes (see patch_navbar_resize_v1.py
and patch_sync_status_indicator_v1.py). Run this after those two scripts
so CHANGELOG.md / SESSION_HANDOFF.md / CONTEXT.md pass a fresh-session
smoke test against the current source.

Changes:
  - CHANGELOG.md: new dated section describing both UI changes.
  - SESSION_HANDOFF.md: two new bullets under "## UI decisions" recording
    the exact navbar ratios and the sync-status behavior, so a future
    session doesn't have to re-derive them from source.
  - CONTEXT.md: "## UI baseline" sentence extended with the same summary.

Usage (run from repo root, inside GitHub Codespaces):
    python3 patch_navbar_sync_status_docs_v1.py
"""

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
HANDOFF = REPO_ROOT / "SESSION_HANDOFF.md"
CONTEXT = REPO_ROOT / "CONTEXT.md"
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"


def die(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def backup(path: Path) -> None:
    if not path.exists():
        die(f"Expected file not found: {path}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    target = BACKUP_DIR / (path.name + ".bak_navbar_sync_status_docs_v1")
    if not target.exists():
        shutil.copy2(path, target)
        print(f"Backed up {path} -> {target}")


def apply_insertion(path: Path, anchor: str, new_with_anchor: str, unique_marker: str, description: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if unique_marker in text:
        print(f"SKIP (already applied): {description}")
        return False
    anchor_count = text.count(anchor)
    if anchor_count != 1:
        die(
            f"Anchor count mismatch for '{description}': expected exactly 1 "
            f"occurrence of anchor, found {anchor_count}. Refusing to guess."
        )
    text = text.replace(anchor, new_with_anchor, 1)
    path.write_text(text, encoding="utf-8")
    print(f"APPLIED: {description}")
    return True


def main() -> None:
    backup(CHANGELOG)
    backup(HANDOFF)
    backup(CONTEXT)

    changed = False

    changed |= apply_insertion(
        CHANGELOG,
        anchor="# Changelog\n\n## 2026-08-29 -- workout interoperability hardening, build/lint recovery, UI cleanup",
        new_with_anchor=(
            "# Changelog\n\n"
            "## 2026-08-29 (b) -- bottom navbar resize, animated background-sync status\n\n"
            "- Bottom navbar: Today/Settings destination buttons shrunk ~20% (button\n"
            "  height 58->46dp, icon 21/20->17/16dp, icon tile 30->24dp, tile radius\n"
            "  12->10dp); center Refresh (sync) button grown ~20% (60->72dp, icon\n"
            "  28->34dp). Both destination buttons remain identical to each other\n"
            "  (shared composable, `Modifier.weight(1f)`), preserving symmetry.\n"
            "- Today screen header: new \"Updating...\" status line under the existing\n"
            "  \"<source> - <last sync>\" text, shown only while a sync is actually in\n"
            "  flight (`SyncUiState.isSyncing`, already tracked but never rendered\n"
            "  before this patch). Fades in/out via `AnimatedVisibility` +\n"
            "  `fadeIn`/`fadeOut` (`AugustMotion.MediumMs` + `StandardEasing`, the same\n"
            "  tokens already used elsewhere in this file) rather than snapping.\n"
            "- New string resource `sync_status_updating`, EN + RU, parity preserved\n"
            "  (255 keys each locale).\n"
            "- Delivered as `patch_navbar_resize_v1.py` and\n"
            "  `patch_sync_status_indicator_v1.py`; both removed after verification per\n"
            "  standing process (one-off delivery scripts are not kept in the repo).\n\n"
            "## 2026-08-29 -- workout interoperability hardening, build/lint recovery, UI cleanup"
        ),
        unique_marker="## 2026-08-29 (b) -- bottom navbar resize, animated background-sync status",
        description="add CHANGELOG.md entry for navbar resize + sync status indicator",
    ) or changed

    changed |= apply_insertion(
        HANDOFF,
        anchor=(
            "- Dashboard-card visibility/order is handled only by `DashboardCardLayoutPrefs` from the pencil editor.\n"
            "- Settings exposes only the steps goal.\n"
        ),
        new_with_anchor=(
            "- Dashboard-card visibility/order is handled only by `DashboardCardLayoutPrefs` from the pencil editor.\n"
            "- Settings exposes only the steps goal.\n"
            "- Bottom navbar (2026-08-29): Today/Settings destination buttons are ~20% smaller than the center Refresh button (button height 46dp vs Refresh 72dp; destination icon 17/16dp vs Refresh icon 34dp), matching the exact ratios documented in `CHANGELOG.md`. The two destination buttons remain identical to each other; do not resize one without the other.\n"
            "- Today header shows an animated \"Updating...\" status line under the last-sync trailing text while `SyncUiState.isSyncing` is true (fades in/out via `AnimatedVisibility`, not a snap toggle). Driven entirely by existing `SyncViewModel.markSyncStarted()`/`markSyncCompleted()` state; no new sync logic was added for this.\n"
        ),
        unique_marker="Bottom navbar (2026-08-29): Today/Settings destination buttons are ~20% smaller",
        description="add SESSION_HANDOFF.md bullets for navbar resize + sync status indicator",
    ) or changed

    changed |= apply_insertion(
        CONTEXT,
        anchor=(
            "August colors remain unchanged. UI direction is quieter/content-first: flat outlined cards, "
            "restrained hero depth, pill buttons, 48 dp targets, restrained tween motion, one primary "
            "Settings action, no fake press animation on non-clickable cards."
        ),
        new_with_anchor=(
            "August colors remain unchanged. UI direction is quieter/content-first: flat outlined cards, "
            "restrained hero depth, pill buttons, 48 dp targets, restrained tween motion, one primary "
            "Settings action, no fake press animation on non-clickable cards. Bottom navbar: destination "
            "buttons ~20% smaller than the center Refresh button (46dp vs 72dp), symmetric between "
            "Today/Settings. Today header shows a fade in/out \"Updating...\" line while a sync is in "
            "progress."
        ),
        unique_marker="Today header shows a fade in/out \"Updating...\" line while a sync is in progress.",
        description="extend CONTEXT.md UI baseline sentence with navbar/sync-status summary",
    ) or changed

    if not changed:
        print("Nothing to do: docs already reflect navbar resize + sync status indicator.")
    else:
        print("All doc edits applied.")

    print("patch_navbar_sync_status_docs_v1.py: done.")


if __name__ == "__main__":
    main()
