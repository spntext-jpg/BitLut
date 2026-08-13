
#!/usr/bin/env python3
"""
August design system integration -- Phase 2: card depth/motion + one real
Growth Lime moment, plus a dead-code sweep.

Continuation of august_phase1_foundation_tokens.py. Run this from the repo
root AFTER phase 1 is applied and compiling green -- it edits the same
files phase 1 touched (GlassCards.kt, FinalBitLutShell.kt) and will not
apply cleanly against pre-phase-1 source.

What this script does:

1. Extends AugustTokens.kt with AugustElevation (section 6.4 shadow
   recipes) -- phase 1 deliberately deferred this ("shadow constants...
   deferred to Phase 2", see that script's docstring).

2. Rewrites GlassCards.kt's SoftCard -- the app's single shared card
   component, used by nearly every Dashboard card -- from the old "Glass
   2.0" recipe (three-stop background gradient, two accent-tinted radial
   glow layers drawn behind the content, a specular top-highlight stroke,
   and a bouncy spring press animation that lifted + scaled + re-tinted the
   card at once) to August's actual spec: a plain Surface/Dark-Panel
   background, border before shadow, at most one restrained neutral-tinted
   shadow, and a small tween-based press translate instead of a spring.
   The public function signature is unchanged, so no FinalBitLutShell.kt
   call site needed editing for this rewrite -- see the file's own header
   comment for what tintWithAccent/pressLift mean now instead.

3. Gives the app's first real "Growth" moment -- the week-over-week
   positive-trend indicator in WeeklyComparisonCard -- August's actual
   Growth Lime treatment: a small Navy-backed pill with Lime text, matching
   the doc's literal "Growth: Lime with Navy text" pairing (section 3.1).
   This was deliberately deferred out of phase 1: [mind]/HealthAccent still
   aliases to Accent Dark rather than Lime, because Lime text/icons placed
   directly on this app's white/light cards measures at 1.14:1 contrast
   (computed) -- unreadable. Lime needs a proper dark backing per call site,
   which is exactly what this change gives it. The activity rings
   (ActivityRingsCard) are NOT touched in this phase -- a decorative ring
   segment's real-world legibility on a solid Lime fill can't be verified
   without actually rendering it (no Android emulator/screenshot tool in
   this pipeline), so that's left for a follow-up once it can be checked
   against a real render rather than guessed.

4. Dead-code sweep, found via whole-tree grep (not guessed):
   - Deletes app/src/main/java/com/openhealth/sync/ui/components/GlassCards.kt,
     a 24-line file containing only unused imports and zero declarations --
     an orphaned duplicate of the real SoftCard implementation at
     app/src/main/java/com/openhealth/sync/GlassCards.kt (which lives in a
     different physical folder than its package name, same as this
     codebase's other Glass* files).
   - Removes 6 string resources (both locales) confirmed to have zero
     Kotlin references anywhere in app/src/main/java: goal_template,
     goals_section_title, goal_steps_label, goal_distance_label,
     goal_active_minutes_label, goal_calories_label. These are leftover
     scaffolding from an earlier, already-abandoned Settings goals UI --
     fix_duplicate_goals_string.py's own docstring already flagged the
     goals_section_title block as "a separate, unrelated cleanup, not this
     fix's job" when it renamed the currently-live string to avoid
     colliding with these; this is that cleanup.

Every old/new text block in this script was hand-edited against a real
extraction of the current (post-phase-1) codebase first, then generated
from that edited copy's actual diff, and tested for idempotency (a second
run makes zero changes) before being included here.

Run from the repo root:
    python3 august_phase2_card_depth_and_growth_lime.py
"""
import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

THEME_DIR = "app/src/main/java/com/openhealth/sync/ui/theme"
AUGUST_TOKENS = f"{THEME_DIR}/AugustTokens.kt"
GLASS_CARDS = "app/src/main/java/com/openhealth/sync/GlassCards.kt"
DEAD_GLASS_CARDS_STUB = "app/src/main/java/com/openhealth/sync/ui/components/GlassCards.kt"
UI_SHELL = "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
STRINGS_EN = "app/src/main/res/values/strings.xml"
STRINGS_RU = "app/src/main/res/values-ru/strings.xml"

TARGET_FILES = [AUGUST_TOKENS, GLASS_CARDS, UI_SHELL, STRINGS_EN, STRINGS_RU]
# DEAD_GLASS_CARDS_STUB is handled separately (deletion, not an edit target).

