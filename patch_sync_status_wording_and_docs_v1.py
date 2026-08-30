#!/usr/bin/env python3
"""
patch_sync_status_wording_and_docs_v1.py

Two small follow-ups from the previous sprint's review (2026-08-29):

1. Wording tightening for the background-sync status line
   (`sync_status_updating`, added by patch_sync_status_indicator_v1.py).
   Note: the shipped RU string was already correctly capitalized
   ("Идёт обновление...", capital И) -- the lowercase "idyot" typo the
   reviewer saw was in chat prose, not in the resource file itself. Per
   the "modern, short, laconic" request this patch still tightens both
   locales to match this app's existing sync terminology:
     EN: "Updating..."       -> "Syncing..."       (matches "Sync now")
     RU: "Идёт обновление..." -> "Синхронизация..." (matches "Синхронизировать")

2. Documentation: adds a CHANGELOG.md entry for this sprint's three
   changes (Huawei workout summary sum fix, Settings engraved signature,
   this wording tightening) and a SESSION_HANDOFF.md bullet recording the
   Huawei aggregation fix, so a fresh session's smoke test reflects
   current source.

Run this AFTER patch_huawei_workout_summary_sum_v1.py and
patch_settings_engraved_signature_v1.py (order doesn't strictly matter
for correctness, but keeps the CHANGELOG narrative in a sensible order).

Usage (run from repo root, inside GitHub Codespaces):
    python3 patch_sync_status_wording_and_docs_v1.py
"""

import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
STRINGS_EN = REPO_ROOT / "app/src/main/res/values/strings.xml"
STRINGS_RU = REPO_ROOT / "app/src/main/res/values-ru/strings.xml"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
HANDOFF = REPO_ROOT / "SESSION_HANDOFF.md"
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"


