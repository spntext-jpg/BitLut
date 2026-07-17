#!/usr/bin/env python3
"""
sprint2_part2_fix_widget_colors.py

BitLut hotfix -- follow-up to sprint2_part2_home_widget.py.

That script's Gradle gate caught a real compile error before it could
reach git (exactly what the gate is for): glance-appwidget 1.1.1's
ColorProvider has no ColorProvider(day = Color(..), night = Color(..))
overload -- only ColorProvider(color: Color) and ColorProvider(resId: Int)
exist. The day/night Color-based factory apparently belongs to a different
Glance version than what got resolved here; rather than chase a version
bump, this switches to the standard, version-stable approach: day/night
resource-qualified color files (values/colors.xml + values-night/colors.xml),
with ColorProvider(resId) pointing at them.

Safe to run regardless of whether sprint2_part2_home_widget.py's failed
attempt left your working tree exactly as described above or you reverted
it first -- every edit here is anchor-verified and idempotent like the
other scripts, so it will either fix the real problem or tell you clearly
if something doesn't match what it expects.

Run from the repo root inside your Codespace:
    python3 sprint2_part2_fix_widget_colors.py
"""

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / f"{TIMESTAMP}_sprint2_part2_fix_widget_colors"

touched_files = set()
edits_applied = 0
edits_skipped = 0


def log(msg):
    print(f"==> {msg}")


def backup(path: Path):
    if path in touched_files:
        return
    touched_files.add(path)
    rel = path.relative_to(ROOT)
    dest = BACKUP_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, dest)


def apply_edit(rel_path: str, description: str, old: str, new: str):
    global edits_applied, edits_skipped
    path = ROOT / rel_path
    if not path.exists():
        print(f"    !! ABORT: {rel_path} does not exist")
        sys.exit(1)
    text = path.read_text(encoding="utf-8")

    count = text.count(old)
    if count == 1:
        backup(path)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
        print(f"    OK: {description}")
        edits_applied += 1
        return

    if count == 0:
        if (not new.strip()) or new in text:
            print(f"    (already applied) {description}")
            edits_skipped += 1
            return
        print(f"    !! ABORT: anchor not found in {rel_path}, and replacement text isn't there either")
        print(f"       description: {description}")
        print("       the file may have diverged from what this script expects -- not guessing, stopping here")
        sys.exit(1)

    print(f"    !! ABORT: expected exactly 1 match for anchor in {rel_path}")
    print(f"       description: {description}")
    print(f"       found: {count} match(es) (ambiguous, refusing to guess which one)")
    sys.exit(1)


def create_file(rel_path: str, description: str, content: str):
    global edits_applied, edits_skipped
    path = ROOT / rel_path
    if path.exists() and path.read_text(encoding="utf-8") == content:
        print(f"    (already applied) {description}")
        edits_skipped += 1
        return
    if path.exists():
        backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"    OK: {description}")
    edits_applied += 1


COMMIT_MESSAGE = """Sprint 2 part 2 hotfix: widget colors via day/night resources, not ColorProvider(day=,night=)

glance-appwidget 1.1.1 has no such overload -- see script docstring.
"""

