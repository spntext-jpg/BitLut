
#!/usr/bin/env python3
"""
Neoglassmorphism 2.0 pass on the bottom nav.

Run this after phase 4 (august_phase4_navigation.py) and the
ExperimentalTextApi fix (fix_augustfont_experimental_api_optin.py) are
both applied -- it edits the exact files those left behind.

Context: phase 4 already rebuilt the bottom nav against August's own
"Mobile nav: dark glass surface" line -- a fixed Navy shell, one shadow,
no bounce. That line is deliberately restrained (it's one sentence, no
numbers), because August's own non-goals rule out "glass-heavy" as a
whole-app default -- see GlassCards.kt's phase-2 rewrite, which moved
cards AWAY from a heavier glass look on purpose. This script does NOT
reverse that. It's scoped to the one place current 2026 design consensus
(checked, not assumed -- see AugustGlass's own doc comment in
AugustTokens.kt for the actual sources) and August's own doc agree glass
belongs: the floating navigation layer specifically, not content.

What "neoglassmorphism 2.0" means here, concretely -- and what it
honestly can't mean without a bigger change:

  - CAN do with stable, dependency-free Compose APIs: multi-layer
    translucent tinting (two stacked background layers instead of one
    flat color, so the shell has real depth instead of reading as "a
    color with alpha"), and a specular gradient-stroke border (bright at
    the top, fading toward transparent, the detail that makes glass read
    as glass rather than plastic in every real reference checked). Both
    verified as real, stable, non-experimental Compose Foundation APIs
    before use -- Modifier.border(brush = ...) and Brush.verticalGradient
    are both checked against Compose's own documented signatures, the
    same way AugustFont's Font() call should have been checked before
    phase 5 shipped instead of after a build broke on it.

  - CANNOT do without a new dependency or a bigger architecture change:
    true backdrop blur-through -- the Dashboard content actually blurring
    as it scrolls behind the bar, which is what Liquid Glass and most
    real "neoglassmorphism" references actually mean by "glass."
    Compose's own Modifier.blur() only blurs a composable's OWN drawn
    content, not whatever sits behind it, and only takes effect on API
    31+ (silently ignored below that -- not a crash, but not the effect
    either). Getting real backdrop-blur-through needs either a shader/
    blur library (a new Gradle dependency, which this integration's own
    conventions treat as its own separate, isolated change, not something
    to fold into a visual pass) or capturing and re-compositing the
    content layer behind the Scaffold, a real structural change. Neither
    is done here -- what's here is everything glassmorphism actually IS
    apart from that one step, not a fake stand-in for it.

What this script does:

1. Adds AugustGlass to AugustTokens.kt: two background tint layers (one
   base wash, one saturation-boosted gradient on top -- the boost color
   was computed, not eyeballed: Navy blended 10% toward Accent, same
   verify-don't-guess approach as every derived color in this
   integration), a specular gradient-stroke border, and a border width
   constant.

2. Rewrites GlassNavigation.kt's shell background/border: the old single
   flat `AugustColor.Navy.copy(alpha = 0.94f)` fill and flat
   `AugustColor.BorderDark` border become the two-layer tint plus the
   specular gradient border. Nothing else in the file changes -- the
   shadow, the button composables, the motion, the tap-secret-trigger
   logic are all untouched, still exactly what phase 4 left them as.

Hand-edited against a real copy of the current (post phase-4 +
ExperimentalTextApi-fix) codebase first, then generated from that edited
copy's actual diff, and tested for idempotency (a second run makes zero
changes) before being included here.

Run from the repo root:
    python3 navbar_neoglassmorphism.py
"""
import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

THEME_DIR = "app/src/main/java/com/openhealth/sync/ui/theme"
AUGUST_TOKENS = f"{THEME_DIR}/AugustTokens.kt"
NAV = "app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt"

TARGET_FILES = [AUGUST_TOKENS, NAV]


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


def apply_insertion(rel_path: str, anchor: str, new_with_anchor: str, unique_marker: str, desc: str) -> bool:
    """For edits that insert new text between two lines that stay unchanged
    on both sides -- see phase 1's script for why this needs to be a
    separate helper from apply_edit."""
    path = ROOT / rel_path
    text = path.read_text(encoding="utf-8")

    if unique_marker in text:
        print(f"   (already applied, skipping) {desc}")
        return False

    anchor_count = text.count(anchor)
    if anchor_count != 1:
        die(f"Expected exactly 1 occurrence of anchor for '{desc}' in "
            f"{rel_path}, found {anchor_count}. Aborting rather than "
            f"guessing which one to patch.")

    path.write_text(text.replace(anchor, new_with_anchor, 1), encoding="utf-8")
    print(f"   applied: {desc}")
    return True


