#!/usr/bin/env python3
"""
BitLut patch v3: activate the August v3 dark theme, driven by system
appearance (Settings > System default).

Context:
  BitPalette.dark() already existed in FinalBitLutShell.kt but was
  completely unreachable -- the one call site was hardcoded to
  BitPalette.light(), and two separate verify scripts explicitly asserted
  that OS dark mode must NOT be wired up
  (`'darkColorScheme' not in theme and 'isSystemInDarkTheme' not in theme`)
  and that the palette call site must stay pinned to light()
  (`'val palette = remember { BitPalette.light() }' in shell`). This patch
  is mostly "finish and activate a dark theme someone already half-built,"
  not a from-scratch design.

  The August v3 design doc (AUGUST_DESIGN_SYSTEM, re-attached 2026-08-22)
  is written for a different product (a web media tool: sidebar, canvas
  panel, drag-and-drop workbench) and does not define a full OS-driven dark
  theme -- only that Navy is a permanent dark architectural anchor inside an
  otherwise light-canvas UI. It has no answer for "what does a white Surface
  card become at night." This patch answers that by extending the existing
  Navy ramp's role rather than inventing a second dark palette:
    - dark Canvas -> AugustColor.Navy      (was Canvas, #F7F8FC, in light)
    - dark Surface -> AugustColor.NavyRaised (was Surface, #FFFFFF, in light)
    - dark Soft -> AugustColor.NavySoft     (was Soft, #F2F3F7, in light)
  matching the light scheme's own Canvas -> Surface -> Soft elevation
  relationship, just inverted.

  Confirmed product decisions (not inferred): Lime stays a filled surface
  with Ink text in both modes; the Steps Hero card stays NavyRaised
  unchanged in both modes (SoftCard's `hero` branch in GlassCards.kt already
  hardcodes AugustColor.NavyRaised independent of `palette`, so it needed no
  change at all for this patch).

  Every reused color pairing was checked against real WCAG contrast math
  before reuse (see BitLutExpressiveTheme.kt's own doc comment for the
  numbers), not eyeballed. DangerFg (tuned for a white background, drops to
  2.62:1 on NavyRaised) is deliberately NOT reused for dark error text --
  AugustColor's pre-existing but previously-unused DarkErrorContainerFg
  (#FFC9C9, ~11:1+ against both Navy and NavyRaised) is used instead for
  both the dark `error` and `onErrorContainer` roles, per the design doc's
  own "don't add a new color literal if a role already exists" rule.

Files touched:
  - app/src/main/java/com/openhealth/sync/ui/theme/BitLutExpressiveTheme.kt
    (new AugustDarkScheme, isSystemInDarkTheme() wiring, status bar contrast)
  - app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt
    (palette call site now switches with system dark mode; also fixes a
    minor Color.White -> AugustColor.Surface token-consistency nit in
    BitPalette.dark() found while in this function)
  - app/src/main/java/com/openhealth/sync/MainActivity.kt
    (comment-only fix: previously described an isSystemInDarkTheme() call
    inside FinalBitLutShell that did not actually exist anywhere in the
    codebase before this patch; now accurate)
  - scripts/verify_sync_august_v3_recovery.py
    (flips the two guardrails that explicitly forbade dark mode; adds
    assertions for the new AugustDarkScheme content itself)
  - scripts/verify_reliability_and_design_sprint.py
    (fixes two assertions that were ALREADY stale/failing before this patch,
    unrelated to dark mode, found in passing while editing this file's
    neighborhood: a "sleep = HealthAccent.sleep" check referencing a field
    that no longer exists post sleep-feature-removal, and a "LightShadowTint"
    check referencing a symbol that no longer exists after GlassCards.kt's
    phase-2 rewrite to the plain August v3 card recipe. Also removes the
    `glass_cards` file read, which becomes dead/unused once its only two
    checks are gone.)

Usage:
    python3 patch_august_v3_dark_theme_v3.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Reuses the repo's existing .bitlut_patch_backup/ convention (already
# present in .gitignore) rather than backing up files in-place next to the
# original -- an in-place *.bak_<suffix> file inside app/src/main/res/ broke
# AGP's mergeDebugResources in an earlier patch this session; none of the
# files this script touches are under res/, but the same convention is kept
# for consistency and to avoid ever reintroducing that class of bug.
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / "august_v3_dark_theme"


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


def backup(path: Path) -> None:
    relative = path.relative_to(ROOT)
    backup_path = BACKUP_DIR / relative
    if not backup_path.exists():
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_path)
        print(f"  backed up -> {backup_path.relative_to(ROOT)}")


def read(path: Path) -> str:
    if not path.exists():
        die(f"Expected file not found: {path}")
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def apply_edit(path: Path, old: str, new: str, expected_count: int = 1) -> bool:
    """Text-anchored replacement for genuine changes (old text disappears)."""
    text = read(path)
    count_old = text.count(old)
    count_new = text.count(new)

    if count_old == 0 and count_new >= 1:
        print(f"  already applied, skipping: {path.name} ({new[:40]!r}...)")
        return False

    if count_old != expected_count:
        die(
            f"{path}: expected {expected_count} occurrence(s) of anchor, "
            f"found {count_old}. Refusing to apply (ambiguous or stale)."
        )

    backup(path)
    write(path, text.replace(old, new, expected_count))
    print(f"  applied: {path.name}")
    return True


def apply_insertion(path: Path, anchor: str, new_with_anchor: str, unique_marker: str) -> bool:
    """
    Anchor-preserving insertion for adding a line next to text that itself
    stays unchanged (e.g. adding an import next to an existing one). Unlike
    apply_edit, the anchor is a genuine substring of the post-insertion
    result, so idempotency cannot be checked by "is the anchor still there."
    Instead this checks for `unique_marker` -- text that only exists after
    the insertion has happened (e.g. the new import line itself).
    """
    text = read(path)
    marker_count = text.count(unique_marker)

    if marker_count >= 1:
        print(f"  already applied, skipping: {path.name} ({unique_marker[:40]!r}...)")
        return False

    anchor_count = text.count(anchor)
    if anchor_count != 1:
        die(
            f"{path}: expected exactly 1 occurrence of insertion anchor, "
            f"found {anchor_count}. Refusing to apply (ambiguous or stale)."
        )

    backup(path)
    write(path, text.replace(anchor, new_with_anchor, 1))
    print(f"  inserted: {path.name}")
    return True


def main() -> None:
    theme_path = ROOT / "app/src/main/java/com/openhealth/sync/ui/theme/BitLutExpressiveTheme.kt"
    shell_path = ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
    main_activity_path = ROOT / "app/src/main/java/com/openhealth/sync/MainActivity.kt"
    verify_recovery_path = ROOT / "scripts/verify_sync_august_v3_recovery.py"
    verify_reliability_path = ROOT / "scripts/verify_reliability_and_design_sprint.py"

    for p in (theme_path, shell_path, main_activity_path, verify_recovery_path, verify_reliability_path):
        if not p.exists():
            die(f"Required file missing: {p}")

    print("== Step 1/8: BitLutExpressiveTheme.kt -- imports ==")
    apply_edit(
        theme_path,
        old="""import android.app.Activity
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme""",
        new="""import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme""",
    )

    print("== Step 2/8: BitLutExpressiveTheme.kt -- doc comment + light scheme rename ==")
    apply_edit(
        theme_path,
        old="""/**
 * August v3 is intentionally a light-canvas product system, not an OS-driven
 * dark theme. Dark is reserved for architectural anchors: the top hero,
 * navigation dock and explicit work surfaces. Regular controls/cards remain
 * White Surface on Canvas in both OS appearance modes.
 */