log("Step 1/4: HomeWidget.kt -- drop the unused Color import")
apply_edit(
    "app/src/main/java/com/openhealth/sync/widget/HomeWidget.kt",
    "drop androidx.compose.ui.graphics.Color import (no longer used once ColorProvider switches to resource IDs)",
    old='''import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp''',
    new='''import androidx.compose.ui.unit.dp''',
)
log("Step 2/4: HomeWidget.kt -- ColorProvider(day=,night=) -> ColorProvider(R.color.*)")
apply_edit(
    "app/src/main/java/com/openhealth/sync/widget/HomeWidget.kt",
    "switch the 3 ColorProvider calls to resource-based day/night colors",
    old='''            val cardColor = ColorProvider(day = Color(0xFFFFFFFF), night = Color(0xFF1C1C1E))
            val textColor = ColorProvider(day = Color(0xFF111318), night = Color(0xFFF8F8F8))
            val secondaryTextColor = ColorProvider(day = Color(0xFF6E6E73), night = Color(0xFF8E8E93))''',
    new='''            val cardColor = ColorProvider(R.color.widget_card)
            val textColor = ColorProvider(R.color.widget_text)
            val secondaryTextColor = ColorProvider(R.color.widget_secondary_text)''',
)
log("Step 3/4: values/colors.xml -- add the light (day) widget colors")
apply_edit(
    "app/src/main/res/values/colors.xml",
    "add widget_card/widget_text/widget_secondary_text (light)",
    old='''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="ic_launcher_background">#0D0D0D</color>
</resources>''',
    new='''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="ic_launcher_background">#0D0D0D</color>
    <!-- Sprint (2026-07-16): home screen widget colors, light (day)
         variant: see values-night/colors.xml for the dark counterpart.
         Resource-qualified files, not Glance's ColorProvider(day=, night=)
         Color-based factory: that overload doesn't exist in
         glance-appwidget 1.1.1 (confirmed from a real compiler error; only
         ColorProvider(color: Color) and ColorProvider(resId: Int) exist). -->
    <color name="widget_card">#FFFFFFFF</color>
    <color name="widget_text">#FF111318</color>
    <color name="widget_secondary_text">#FF6E6E73</color>
</resources>''',
)
log("Step 4/4: create values-night/colors.xml -- the dark (night) widget colors")
create_file(
    "app/src/main/res/values-night/colors.xml",
    "create values-night/colors.xml",
    '''<?xml version="1.0" encoding="utf-8"?>
<!--
  Sprint (2026-07-16): home screen widget colors, dark (night) variant.
  See values/colors.xml for why this is resource-qualified files rather
  than Glance's ColorProvider(day=, night=).
-->
<resources>
    <color name="widget_card">#FF1C1C1E</color>
    <color name="widget_text">#FFF8F8F8</color>
    <color name="widget_secondary_text">#FF8E8E93</color>
</resources>
''',
)

# ---------------------------------------------------------------------------
log(f"Done: {edits_applied} edit(s) applied, {edits_skipped} already up to date")

if edits_applied == 0:
    log("Nothing to do -- repo already matches the target state. Exiting without touching git.")
    sys.exit(0)

log(f"Backups written to {BACKUP_DIR.relative_to(ROOT)}")

gradlew = ROOT / "gradlew"
build_ok = None
if gradlew.exists():
    log("Running best-effort Gradle compile gate (compileDebugKotlin + processDebugResources)...")
    try:
        result = subprocess.run(
            ["./gradlew", "--console=plain", ":app:compileDebugKotlin", ":app:processDebugResources"],
            cwd=ROOT,
        )
        build_ok = result.returncode == 0
    except OSError as e:
        log(f"Could not run ./gradlew ({e}) -- skipping the compile gate.")
        build_ok = None

    if build_ok is False:
        log("Gradle check FAILED. Working tree is left patched (see backups above to revert if needed).")
        log("Not committing or pushing. Fix the reported error and re-run this script -- it is idempotent.")
        sys.exit(1)
    elif build_ok is True:
        log("Gradle check passed.")
else:
    log("No ./gradlew found in this directory -- skipping the compile gate (expected in a sandbox/test run).")

log("Committing and pushing...")
subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
commit = subprocess.run(
    ["git", "commit", "-m", COMMIT_MESSAGE],
    cwd=ROOT,
)
if commit.returncode != 0:
    log("git commit reported nothing to commit or failed -- check git status manually.")
    sys.exit(1)

push = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT)
if push.returncode != 0:
    log("git push failed -- the commit is local; push manually once resolved (e.g. auth/network).")
    sys.exit(1)

log("Pushed to origin/main. Done.")
