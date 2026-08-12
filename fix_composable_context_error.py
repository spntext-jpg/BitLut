#!/usr/bin/env python3
"""
Fix: "@Composable invocations can only happen from the context of a
@Composable function" at FinalBitLutShell.kt:564-565.

add_dashboard_card_layout_editor.py placed `LocalContext.current` and
`remember(cardLayoutVersion) { ... }` directly inside the LazyColumn's
content lambda, between two `item { }` blocks. That lambda is a
LazyListScope DSL body, not a normal @Composable context -- only the DSL
functions themselves (item, items, ...) are valid to call there directly;
arbitrary composable calls like LocalContext.current or remember() are not,
even though it looks like ordinary code. My mistake -- this only shows up
at compile time, not from reading the code.

Fix: moves that LocalContext.current + remember(...) computation up to the
top of SummaryScreen's function body (a real @Composable context, before
the LazyColumn(...) call even starts), and leaves only the resulting
`orderedCards.forEach { ... item { ... } }` loop -- which IS valid inside
the LazyColumn scope -- where it was.

Run from the repo root:
    python3 fix_composable_context_error.py
"""
import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

UI = "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
TARGET_FILES = [UI]


def die(msg: str) -> None:
    print(f"!! {msg}")
    sys.exit(1)


def backup_file(rel_path: str) -> None:
    src = ROOT / rel_path
    dst = BACKUP_DIR / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def apply_edit(rel_path: str, old: str, new: str, desc: str) -> bool:
    path = ROOT / rel_path
    text = path.read_text(encoding="utf-8")

    old_count = text.count(old)
    if old_count == 0:
        if text.count(new) >= 1:
            print(f"   (already applied, skipping) {desc}")
            return False
        die(f"Anchor not found for '{desc}' in {rel_path}, and patched text "
            f"is also absent. File may have changed since this script was "
            f"written -- aborting rather than guessing.")

    if old_count != 1:
        die(f"Expected exactly 1 occurrence of anchor for '{desc}' in "
            f"{rel_path}, found {old_count}. Aborting rather than guessing "
            f"which one to patch.")

    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"   applied: {desc}")
    return True


def main() -> None:
    print("==> Checking target files exist")
    for rel in TARGET_FILES:
        if not (ROOT / rel).exists():
            die(f"Expected file not found: {rel} (run this from the repo root)")

    print(f"==> Backing up touched files to {BACKUP_DIR.relative_to(ROOT)}")
    for rel in TARGET_FILES:
        backup_file(rel)

    print("==> Moving LocalContext.current + remember(...) to the top of SummaryScreen")
    apply_edit(
        UI,
        old='private fun SummaryScreen(\n'
            '    palette: BitPalette,\n'
            '    state: DashboardUiState,\n'
            '    dataSource: HealthDataSource,\n'
            '    lastSyncTime: String,\n'
            '    onRefresh: () -> Unit,\n'
            '    onRequestGoogle: () -> Unit,\n'
            '    onEditLayout: () -> Unit,\n'
            '    cardLayoutVersion: Int\n'
            ') {\n'
            '    LazyColumn(',
        new='private fun SummaryScreen(\n'
            '    palette: BitPalette,\n'
            '    state: DashboardUiState,\n'
            '    dataSource: HealthDataSource,\n'
            '    lastSyncTime: String,\n'
            '    onRefresh: () -> Unit,\n'
            '    onRequestGoogle: () -> Unit,\n'
            '    onEditLayout: () -> Unit,\n'
            '    cardLayoutVersion: Int\n'
            ') {\n'
            '    val context = LocalContext.current\n'
            '    val orderedCards = remember(cardLayoutVersion) {\n'
            '        com.openhealth.sync.config.DashboardCardLayoutPrefs(context).orderedVisibleCards()\n'
            '    }\n'
            '    LazyColumn(',
        desc="hoist LocalContext.current + remember() out of the LazyColumn scope",
    )

    print("==> Removing the now-duplicate (and invalid) block from inside the LazyColumn")
    apply_edit(
        UI,
        old='                }\n'
            '\n'
            '                val context = LocalContext.current\n'
            '                val orderedCards = remember(cardLayoutVersion) {\n'
            '                    com.openhealth.sync.config.DashboardCardLayoutPrefs(context).orderedVisibleCards()\n'
            '                }\n'
            '                orderedCards.forEach { cardType ->\n'
            '                    item {\n'
            '                        DashboardOrderedCard(palette = palette, state = state, cardType = cardType)\n'
            '                    }\n'
            '                }\n'
            '            }\n'
            '        }',
        new='                }\n'
            '\n'
            '                orderedCards.forEach { cardType ->\n'
            '                    item {\n'
            '                        DashboardOrderedCard(palette = palette, state = state, cardType = cardType)\n'
            '                    }\n'
            '                }\n'
            '            }\n'
            '        }',
        desc="remove the invalid in-LazyColumn context/remember block",
    )

    print("==> Best-effort compile check")
    gradlew = ROOT / "gradlew"
    if gradlew.exists():
        result = subprocess.run(
            ["./gradlew", ":app:compileDebugKotlin", "--console=plain"],
            cwd=ROOT,
        )
        if result.returncode != 0:
            die("compileDebugKotlin failed -- NOT committing or pushing. "
                "Fix the error above (or paste it back) before re-running.")
        print("==> Compile check passed")
    else:
        print("   gradlew not found -- skipping compile check (unexpected outside "
              "a throwaway sandbox; NOT committing automatically).")
        return

    print("==> git add / commit / push")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    commit = subprocess.run(
        ["git", "commit", "-m",
         "Fix @Composable-outside-composable-context error in SummaryScreen"],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("   (nothing to commit -- all edits were likely already applied)")
        return
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)
    print("==> Done: pushed to origin/main")


if __name__ == "__main__":
    main()