def die(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def backup(path: Path) -> None:
    if not path.exists():
        die(f"Expected file not found: {path}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    target = BACKUP_DIR / (path.name + ".bak_sync_status_wording_and_docs_v1")
    if not target.exists():
        shutil.copy2(path, target)
        print(f"Backed up {path} -> {target}")


def apply_edit(path: Path, old: str, new: str, expected_old_count: int, description: str) -> bool:
    text = path.read_text(encoding="utf-8")
    old_count = text.count(old)
    new_count = text.count(new)
    if old_count == 0 and new_count > 0:
        print(f"SKIP (already applied): {description}")
        return False
    if old_count != expected_old_count:
        die(
            f"Anchor count mismatch for '{description}': expected {expected_old_count} "
            f"occurrence(s), found {old_count}. Refusing to guess."
        )
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print(f"APPLIED: {description}")
    return True


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


def validate_strings_xml_parity() -> None:
    try:
        en_root = ET.parse(STRINGS_EN).getroot()
        ru_root = ET.parse(STRINGS_RU).getroot()
    except ET.ParseError as e:
        die(f"strings.xml is not well-formed after patch: {e}")
    en_names = {el.get("name") for el in en_root.findall("string")}
    ru_names = {el.get("name") for el in ru_root.findall("string")}
    only_en = en_names - ru_names
    only_ru = ru_names - en_names
    if only_en or only_ru:
        die(f"EN/RU string key parity broken. EN-only: {sorted(only_en)} RU-only: {sorted(only_ru)}")
    print(f"strings.xml EN/RU parity OK ({len(en_names)} keys each).")


def main() -> None:
    backup(STRINGS_EN)
    backup(STRINGS_RU)
    backup(CHANGELOG)
    backup(HANDOFF)

    changed = False

    # 1) Tighten wording in both locales.
    changed |= apply_edit(
        STRINGS_EN,
        old='<string name="sync_status_updating">Updating\u2026</string>',
        new='<string name="sync_status_updating">Syncing\u2026</string>',
        expected_old_count=1,
        description="tighten EN sync status wording to 'Syncing...'",
    ) or changed

    changed |= apply_edit(
        STRINGS_RU,
        old='<string name="sync_status_updating">\u0418\u0434\u0451\u0442 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0435\u2026</string>',
        new='<string name="sync_status_updating">\u0421\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044f\u2026</string>',
        expected_old_count=1,
        description="tighten RU sync status wording to 'Синхронизация...'",
    ) or changed

    # 2) CHANGELOG entry for this sprint.
    changed |= apply_insertion(
        CHANGELOG,
        anchor="# Changelog\n\n## 2026-08-29 (b) -- bottom navbar resize, animated background-sync status",
        new_with_anchor=(
            "# Changelog\n\n"
            "## 2026-08-29 (c) -- Huawei workout summary fix, Settings signature, wording pass\n\n"
            "- Fixed a confirmed real-device bug: a walking workout showed a correct\n"
            "  2.5 km distance but only 250 steps. Root cause: Huawei splits\n"
            "  steps/calories/elevation across multiple sample points per activity,\n"
            "  and `HuaweiHealthManager.readActivityRecordSummary()` kept only the\n"
            "  first matching point instead of summing them (distance already summed\n"
            "  correctly via its existing fallback path, which masked the same bug\n"
            "  class for that one metric). Steps, calories, and elevation now sum all\n"
            "  matching points, consistent with distance.\n"
            "- Settings screen: new wood-carved-style signature at the very bottom\n"
            "  (`EngravedSignature()`), built from Inter Black + letter-spacing + a\n"
            "  two-layer engraved-shadow effect (no new font asset added -- see\n"
            "  CLAUDE.md's GMS-free/Downloadable-Fonts constraint). New string\n"
            "  `settings_signature`, EN + RU.\n"
            "- Tightened `sync_status_updating` wording for both locales to match\n"
            "  existing sync terminology: EN \"Updating...\" -> \"Syncing...\"; RU\n"
            "  \"\u0418\u0434\u0451\u0442 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0435...\" -> \"\u0421\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044f...\".\n"
            "- Delivered as `patch_huawei_workout_summary_sum_v1.py`,\n"
            "  `patch_settings_engraved_signature_v1.py`, and\n"
            "  `patch_sync_status_wording_and_docs_v1.py`; all removed after\n"
            "  verification per standing process.\n\n"
            "## 2026-08-29 (b) -- bottom navbar resize, animated background-sync status"
        ),
        unique_marker="## 2026-08-29 (c) -- Huawei workout summary fix, Settings signature, wording pass",
        description="add CHANGELOG.md entry for this sprint",
    ) or changed

    # 3) SESSION_HANDOFF.md bullet for the Huawei aggregation fix (the one
    #    future-session-relevant technical fact from this sprint; the
    #    signature and wording tweak are cosmetic and already fully
    #    described in CHANGELOG.md).
    changed |= apply_insertion(
        HANDOFF,
        anchor="- Today header shows an animated \"Updating...\" status line under the last-sync trailing text while `SyncUiState.isSyncing` is true (fades in/out via `AnimatedVisibility`, not a snap toggle). Driven entirely by existing `SyncViewModel.markSyncStarted()`/`markSyncCompleted()` state; no new sync logic was added for this.\n",
        new_with_anchor=(
            "- Today header shows an animated \"Syncing...\" status line under the last-sync trailing text while `SyncUiState.isSyncing` is true (fades in/out via `AnimatedVisibility`, not a snap toggle). Driven entirely by existing `SyncViewModel.markSyncStarted()`/`markSyncCompleted()` state; no new sync logic was added for this. Wording tightened 2026-08-29 (c) to \"Syncing...\"/\"Синхронизация...\".\n"
            "- Huawei per-activity summary aggregation (2026-08-29 (c)): `readActivityRecordSummary()` in `HuaweiHealthManager.kt` sums steps/calories/elevation across ALL matching sample points for an activity, not just the first. Do not revert to `firstOrNull()` for these fields -- Huawei can and does split them across multiple points per activity (confirmed on-device: a real walk showed 2.5 km distance but only 250 steps before this fix).\n"
        ),
        unique_marker="Huawei per-activity summary aggregation (2026-08-29 (c))",
        description="add SESSION_HANDOFF.md bullet for Huawei aggregation fix",
    ) or changed

    if not changed:
        print("Nothing to do: wording and docs already up to date.")
    else:
        print("Wording tightened and docs updated.")

    validate_strings_xml_parity()
    print("patch_sync_status_wording_and_docs_v1.py: done.")


if __name__ == "__main__":
    main()
