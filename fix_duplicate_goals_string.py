#!/usr/bin/env python3
"""
Fix: duplicate `goals_section_title` string resource.

add_activity_rings_and_goal_progress.py introduced a new string named
goals_section_title without checking whether that name already existed in
the app. It did: goals_section_title/goal_steps_label/goal_distance_label/
goal_active_minutes_label/goal_calories_label already sit, unused, near the
Data Source section -- a dead leftover from an earlier, already-abandoned
"Daily goals" settings UI (the same "outside BitLut's transfer mission"
decision referenced elsewhere in this codebase). My new string collided
with that old one, breaking :app:mergeDebugResources with "Found item
String/goals_section_title more than one time" -- exactly the error you
hit. Sorry about that; should have grepped for the name before adding it.

Fix: renames the string I actually introduced (the one paired with
goals_section_body, next to goal_template, that the Goals card in Settings
uses) to dashboard_goals_section_title, in both locales and in the one
Kotlin reference. The old, pre-existing, still-unused strings near Data
Source are left exactly as they were -- untangling that dead leftover is a
separate, unrelated cleanup, not this fix's job.

Safe to run regardless of whether add_activity_rings_and_goal_progress.py
or add_dashboard_card_layout_editor.py partially applied before failing --
their file edits stayed in place even though the compile check failed and
blocked the commit, so this fixes them in place, then compiles and commits
+ pushes everything that's currently pending (this script's own fix plus
both of those scripts' already-applied-but-uncommitted edits) in one go.
No need to re-run add_activity_rings_and_goal_progress.py or
add_dashboard_card_layout_editor.py afterward -- just this one:

    python3 fix_duplicate_goals_string.py
"""
import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

UI = "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
STRINGS_EN = "app/src/main/res/values/strings.xml"
STRINGS_RU = "app/src/main/res/values-ru/strings.xml"

TARGET_FILES = [UI, STRINGS_EN, STRINGS_RU]


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

    print("==> Renaming the colliding string (EN)")
    apply_edit(
        STRINGS_EN,
        old='    <string name="goals_section_title">Daily goals</string>\n'
            '    <string name="goals_section_body">Used by the activity rings and progress indicators on the dashboard.</string>',
        new='    <string name="dashboard_goals_section_title">Daily goals</string>\n'
            '    <string name="goals_section_body">Used by the activity rings and progress indicators on the dashboard.</string>',
        desc="rename goals_section_title -> dashboard_goals_section_title (EN)",
    )

    print("==> Renaming the colliding string (RU)")
    apply_edit(
        STRINGS_RU,
        old='    <string name="goals_section_title">Дневные цели</string>\n'
            '    <string name="goals_section_body">Используются кольцами активности и индикаторами прогресса на главном экране.</string>',
        new='    <string name="dashboard_goals_section_title">Дневные цели</string>\n'
            '    <string name="goals_section_body">Используются кольцами активности и индикаторами прогресса на главном экране.</string>',
        desc="rename goals_section_title -> dashboard_goals_section_title (RU)",
    )

    print("==> Updating the Kotlin reference")
    apply_edit(
        UI,
        old='            text = stringResource(R.string.goals_section_title),',
        new='            text = stringResource(R.string.dashboard_goals_section_title),',
        desc="update Kotlin reference to the renamed string",
    )

    print("==> Checking for any remaining duplicate string names (defensive)")
    for rel in (STRINGS_EN, STRINGS_RU):
        text = (ROOT / rel).read_text(encoding="utf-8")
        import re
        names = re.findall(r'<string name="([a-zA-Z0-9_]+)"', text)
        seen = set()
        dupes = set()
        for n in names:
            if n in seen:
                dupes.add(n)
            seen.add(n)
        if dupes:
            die(f"{rel} still has duplicate string names after the fix: {sorted(dupes)}. "
                f"Aborting -- this needs a human look, not another automated guess.")
    print("   no duplicate string names found")

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
        ["git", "commit", "-m", "Fix duplicate goals_section_title string resource"],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("   (nothing to commit -- all edits were likely already applied)")
        return
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)
    print("==> Done: pushed to origin/main")


if __name__ == "__main__":
    main()
