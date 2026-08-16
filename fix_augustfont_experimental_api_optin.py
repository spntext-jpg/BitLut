
#!/usr/bin/env python3
"""
Fix: compileDebugKotlin failure in AugustTokens.kt (ExperimentalTextApi).

Your build log caught a real bug that this integration's own sandbox
testing structurally cannot catch: `Font(resId, weight, style,
variationSettings)` -- the overload phase 5 used to render the bundled
Inter Variable font at specific points on its weight axis -- is marked
`@ExperimentalTextApi` by Compose UI itself. Unlike most experimental-API
warnings, Kotlin treats an unacknowledged use of this one as a hard
compile error (`e:`, not `w:`), which is exactly what failed on your
Codespace.

Every phase of this integration was hand-edited, diffed against a fresh
extraction, and verified byte-for-byte + idempotent before delivery -- but
none of that touches a real Kotlin/Compose compiler, only text equality.
Phase 5 got the font resource, the weight registration, and the doc
comments right (nothing about those changed), but missed that this one
specific API needs an explicit opt-in. This script adds exactly that,
nothing else.

Both phase 4 (navigation) and remove_activity_rings.py compiled and
pushed successfully on your end -- this fix only touches AugustTokens.kt,
same file phase 5 touched, nothing from those other two scripts.

What this script does:

1. Imports androidx.compose.ui.text.ExperimentalTextApi.
2. Adds @OptIn(ExperimentalTextApi::class) directly on the AugustFont
   object -- scoped to just that one declaration (the only place in the
   app that touches this API), not a broader file- or module-level
   suppression.

Hand-edited against a real copy of your current (post phase-5) AugustTokens.kt
first, then generated from that edited copy's actual diff, and tested for
idempotency (a second run makes zero changes) before being included here.

Run from the repo root:
    python3 fix_augustfont_experimental_api_optin.py
"""
import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

AUGUST_TOKENS = "app/src/main/java/com/openhealth/sync/ui/theme/AugustTokens.kt"
TARGET_FILES = [AUGUST_TOKENS]


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
            die(f"Expected file not found: {rel} (run this from the repo root, "
                f"after phase 5 has been applied)")

    print(f"==> Backing up touched files to {BACKUP_DIR.relative_to(ROOT)}")
    for rel in TARGET_FILES:
        backup_file(rel)

    print("==> Importing ExperimentalTextApi")
    apply_edit(
        AUGUST_TOKENS,
        old='''import androidx.compose.material3.Typography
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle''',
        new='''import androidx.compose.material3.Typography
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.ExperimentalTextApi
import androidx.compose.ui.text.TextStyle''',
        desc="import ExperimentalTextApi",
    )

    print("==> Adding @OptIn(ExperimentalTextApi::class) to AugustFont")
    apply_edit(
        AUGUST_TOKENS,
        old=''' * didn't need per-TextStyle fontFamily overrides).
 */
internal object AugustFont {''',
        new=''' * didn't need per-TextStyle fontFamily overrides).
 *
 * @OptIn(ExperimentalTextApi::class): the `Font(resId, weight, style,
 * variationSettings)` overload -- the one that actually lets a resource
 * font be rendered at a specific point on its variable axes instead of
 * just its default instance -- is marked experimental by Compose UI
 * itself, and unlike most `@Experimental*` warnings, Kotlin treats an
 * unacknowledged use of it as a hard compile error, not a warning (caught
 * by this integration's own compile gate on the very first real build --
 * this file had never actually been compiled by a real Kotlin toolchain
 * before that, only diffed against a hand-edited copy, which can verify
 * the text is exactly what was intended but can't catch a real compiler
 * error). The opt-in is scoped to this one object rather than a broader
 * file- or module-level suppression, since it's the only place in the
 * app that touches this API.
 */
@OptIn(ExperimentalTextApi::class)
internal object AugustFont {''',
        desc="add @OptIn(ExperimentalTextApi::class) to AugustFont",
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
        ["git", "commit", "-m", "Fix: opt in to ExperimentalTextApi for AugustFont's variable-font Font() calls"],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("   (nothing to commit -- all edits were likely already applied)")
        return
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)
    print("==> Done: pushed to origin/main")


if __name__ == "__main__":
    main()