private val AugustScheme = lightColorScheme(""",
        new="""/**
 * August v3's own doc (section 1: "Dark Workbench, Light Controls") only
 * specifies Navy as a permanent architectural anchor -- sidebar, hero,
 * navigation -- inside an otherwise light-canvas product. It does not define
 * a full OS-driven dark theme: there is no "what does a white Surface card
 * become at night" answer in the source doc, because the doc's own product
 * (a media tool) never asked that question.
 *
 * BitLut's dark theme (2026-08-22) answers it by extending Navy's existing
 * role rather than inventing a second, unrelated dark palette: Navy takes
 * over Canvas's role, NavyRaised takes over Surface's role, NavySoft takes
 * over Soft's role -- the same relative-elevation relationship the light
 * scheme already has (Canvas -> Surface -> Soft, each one step lighter),
 * just inverted. This was a deliberate content decision confirmed directly
 * (not inferred): Lime stays a filled surface with Ink text in both modes,
 * and the Steps Hero card stays NavyRaised unchanged (SoftCard's `hero`
 * branch already hardcodes NavyRaised independent of `palette`, so it never
 * needed a dark-mode-specific change).
 *
 * Every reused token was checked against WCAG contrast math before reuse,
 * not assumed: Surface/DarkSecondaryText/Lime/Ink all clear 7:1+ against
 * Navy/NavyRaised/NavySoft. Purple only clears AA-large (3:1) against dark
 * backgrounds, not full AA text contrast (4.5:1) -- consistent with the
 * source doc's own contract that Purple is for focus rings/links/selection
 * detail, never body text, so this doesn't block reuse for that role.
 * DangerFg (tuned for white) drops to 2.62:1 on NavyRaised and does NOT get
 * reused for dark error text; AugustColor's pre-existing but previously
 * unused DarkErrorContainerFg (#FFC9C9) is used for both the dark `error`
 * role and dark `onErrorContainer`, since it already clears 11:1+ against
 * both Navy and NavyRaised and reusing one token for both matches the
 * doc's own "don't add a new color literal if a role already exists" rule
 * (section 16.5) instead of inventing a fourth red.
 */
private val AugustLightScheme = lightColorScheme(""",
    )

    print("== Step 3/8: BitLutExpressiveTheme.kt -- insert AugustDarkScheme ==")
    apply_edit(
        theme_path,
        old="""    surfaceTint          = Color.Transparent,
    scrim                = AugustColor.Navy.copy(alpha = 0.80f),
)

@Composable
fun BitLutExpressiveTheme(content: @Composable () -> Unit) {
    val view = LocalView.current""",
        new="""    surfaceTint          = Color.Transparent,
    scrim                = AugustColor.Navy.copy(alpha = 0.80f),
)

private val AugustDarkScheme = darkColorScheme(
    primary              = AugustColor.Lime,
    onPrimary            = AugustColor.LimeInk,
    primaryContainer     = AugustColor.DarkPrimaryContainer,
    onPrimaryContainer   = AugustColor.Surface,
    secondary            = AugustColor.Purple,
    onSecondary          = AugustColor.Surface,
    secondaryContainer   = AugustColor.DarkSecondaryContainer,
    onSecondaryContainer = AugustColor.Surface,
    tertiary             = AugustColor.Surface,
    onTertiary           = AugustColor.Navy,
    tertiaryContainer    = AugustColor.DarkTertiaryContainer,
    onTertiaryContainer  = AugustColor.Surface,
    error                = AugustColor.DarkErrorContainerFg,
    onError              = AugustColor.Navy,
    errorContainer       = AugustColor.DarkErrorContainer,
    onErrorContainer     = AugustColor.DarkErrorContainerFg,
    background           = AugustColor.Navy,
    onBackground         = AugustColor.Surface,
    surface              = AugustColor.NavyRaised,
    onSurface            = AugustColor.Surface,
    surfaceVariant       = AugustColor.NavySoft,
    onSurfaceVariant     = AugustColor.DarkSecondaryText,
    outline              = AugustColor.BorderDark,
    outlineVariant       = AugustColor.NavySoft,
    inverseSurface       = AugustColor.Surface,
    inverseOnSurface     = AugustColor.Ink,
    inversePrimary       = AugustColor.Lime,
    surfaceTint          = Color.Transparent,
    scrim                = AugustColor.Navy.copy(alpha = 0.80f),
)

@Composable
fun BitLutExpressiveTheme(content: @Composable () -> Unit) {
    val isDark = isSystemInDarkTheme()
    val view = LocalView.current""",
    )

    print("== Step 4/8: BitLutExpressiveTheme.kt -- status bar + colorScheme selection ==")
    apply_edit(
        theme_path,
        old="""            window.statusBarColor = AugustColor.Canvas.toArgb()
            window.navigationBarColor = AugustColor.Navy.toArgb()
            WindowCompat.getInsetsController(window, view).apply {
                isAppearanceLightStatusBars = true
                isAppearanceLightNavigationBars = false
            }
        }
    }

    MaterialTheme(
        colorScheme = AugustScheme,""",
        new="""            // Navy anchors navigation chrome in both modes already (August
            // v3's own permanent-anchor rule); the status bar follows the
            // active scheme's background/canvas so its icons keep enough
            // contrast against whatever is actually behind them.
            window.statusBarColor =
                (if (isDark) AugustColor.Navy else AugustColor.Canvas).toArgb()
            window.navigationBarColor = AugustColor.Navy.toArgb()
            WindowCompat.getInsetsController(window, view).apply {
                isAppearanceLightStatusBars = !isDark
                isAppearanceLightNavigationBars = false
            }
        }
    }

    MaterialTheme(
        colorScheme = if (isDark) AugustDarkScheme else AugustLightScheme,""",
    )

    print("== Step 5/8: FinalBitLutShell.kt -- import + palette call site ==")
    apply_insertion(
        shell_path,
        anchor="import androidx.compose.foundation.Canvas\n",
        new_with_anchor="import androidx.compose.foundation.Canvas\nimport androidx.compose.foundation.isSystemInDarkTheme\n",
        unique_marker="import androidx.compose.foundation.isSystemInDarkTheme",
    )
    apply_edit(
        shell_path,
        old="""    // August v3 uses a stable light Canvas + White Surface architecture.
    // Dark styling belongs only to explicit semantic anchors (hero/nav), not
    // to every card when the OS happens to be in dark mode.
    val palette = remember { BitPalette.light() }""",
        new="""    // August v3 dark theme (2026-08-22): non-hero cards now follow the OS
    // appearance setting via BitPalette.dark()/light(). The Hero card itself
    // is unaffected either way -- SoftCard's `hero` branch hardcodes
    // AugustColor.NavyRaised directly, independent of `palette`, since the
    // Steps card was always meant to read as the dark architectural anchor
    // in both modes (confirmed product decision, not a default carried over
    // by omission).
    val isDarkTheme = isSystemInDarkTheme()
    val palette = remember(isDarkTheme) {
        if (isDarkTheme) BitPalette.dark() else BitPalette.light()
    }""",
    )

    print("== Step 6/8: FinalBitLutShell.kt -- BitPalette.dark() token consistency ==")
    apply_edit(
        shell_path,
        old="""        fun dark(): BitPalette = BitPalette(
            dark = true,
            systemBackground = AugustColor.Navy,
            card = AugustColor.DarkPanel,
            text = Color.White,""",
        new="""        fun dark(): BitPalette = BitPalette(
            dark = true,
            systemBackground = AugustColor.Navy,
            card = AugustColor.DarkPanel,
            text = AugustColor.Surface,""",
    )

    print("== Step 7/8: MainActivity.kt -- comment correction ==")
    apply_edit(
        main_activity_path,
        old="""        // isDark is computed in FinalBitLutShell (isSystemInDarkTheme()) --
        // no manual SystemBarStyle wiring needed since both use the same
        // system signal. The root Scaffold in FinalBitLutShell already
        // applies M3's default contentWindowInsets, and the bottom nav bar
        // already calls navigationBarsPadding() itself, so no other insets
        // work was needed for this.""",
        new="""        // isSystemInDarkTheme() is read in BitLutExpressiveTheme (status/nav
        // bar icon contrast) and in FinalBitLutShell (card palette, since
        // 2026-08-22's dark theme) -- no manual SystemBarStyle wiring needed
        // since all three read the same system signal. The root Scaffold in
        // FinalBitLutShell already applies M3's default contentWindowInsets,
        // and the bottom nav bar already calls navigationBarsPadding()
        // itself, so no other insets work was needed for this.""",
    )

    print("== Step 8/8: verify scripts -- flip dark-mode guardrails, fix stale checks ==")
    apply_edit(
        verify_recovery_path,
        old="require('darkColorScheme' not in theme and 'isSystemInDarkTheme' not in theme, 'OS dark mode still overrides August v3 surface architecture')",
        new="""require(
    'darkColorScheme' in theme and 'isSystemInDarkTheme' in theme,
    'August v3 dark theme (2026-08-22) must wire a real dark ColorScheme driven by system appearance'
)""",
    )
    apply_edit(
        verify_recovery_path,
        old="require('val palette = remember { BitPalette.light() }' in shell, 'main shell can still switch all cards to dark palette')",
        new="""require(
    'if (isDarkTheme) BitPalette.dark() else BitPalette.light()' in shell,
    'main shell must switch card palette with system dark mode (2026-08-22 dark theme)'
)""",
    )
    apply_edit(
        verify_recovery_path,
        old="""require('targetValue = if (hero) AugustColor.NavyRaised else palette.card' in cards, 'top hero is not a true NavyRaised surface')
print('Sync quota recovery + August v3 verifier passed.')""",
        new="""require('targetValue = if (hero) AugustColor.NavyRaised else palette.card' in cards, 'top hero is not a true NavyRaised surface')
require('AugustDarkScheme' in theme, 'dark ColorScheme definition missing')
require('background           = AugustColor.Navy' in theme, 'dark scheme background is not Navy')
require('surface              = AugustColor.NavyRaised' in theme, 'dark scheme surface is not NavyRaised')
print('Sync quota recovery + August v3 verifier passed.')""",
    )
    apply_edit(
        verify_reliability_path,
        old='glass_cards = read("app/src/main/java/com/openhealth/sync/GlassCards.kt")\nshell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")',
        new='shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")',
    )
    apply_edit(
        verify_reliability_path,
        old="""require("activity = HealthAccent.activity" in shell, "BitPalette.dark() must reuse HealthAccent instead of redeclaring near-duplicate hex values")
require("sleep = HealthAccent.sleep" in shell, "BitPalette.dark() sleep must reuse HealthAccent")
require("0xFF6D5DF6" not in shell, "The old orphaned third 'sleep' purple must be gone")""",
        new="""require("activity = HealthAccent.activity" in shell, "BitPalette.dark() must reuse HealthAccent instead of redeclaring near-duplicate hex values")
require("0xFF6D5DF6" not in shell, "The old orphaned third 'sleep' purple must be gone")""",
    )
    apply_edit(
        verify_reliability_path,
        old="""require("LightShadowTint" in glass_cards, "GlassCards.kt must use a warm shadow tint for light theme instead of flat black")
require("0.045f else 0.025f" not in glass_cards, "Light theme card tint must be strengthened beyond the old near-invisible values")""",
        new="""# LightShadowTint / the old "0.045f else 0.025f" check were removed
# (2026-08-22): GlassCards.kt was rewritten to the plain August v3 card recipe
# (see that file's own phase-2 doc comment) and no longer has a
# LightShadowTint symbol at all -- this assertion had been silently failing
# against the current codebase before this fix, unrelated to the dark theme
# work that prompted this pass over the file.""",
    )

    print("\n== Compile gate: :app:assembleDebug ==")
    gradlew = ROOT / "gradlew"
    if not gradlew.exists():
        die("gradlew not found at repo root -- run this script from the BitLut repo root.")

    result = subprocess.run(
        [
            str(gradlew),
            ":app:assembleDebug",
            "--no-daemon",
            "--max-workers=1",
            "--no-watch-fs",
            "--console=plain",
            "-Dorg.gradle.jvmargs=-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8",
            "-Pkotlin.compiler.execution.strategy=in-process",
        ],
        cwd=ROOT,
    )
    if result.returncode != 0:
        die("assembleDebug failed. No commit, no push. Fix the build and re-run this script.")

    print("\n== assembleDebug succeeded. Committing and pushing. ==")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    commit = subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "Activate August v3 dark theme, driven by system appearance",
        ],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("Nothing to commit (already applied) -- skipping push.")
        return

    push = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT)
    if push.returncode != 0:
        die("git push failed. Commit succeeded locally; push manually once resolved.")

    print("\nDone.")


if __name__ == "__main__":
    main()