GLASS_CARDS_CONTENT = '''
package com.openhealth.sync

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import com.openhealth.sync.ui.theme.AugustElevation
import com.openhealth.sync.ui.theme.AugustMotion
import com.openhealth.sync.ui.theme.AugustRadius
import com.openhealth.sync.ui.theme.AugustSpace

/**
 * August design system integration, phase 2 (see AugustTokens.kt). Rewritten
 * from the old "Glass 2.0" card recipe -- a three-stop background gradient,
 * two accent-tinted radial "glow" layers drawn behind the content, a
 * specular top-highlight stroke, and a bouncy spring press animation that
 * simultaneously lifted, scaled and re-tinted the card -- to August's actual
 * card spec: a plain Surface/Dark-Panel colored panel, border before shadow,
 * at most one restrained shadow, and press motion that "confirms" a state
 * change rather than performing for its own sake (doc section 1.3 principle
 * 7; section 6.4 "A component SHOULD have zero or one shadow"; section 7
 * "no bounce/elastic overshoot").
 *
 * The public signature is unchanged -- accent/hero/tintWithAccent/pressLift
 * all still exist -- so no call site in FinalBitLutShell.kt needed editing
 * for this rewrite. Two of those parameters do mean something different now
 * than before, both toward the same "quiet depth" principle:
 *
 *   - tintWithAccent no longer tints the card's background fill (background
 *     is always palette.card now, a plain Surface/Dark-Panel color -- the
 *     accent-wash background was exactly the "glass-heavy" look August's
 *     non-goals rule out). It now strengthens the BORDER toward the card's
 *     accent color instead, which is still "border before shadow" -- a more
 *     emphasized border, not a colored fill.
 *   - pressLift no longer scales the card or re-tints its background on
 *     press, just a small upward translate (2dp, matching the doc's "-2px
 *     for cards" hover translation) on a plain tween instead of a spring.
 */
@Composable
internal fun SoftCard(
    palette: BitPalette,
    modifier: Modifier = Modifier.fillMaxWidth(),
    accent: Color = palette.activity,
    hero: Boolean = false,
    tintWithAccent: Boolean = false,
    pressLift: Boolean = false,
    content: @Composable ColumnScope.() -> Unit
) {
    val shape = remember(hero) { RoundedCornerShape(if (hero) AugustRadius.Hero else AugustRadius.Card) }
    var pressed by remember { mutableStateOf(false) }

    val lift by animateDpAsState(
        targetValue = if (pressed) 2.dp else 0.dp,
        animationSpec = tween(AugustMotion.DefaultMs, easing = AugustMotion.StandardEasing),
        label = "softCardLift"
    )

    val bg by animateColorAsState(
        targetValue = palette.card,
        animationSpec = tween(AugustMotion.FastMs),
        label = "softCardBg"
    )

    val borderColor = if (tintWithAccent) {
        lerp(palette.stroke, accent, if (palette.dark) 0.55f else 0.45f)
    } else {
        palette.stroke
    }

    val shadowColor = if (hero) AugustElevation.HeroShadowColor else AugustElevation.CardShadowColor
    val shadowAlpha = if (hero) AugustElevation.HeroShadowAlpha else AugustElevation.CardShadowAlpha
    val shadowElevation = if (hero) AugustElevation.HeroShadowElevation else AugustElevation.CardShadowElevation

    val pressModifier = if (pressLift) {
        Modifier.pointerInput(Unit) {
            awaitEachGesture {
                try {
                    awaitFirstDown(requireUnconsumed = false)
                    pressed = true
                    do {
                        val event = awaitPointerEvent()
                    } while (event.changes.any { it.pressed })
                } finally {
                    pressed = false
                }
            }
        }
    } else {
        Modifier
    }

    Column(
        modifier = modifier
            .then(pressModifier)
            .graphicsLayer { translationY = -lift.toPx() }
            .shadow(
                elevation = shadowElevation,
                shape = shape,
                ambientColor = shadowColor.copy(alpha = shadowAlpha),
                spotColor = shadowColor.copy(alpha = shadowAlpha)
            )
            .clip(shape)
            .background(bg)
            .border(width = 1.dp, color = borderColor, shape = shape)
            .padding(if (hero) AugustSpace.s24 else AugustSpace.s16),
        content = content
    )
}
'''