def main() -> None:
    print("==> Checking target files exist")
    for rel in TARGET_FILES:
        if not (ROOT / rel).exists():
            die(f"Expected file not found: {rel} (run this from the repo root, "
                f"after phase 4 and the ExperimentalTextApi fix have been applied)")

    print(f"==> Backing up touched files to {BACKUP_DIR.relative_to(ROOT)}")
    for rel in TARGET_FILES:
        backup_file(rel)

    # -- AugustTokens.kt: add AugustGlass --------------------------------
    print("==> Adding AugustGlass token object")
    apply_insertion(
        AUGUST_TOKENS,
        anchor='''    val ButtonShadowColor = AugustColor.Accent
    const val ButtonShadowAlpha = 0.24f
    val ButtonShadowElevation = 10.dp
}

/**
 * Section 4 typography, font family (integration phase 5).''',
        new_with_anchor='''    val ButtonShadowColor = AugustColor.Accent
    const val ButtonShadowAlpha = 0.24f
    val ButtonShadowElevation = 10.dp
}

/**
 * Neoglassmorphism 2.0 recipe for the bottom nav shell (integration
 * addendum, 2026-08). NOT part of the source design doc -- August's own
 * "Mobile nav: dark glass surface" line is one sentence with no numbers
 * attached, and its non-goals explicitly rule out "glass-heavy" as a
 * whole-app default (see AugustTokens.kt's own header, and GlassCards.kt's
 * phase-2 rewrite, which deliberately moved cards AWAY from this exact
 * aesthetic). This object exists because the single named exception is the
 * navigation layer -- current 2026 consensus (checked, not assumed;
 * multiple industry sources through mid-2026, plus Apple's own Liquid
 * Glass developer guidance) converges on the same split this codebase
 * already has: flat/bento as the primary language for content, heavier
 * glass reserved specifically for the floating nav/toolbar layer that
 * sits above content. So this is real glassmorphism, deliberately
 * confined to the one component it's supposed to live on, not a reversion
 * of phase 2's card decision.
 *
 * Two real engineering constraints, checked rather than assumed:
 *   - True backdrop blur (seeing the Dashboard blur THROUGH the bar, the
 *     way iOS Liquid Glass actually works) needs either a capture of the
 *     content layer behind the bar or a third-party shader library --
 *     Compose's own `Modifier.blur()` only blurs a composable's OWN
 *     drawn content, not whatever sits behind it, and only on API 31+
 *     (silently ignored below that, not a crash). Real backdrop-blur is
 *     a separate, larger change (either add a blur library dependency or
 *     plumb a captured background layer through to this composable) --
 *     not something to slip into a nav-bar-only visual pass. What's here
 *     instead is what Liquid Glass actually IS underneath the backdrop
 *     step: multi-layer translucency, a saturation-boosted tint instead
 *     of a flat one, and a specular top-edge highlight -- the same recipe
 *     documented across Apple's own engineering write-ups and 2026 CSS
 *     implementations, minus the one step (real-time backdrop sampling)
 *     that needs a dependency this integration hasn't added.
 *   - `Modifier.border(brush = ...)` (a gradient-stroke border, not a
 *     flat color) is a real, stable, non-experimental Compose Foundation
 *     API -- verified against Compose Foundation's own border() samples
 *     before use, the same way AugustFont's Font() overload should have
 *     been checked against a real signature before phase 5 shipped
 *     instead of after a build broke on it.
 */
internal object AugustGlass {
    /** Base tint: Navy blended 10% toward Accent (computed, not eyeballed --
     * `blend(#15172A, #6E5CF6, 0.10)`), standing in for the saturation
     * boost a true backdrop-blur-through implementation would apply to
     * whatever's actually behind the bar (see this object's header for why
     * that step itself isn't implemented here). At partial alpha so it
     * reads as glass rather than a flat panel. */
    val ShellTint = Color(0xFF1E1E3E).copy(alpha = 0.72f)

    /** Second, lower layer UNDER the tint -- gives the glass real depth
     * instead of one flat translucent wash; this is what makes it read as
     * multi-layer glass rather than "Navy with alpha," the single most
     * common way a glassmorphism attempt ends up looking flat instead of
     * dimensional. */
    val ShellUndertint = AugustColor.Navy.copy(alpha = 0.55f)

    /** Specular top-edge highlight: a gradient stroke, bright at the top
     * corners fading toward transparent, standing in for the light-catching
     * rim every real glass reference (Apple's engineering write-ups, 2026
     * CSS implementations) describes as the detail that reads as "glass"
     * rather than "translucent plastic." */
    val SpecularTop = Color.White.copy(alpha = 0.38f)
    val SpecularBottom = Color.White.copy(alpha = 0.04f)

    val ShellBorderWidth = 1.dp
}

/**
 * Section 4 typography, font family (integration phase 5).''',
        unique_marker="internal object AugustGlass {",
        desc="add AugustGlass token object",
    )

    # -- GlassNavigation.kt ------------------------------------------------
    print("==> Importing Brush + AugustGlass")
    apply_insertion(
        NAV,
        anchor='''import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp
import com.openhealth.sync.ui.theme.AugustColor
import com.openhealth.sync.ui.theme.AugustElevation
import com.openhealth.sync.ui.theme.AugustMotion
import com.openhealth.sync.ui.theme.AugustRadius''',
        new_with_anchor='''import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp
import com.openhealth.sync.ui.theme.AugustColor
import com.openhealth.sync.ui.theme.AugustElevation
import com.openhealth.sync.ui.theme.AugustGlass
import com.openhealth.sync.ui.theme.AugustMotion
import com.openhealth.sync.ui.theme.AugustRadius''',
        unique_marker="import com.openhealth.sync.ui.theme.AugustGlass\n",
        desc="import Brush, AugustGlass",
    )

    print("==> Updating file header doc comment")
    apply_edit(
        NAV,
        old='''/**
 * August design system integration, phase 4 (see AugustTokens.kt). This
 * whole file was the app's last and heaviest "Glass 2.0" holdout -- a
 * 3-stop translucent gradient shell, two accent-tinted radial glow layers,
 * a specular top-highlight line, a 40dp accent-tinted shadow, an icon that
 * tilted +/-13deg and spun 360deg on tap, and five separate bouncy-spring
 * animations across the two button composables. Rewritten against section
 * 9's literal "Mobile nav: Fixed floating bar, dark glass surface" plus the
 * blanket rules already applied elsewhere in this integration: one shadow
 * per component (6.4), no bounce/elastic overshoot and motion that confirms
 * state rather than performing for its own sake (7).
 *
 * "Dark glass surface" is why this shell is Navy-based regardless of the''',
        new='''/**
 * August design system integration, phase 4 (see AugustTokens.kt), plus a
 * neoglassmorphism 2.0 pass (2026-08, see AugustGlass in AugustTokens.kt
 * for what that means here and why it's confined to this one file). This
 * file was the app's last and heaviest "Glass 2.0" holdout before phase 4
 * -- a 3-stop translucent gradient shell, two accent-tinted radial glow
 * layers, a specular top-highlight line, a 40dp accent-tinted shadow, an
 * icon that tilted +/-13deg and spun 360deg on tap, and five separate
 * bouncy-spring animations across the two button composables. Phase 4
 * rewrote it against section 9's literal "Mobile nav: Fixed floating bar,
 * dark glass surface" plus the blanket rules already applied elsewhere in
 * this integration: one shadow per component (6.4), no bounce/elastic
 * overshoot and motion that confirms state rather than performing for its
 * own sake (7). This pass keeps every one of those rules -- the shell
 * still has exactly one shadow, buttons still use a plain tween, nothing
 * bounces -- and adds real glass depth on top: a two-layer tinted
 * background instead of one flat translucent color, and a specular
 * gradient-stroke border instead of a flat one.
 *
 * "Dark glass surface" is why this shell is Navy-based regardless of the''',
        desc="update file header for neoglassmorphism pass",
    )

    print("==> Replacing flat shell background/border with layered glass tint + specular border")
    apply_edit(
        NAV,
        old='''                .clip(shellShape)
                .background(AugustColor.Navy.copy(alpha = 0.94f))
                .border(width = 1.dp, color = AugustColor.BorderDark, shape = shellShape)
                .padding(horizontal = 12.dp, vertical = 8.dp)''',
        new='''                .clip(shellShape)
                .background(AugustGlass.ShellUndertint)
                .background(Brush.verticalGradient(listOf(AugustGlass.ShellTint, Color.Transparent)))
                .border(
                    width = AugustGlass.ShellBorderWidth,
                    brush = Brush.verticalGradient(listOf(AugustGlass.SpecularTop, AugustGlass.SpecularBottom)),
                    shape = shellShape
                )
                .padding(horizontal = 12.dp, vertical = 8.dp)''',
        desc="layered glass background + specular gradient border",
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
        ["git", "commit", "-m", "Neoglassmorphism 2.0 pass on the bottom nav shell"],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("   (nothing to commit -- all edits were likely already applied)")
        return
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)
    print("==> Done: pushed to origin/main")


if __name__ == "__main__":
    main()
