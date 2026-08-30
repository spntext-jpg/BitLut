#!/usr/bin/env python3
"""
patch_sync_status_indicator_v1.py

Adds a background-sync status line under the existing "last sync" text on
the Today screen header, with a fade-in / fade-out transition (2026-08-29).

Context: SyncUiState.isSyncing already exists and is already flipped by
SyncViewModel.markSyncStarted()/markSyncCompleted() around every real sync
attempt (manual "Sync now", the navbar Refresh button, and periodic
WorkManager runs that call back into the same view model). Nothing in the
UI ever read isSyncing before this patch -- it was tracked but never
rendered. This patch is UI-only: no sync/orchestration/permission logic is
touched.

Changes:
  1. FinalBitLutShell.kt
     - New imports: androidx.compose.animation.AnimatedVisibility, fadeIn,
       fadeOut (animateFloatAsState was already imported; these were not).
     - SummaryScreen() gains an `isSyncing: Boolean = false` parameter,
       passed from FinalBitLutShell's existing `syncState.isSyncing`.
     - MinimalHeader() gains an `isSyncing: Boolean = false` parameter and
       renders the "Updating..." line itself, wrapped in AnimatedVisibility
       (fadeIn/fadeOut, AugustMotion.MediumMs + StandardEasing -- the same
       duration/easing tokens already used for existing press animations
       in this file) so the line fades in when a sync starts and fades out
       (rather than snapping) when it completes.
     - Uses the existing R.string.sync_status_updating resource (added by
       this same patch) rather than a hardcoded literal.
  2. res/values/strings.xml / res/values-ru/strings.xml
     - New string `sync_status_updating`, added to both locales in the same
       patch to preserve EN/RU key parity.

Idempotency: every text edit is checked by exact-occurrence count (genuine
replacements) or by a unique marker string that only exists in the newly
inserted text (pure insertions) before being applied; a second run finds
everything already in place and skips every step.

Usage (run from repo root, inside GitHub Codespaces):
    python3 patch_sync_status_indicator_v1.py
"""

import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SHELL_FILE = REPO_ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
STRINGS_EN = REPO_ROOT / "app/src/main/res/values/strings.xml"
STRINGS_RU = REPO_ROOT / "app/src/main/res/values-ru/strings.xml"
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"