def die(msg: str) -> None:
    print(f"!! {msg}")
    sys.exit(1)


def backup_file(rel_path: str) -> None:
    src = ROOT / rel_path
    if not src.exists():
        return
    dst = BACKUP_DIR / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def apply_edit(rel_path: str, old: str, new: str, desc: str) -> bool:
    """Plain-substring replacement, exactly 1 occurrence expected."""
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
    separate helper from apply_edit (the anchor remains a substring of the
    inserted result, so anchor-count-based idempotency checks never fire)."""
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
                f"after phase 1 has been applied)")

    print(f"==> Backing up touched files to {BACKUP_DIR.relative_to(ROOT)}")
    for rel in TARGET_FILES:
        backup_file(rel)
    if (ROOT / DEAD_GLASS_CARDS_STUB).exists():
        backup_file(DEAD_GLASS_CARDS_STUB)

    print("==> Extending AugustTokens.kt with AugustElevation (section 6.4 shadow recipes)")
    apply_insertion(
        AUGUST_TOKENS,
        anchor='''    val StandardEasing = androidx.compose.animation.core.CubicBezierEasing(0.2f, 0.8f, 0.2f, 1f)
}

/** Section 4 typography.''',
        new_with_anchor='''    val StandardEasing = androidx.compose.animation.core.CubicBezierEasing(0.2f, 0.8f, 0.2f, 1f)
}

/**
 * Section 6.4 shadow recipes (integration phase 2). Compose's `shadow()`
 * takes an elevation, not an explicit CSS-style blur radius/spread, so
 * there's no exact 1:1 port of the doc's `0 14px 34px rgba(27,30,48,.08)` /
 * `0 24px 60px rgba(28,31,49,.15)` values -- the dp elevations here were
 * chosen to read similarly at typical phone density rather than copying the
 * px numbers literally. The color + alpha ARE taken directly from the doc.
 * Both ambient and spot use the same neutral, non-accent tint, matching
 * section 6.4's "A component SHOULD have zero or one shadow" -- no stacked
 * or accent-tinted decorative shadow.
 */
internal object AugustElevation {
    val CardShadowColor = Color(0xFF1B1E30)   // rgba(27,30,48, x)
    const val CardShadowAlpha = 0.08f
    val CardShadowElevation = 12.dp

    val HeroShadowColor = Color(0xFF1C1F31)   // rgba(28,31,49, x)
    const val HeroShadowAlpha = 0.15f
    val HeroShadowElevation = 20.dp
}

/** Section 4 typography.''',
        unique_marker="internal object AugustElevation {",
        desc="add AugustElevation token object",
    )

    print("==> Rewriting GlassCards.kt (August Panel/Bento card recipe)")
    path = ROOT / GLASS_CARDS
    current = path.read_text(encoding="utf-8")
    if current == GLASS_CARDS_CONTENT:
        print("   (already applied, skipping) GlassCards.kt rewrite")
    else:
        path.write_text(GLASS_CARDS_CONTENT, encoding="utf-8")
        print("   applied: GlassCards.kt rewrite")

    print("==> Deleting dead stub file (ui/components/GlassCards.kt)")
    stub_path = ROOT / DEAD_GLASS_CARDS_STUB
    if stub_path.exists():
        stub_path.unlink()
        print(f"   deleted: {DEAD_GLASS_CARDS_STUB}")
    else:
        print(f"   (already applied, skipping) {DEAD_GLASS_CARDS_STUB} already absent")

    print("==> Adding AugustRadius import to FinalBitLutShell.kt")
    apply_insertion(
        UI_SHELL,
        anchor="import com.openhealth.sync.ui.theme.AugustColor\nimport com.openhealth.sync.ui.theme.BitLutExpressiveTheme",
        new_with_anchor="import com.openhealth.sync.ui.theme.AugustColor\nimport com.openhealth.sync.ui.theme.AugustRadius\nimport com.openhealth.sync.ui.theme.BitLutExpressiveTheme",
        unique_marker="import com.openhealth.sync.ui.theme.AugustRadius\n",
        desc="import AugustRadius",
    )

    print("==> Giving the positive week-over-week trend indicator a Growth Lime badge")
    apply_edit(
        UI_SHELL,
        old='''        } else {
            val positive = percentChange >= 0
            val displayColor = if (positive) HealthAccent.mind else palette.secondaryText
            Text(
                text = "${if (positive) "+" else ""}$percentChange%",
                color = displayColor,
                fontWeight = FontWeight.Black,
                fontSize = 18.sp
            )
        }''',
        new='''        } else {
            val positive = percentChange >= 0
            if (positive) {
                // August design system integration, phase 2 (see
                // AugustTokens.kt): this is the app's first real "growth"
                // moment -- a week-over-week improvement -- and the doc's
                // own named pattern for exactly this ("Growth: Lime with
                // Navy text. Never use Lime text on white", section 3.1) is
                // a small dark-backed badge, not bare colored text on the
                // ambient card. A bare Lime number on this app's white/light
                // cards measures at 1.14:1 contrast (computed) -- unreadable
                // -- which is why [mind]/HealthAccent still aliases to
                // Accent Dark rather than Lime (see HealthAccent's doc
                // comment): Lime needs its own dark backing per call site,
                // not a global color swap. Navy is used as a fixed badge
                // color in both light and dark theme, matching the doc's
                // literal "Lime with Navy text" pairing rather than
                // following the surrounding card's theme.
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(AugustRadius.Pill))
                        .background(AugustColor.Navy)
                        .padding(horizontal = 8.dp, vertical = 3.dp)
                ) {
                    Text(
                        text = "+$percentChange%",
                        color = AugustColor.GrowthLime,
                        fontWeight = FontWeight.Black,
                        fontSize = 14.sp
                    )
                }
            } else {
                Text(
                    text = "$percentChange%",
                    color = palette.secondaryText,
                    fontWeight = FontWeight.Black,
                    fontSize = 18.sp
                )
            }
        }''',
        desc="Growth Lime badge for positive week-over-week trend",
    )

    print("==> Removing dead strings (values/strings.xml)")
    apply_edit(
        STRINGS_EN,
        old='    <string name="goal_template">Goal %1$s</string>\n    <string name="dashboard_goals_section_title">Daily goals</string>',
        new='    <string name="dashboard_goals_section_title">Daily goals</string>',
        desc="remove unused goal_template (EN)",
    )
    apply_edit(
        STRINGS_EN,
        old='''    <string name="data_source_google_fit_body">The Dashboard reads only Google Fit records from Health Connect.</string>
    <string name="goals_section_title">Daily goals</string>
    <string name="goal_steps_label">Steps</string>
    <string name="goal_distance_label">Distance</string>
    <string name="goal_active_minutes_label">Active minutes</string>
    <string name="goal_calories_label">Active calories</string>
    <string name="onboarding_title">Why BitLut needs this</string>''',
        new='''    <string name="data_source_google_fit_body">The Dashboard reads only Google Fit records from Health Connect.</string>
    <string name="onboarding_title">Why BitLut needs this</string>''',
        desc="remove unused goals_section_title/goal_*_label block (EN)",
    )

    print("==> Removing dead strings (values-ru/strings.xml)")
    apply_edit(
        STRINGS_RU,
        old='    <string name="goal_template">Цель %1$s</string>\n    <string name="dashboard_goals_section_title">Дневные цели</string>',
        new='    <string name="dashboard_goals_section_title">Дневные цели</string>',
        desc="remove unused goal_template (RU)",
    )
    apply_edit(
        STRINGS_RU,
        old='''    <string name="data_source_google_fit_body">Dashboard читает только записи Google Fit из Health Connect.</string>
    <string name="goals_section_title">Дневные цели</string>
    <string name="goal_steps_label">Шаги</string>
    <string name="goal_distance_label">Дистанция</string>
    <string name="goal_active_minutes_label">Активные минуты</string>
    <string name="goal_calories_label">Активные калории</string>
    <string name="onboarding_title">Зачем это нужно BitLut</string>''',
        new='''    <string name="data_source_google_fit_body">Dashboard читает только записи Google Fit из Health Connect.</string>
    <string name="onboarding_title">Зачем это нужно BitLut</string>''',
        desc="remove unused goals_section_title/goal_*_label block (RU)",
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
        ["git", "commit", "-m", "August design system integration, phase 2: card depth/motion + growth lime + dead code sweep"],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("   (nothing to commit -- all edits were likely already applied)")
        return
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)
    print("==> Done: pushed to origin/main")


if __name__ == "__main__":
    main()