def die(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def backup(path: Path) -> None:
    if not path.exists():
        die(f"Expected file not found: {path}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    target = BACKUP_DIR / (path.name + ".bak_sync_status_indicator_v1")
    if not target.exists():
        shutil.copy2(path, target)
        print(f"Backed up {path} -> {target}")


def apply_insertion(path: Path, anchor: str, new_with_anchor: str, unique_marker: str, description: str) -> bool:
    """Pure insertion: `anchor` itself survives unchanged in the result, so
    idempotency must be keyed on `unique_marker` (text that exists only in
    the newly inserted content), never on the anchor's own occurrence count."""
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


def add_string_resource(path: Path, after_name: str, new_name: str, new_value: str, description: str) -> bool:
    """Inserts a <string name="new_name">...</string> immediately after the
    <string name="after_name">...</string> line. Idempotent on new_name's
    presence."""
    text = path.read_text(encoding="utf-8")
    marker = f'<string name="{new_name}">'
    if marker in text:
        print(f"SKIP (already applied): {description}")
        return False

    anchor_pattern = f'<string name="{after_name}">'
    if text.count(anchor_pattern) != 1:
        die(f"Could not find unique anchor string '{after_name}' in {path}")

    lines = text.splitlines(keepends=True)
    anchor_line_index = None
    for i, line in enumerate(lines):
        if anchor_pattern in line and line.strip().startswith("<string"):
            anchor_line_index = i
            break
    if anchor_line_index is None:
        die(f"Could not locate anchor line for '{after_name}' in {path}")

    indent = lines[anchor_line_index][: len(lines[anchor_line_index]) - len(lines[anchor_line_index].lstrip())]
    new_line = f'{indent}<string name="{new_name}">{new_value}</string>\n'
    lines.insert(anchor_line_index + 1, new_line)
    path.write_text("".join(lines), encoding="utf-8")
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
        die(
            "EN/RU string key parity broken after patch. "
            f"EN-only: {sorted(only_en)} RU-only: {sorted(only_ru)}"
        )
    print(f"strings.xml EN/RU parity OK ({len(en_names)} keys each).")


def main() -> None:
    backup(SHELL_FILE)
    backup(STRINGS_EN)
    backup(STRINGS_RU)

    changed = False

    # 1) New animation imports.
    changed |= apply_insertion(
        SHELL_FILE,
        anchor="import androidx.compose.animation.core.animateFloatAsState\n",
        new_with_anchor=(
            "import androidx.compose.animation.core.animateFloatAsState\n"
            "import androidx.compose.animation.AnimatedVisibility\n"
            "import androidx.compose.animation.fadeIn\n"
            "import androidx.compose.animation.fadeOut\n"
        ),
        unique_marker="import androidx.compose.animation.AnimatedVisibility",
        description="add AnimatedVisibility/fadeIn/fadeOut imports",
    ) or changed

    # 2) Thread isSyncing into SummaryScreen's call site.
    changed |= apply_insertion(
        SHELL_FILE,
        anchor=(
            "                MainTab.Today -> SummaryScreen(\n"
            "                    palette, dashboardState, syncState.selectedDataSource, onRefresh, wrappedOnRequestGoogle,\n"
            "                    onEditLayout = { showCardLayoutEditor = true },\n"
            "                    cardLayoutVersion = cardLayoutVersion\n"
            "                )"
        ),
        new_with_anchor=(
            "                MainTab.Today -> SummaryScreen(\n"
            "                    palette, dashboardState, syncState.selectedDataSource, onRefresh, wrappedOnRequestGoogle,\n"
            "                    onEditLayout = { showCardLayoutEditor = true },\n"
            "                    cardLayoutVersion = cardLayoutVersion,\n"
            "                    isSyncing = syncState.isSyncing\n"
            "                )"
        ),
        unique_marker="isSyncing = syncState.isSyncing",
        description="pass syncState.isSyncing into SummaryScreen()",
    ) or changed

    # 3) SummaryScreen() signature gains isSyncing param.
    changed |= apply_insertion(
        SHELL_FILE,
        anchor=(
            "    onEditLayout: () -> Unit,\n"
            "    cardLayoutVersion: Int\n"
            ") {\n"
            "    val context = LocalContext.current\n"
            "    val orderedCards = remember(cardLayoutVersion) {"
        ),
        new_with_anchor=(
            "    onEditLayout: () -> Unit,\n"
            "    cardLayoutVersion: Int,\n"
            "    isSyncing: Boolean = false\n"
            ") {\n"
            "    val context = LocalContext.current\n"
            "    val orderedCards = remember(cardLayoutVersion) {"
        ),
        unique_marker="isSyncing: Boolean = false\n) {\n    val context = LocalContext.current",
        description="add isSyncing parameter to SummaryScreen()",
    ) or changed

    # 4) MinimalHeader() call site inside SummaryScreen passes isSyncing.
    changed |= apply_insertion(
        SHELL_FILE,
        anchor=(
            "                trailing = formatDashboardSourceStatus(\n"
            "                    source = dataSource,\n"
            "                    lastUpdatedAtMs = state.lastUpdatedAtMs,\n"
            "                    isFromCache = state.isFromCache\n"
            "                ),\n"
            "                onEditClick = onEditLayout"
        ),
        new_with_anchor=(
            "                trailing = formatDashboardSourceStatus(\n"
            "                    source = dataSource,\n"
            "                    lastUpdatedAtMs = state.lastUpdatedAtMs,\n"
            "                    isFromCache = state.isFromCache\n"
            "                ),\n"
            "                // Background-sync indicator (2026-08-29): a second status\n"
            "                // line under the last-sync trailing text, shown only while\n"
            "                // SyncUiState.isSyncing is true. This is a UI-only read of\n"
            "                // pre-existing state -- SyncViewModel.markSyncStarted()/\n"
            "                // markSyncCompleted() already flip isSyncing around every\n"
            "                // real sync attempt (manual \"Sync now\", the navbar Refresh\n"
            "                // action, and periodic WorkManager runs that call back into\n"
            "                // the same view model); this patch is the first thing that\n"
            "                // actually renders it anywhere.\n"
            "                isSyncing = isSyncing,\n"
            "                onEditClick = onEditLayout"
        ),
        unique_marker="Background-sync indicator (2026-08-29)",
        description="pass isSyncing into MinimalHeader() call in SummaryScreen",
    ) or changed

    # 5) MinimalHeader() signature gains isSyncing param.
    changed |= apply_insertion(
        SHELL_FILE,
        anchor=(
            "    subtitle: String? = null,\n"
            "    trailing: String? = null,\n"
            "    onEditClick: (() -> Unit)? = null\n"
            ") {\n"
            "    Column(modifier = Modifier.fillMaxWidth()) {"
        ),
        new_with_anchor=(
            "    subtitle: String? = null,\n"
            "    trailing: String? = null,\n"
            "    isSyncing: Boolean = false,\n"
            "    onEditClick: (() -> Unit)? = null\n"
            ") {\n"
            "    Column(modifier = Modifier.fillMaxWidth()) {"
        ),
        unique_marker="isSyncing: Boolean = false,\n    onEditClick: (() -> Unit)? = null",
        description="add isSyncing parameter to MinimalHeader()",
    ) or changed

    # 6) MinimalHeader() body renders the new AnimatedVisibility status
    #    line, right after the trailing/edit-button Row and before the
    #    existing subtitle block.
    changed |= apply_insertion(
        SHELL_FILE,
        anchor=(
            "                }\n"
            "            }\n"
            "        }\n"
            "        if (subtitle != null) {\n"
            "            Spacer(Modifier.height(4.dp))\n"
            "            Text(\n"
            "                text = subtitle,\n"
            "                color = palette.secondaryText,\n"
            "                fontWeight = FontWeight.SemiBold,\n"
            "                fontSize = 13.sp,\n"
            "                modifier = Modifier.fillMaxWidth()\n"
            "            )\n"
            "        }\n"
            "    }\n"
            "}"
        ),
        new_with_anchor=(
            "                }\n"
            "            }\n"
            "        }\n"
            "        // Background-sync status (2026-08-29): a quiet second line, right\n"
            "        // under the last-sync trailing text, shown only while a sync is\n"
            "        // actually in flight. AnimatedVisibility fades it in on\n"
            "        // isSyncing=true and fades it out (rather than snapping) once\n"
            "        // markSyncCompleted() flips isSyncing back to false, per product\n"
            "        // request. Uses the Tangerine \"active\" accent (already the navbar\n"
            "        // Refresh action's color) rather than introducing a new token.\n"
            "        AnimatedVisibility(\n"
            "            visible = isSyncing,\n"
            "            enter = fadeIn(animationSpec = tween(AugustMotion.MediumMs, easing = AugustMotion.StandardEasing)),\n"
            "            exit = fadeOut(animationSpec = tween(AugustMotion.MediumMs, easing = AugustMotion.StandardEasing))\n"
            "        ) {\n"
            "            Column {\n"
            "                Spacer(Modifier.height(2.dp))\n"
            "                Text(\n"
            "                    text = stringResource(R.string.sync_status_updating),\n"
            "                    color = AugustColor.Tangerine,\n"
            "                    fontWeight = FontWeight.Bold,\n"
            "                    fontSize = 11.sp,\n"
            "                    maxLines = 1,\n"
            "                    modifier = Modifier.fillMaxWidth()\n"
            "                )\n"
            "            }\n"
            "        }\n"
            "        if (subtitle != null) {\n"
            "            Spacer(Modifier.height(4.dp))\n"
            "            Text(\n"
            "                text = subtitle,\n"
            "                color = palette.secondaryText,\n"
            "                fontWeight = FontWeight.SemiBold,\n"
            "                fontSize = 13.sp,\n"
            "                modifier = Modifier.fillMaxWidth()\n"
            "            )\n"
            "        }\n"
            "    }\n"
            "}"
        ),
        unique_marker="Background-sync status (2026-08-29)",
        description="render animated sync status line inside MinimalHeader()",
    ) or changed

    # 7) New string resources, EN + RU, added in the same patch for parity.
    changed |= add_string_resource(
        STRINGS_EN,
        after_name="sync_now",
        new_name="sync_status_updating",
        new_value="Updating\u2026",
        description="add sync_status_updating to values/strings.xml",
    ) or changed

    changed |= add_string_resource(
        STRINGS_RU,
        after_name="sync_now",
        new_name="sync_status_updating",
        new_value="\u0418\u0434\u0451\u0442 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0435\u2026",
        description="add sync_status_updating to values-ru/strings.xml",
    ) or changed

    if not changed:
        print("Nothing to do: sync status indicator already applied.")
    else:
        print("All sync-status-indicator edits applied.")

    validate_strings_xml_parity()

    text = SHELL_FILE.read_text(encoding="utf-8")
    if text.count("{") != text.count("}"):
        die("Brace mismatch detected in FinalBitLutShell.kt after patch -- aborting before build.")

    print("patch_sync_status_indicator_v1.py: structural checks passed.")


if __name__ == "__main__":
    main()
