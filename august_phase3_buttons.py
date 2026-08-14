
#!/usr/bin/env python3
"""
August design system integration -- Phase 3: buttons.

Continuation of august_phase1_foundation_tokens.py and
august_phase2_card_depth_and_growth_lime.py. Run this from the repo root
AFTER both prior phases are applied and compiling green -- it edits the
same files they touched and will not apply cleanly against earlier source.

What this script does, all sourced from section 9's component table and
section 6.4/7/10 (verified against a fresh copy of
AUGUST_DESIGN_SYSTEM_AI_FIRST_v1.0.md, not from memory):

1. Extends AugustTokens.kt:
   - AugustRadius.Button = 13.dp -- the doc's exact Primary/Secondary button
     radius (distinct from the general 13-16px "regular controls" bucket
     phase 1 already covers with AugustRadius.Control, because the doc
     gives buttons one specific canonical number, not just a bucket).
   - AugustElevation.ButtonShadow{Color,Alpha,Elevation} -- the doc's
     "Accent action" shadow, `0 8px 22px rgba(110,92,246,.24)`. This is the
     one shadow in the whole spec that's deliberately accent-tinted (rgb
     110,92,246 is literally Accent, #6E5CF6) -- reserved for the Primary
     button specifically; every other shadow in this app stays neutral-
     tinted (see phase 2's card shadows).

2. Rewrites PrimaryButton (FinalBitLutShell.kt) to the doc's "Primary
   button | 44px minimum height | Purple fill, white text, 13px radius,
   accent shadow": explicit 44dp/36dp(compact) minimum height, 13dp radius,
   the accent action shadow (suppressed when disabled), and a small 1dp
   press translate on a plain tween -- matching the doc's "Hover
   translation: -1px for buttons" (section 6.4) rather than the old bouncy
   spring scale it inherited implicitly from nothing (PrimaryButton itself
   had no press animation before this phase; the *card* press bounce was
   already fixed in phase 2). Material3's own default button elevation is
   zeroed out so only the doc's explicit shadow renders -- "a component
   SHOULD have zero or one shadow".

3. Adds a new SecondaryButton, matching "Secondary button | 40px minimum
   height | White surface, subtle border, dark text" -- no shadow, per the
   same "zero or one shadow" rule (only Primary is named as having one).
   Wires it into SettingsConnectionCard's secondaryAction slot (3 real call
   sites: Google/Huawei "Connect" + "Refresh status", and "Sync now" +
   "Import archive"), which previously rendered its secondary action as a
   second identical PrimaryButton -- two equally loud purple, shadowed
   buttons side by side, when only one of them is the actual primary
   action.

4. Fixes the shared pressScale() modifier (used by 3 other pressable
   elements) from a bouncy spring to a plain tween on the doc's standard
   easing -- section 7's "no bounce, elastic overshoot" is a blanket motion
   rule, not scoped to cards specifically (which phase 2 already covered).
   The scale-on-press technique itself isn't something the doc rules out,
   just the bounce.

5. Small token-purity fix: GoalStepperButton's RoundedCornerShape(10.dp)
   literal already numerically matched AugustRadius.Compact (8-12px
   bucket) by coincidence -- swapped to the token so it stops being a
   coincidence, zero visual change.

Explicitly NOT in this phase (checked against the doc, not skipped by
accident): a real Segmented Control component (15px shell / 10px segment,
"two to four mutually exclusive views") and a text Input component (12px
radius, 11-12px inset, visible focus ring) -- there is no free-text input
anywhere in this app to redesign, and the app's one binary-choice selector
(Huawei vs Google Fit data source in Settings) is currently built from two
switch-style rows rather than a single segmented pill shell. Turning that
into a real segmented control is a genuine new component to build, and
without a way to render/screenshot Compose in this pipeline it can't be
visually verified before shipping -- same reasoning as deferring the
activity rings' Growth Lime treatment in phase 2. Left for a future phase
that can be checked against a real device render.

Every old/new text block in this script was hand-edited against a real
extraction of the current (post-phase-1-and-2) codebase first, then
generated from that edited copy's actual diff, and tested for idempotency
(a second run makes zero changes) before being included here.

Run from the repo root:
    python3 august_phase3_buttons.py
"""
import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

THEME_DIR = "app/src/main/java/com/openhealth/sync/ui/theme"
AUGUST_TOKENS = f"{THEME_DIR}/AugustTokens.kt"
UI_SHELL = "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"

TARGET_FILES = [AUGUST_TOKENS, UI_SHELL]


def die(msg: str) -> None:
    print(f"!! {msg}")
    sys.exit(1)


def backup_file(rel_path: str) -> None:
    src = ROOT / rel_path
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
                f"after phases 1 and 2 have been applied)")

    print(f"==> Backing up touched files to {BACKUP_DIR.relative_to(ROOT)}")
    for rel in TARGET_FILES:
        backup_file(rel)

    # -- AugustTokens.kt -----------------------------------------------
    print("==> Adding AugustRadius.Button")
    apply_insertion(
        AUGUST_TOKENS,
        anchor='''    val Control = 15.dp   // 13-16px: regular controls, nav items, segmented controls
    val Card = 20.dp''',
        new_with_anchor='''    val Control = 15.dp   // 13-16px: regular controls, nav items, segmented controls
    val Button = 13.dp    // component spec (9): Primary/Secondary button, exact value
    val Card = 20.dp''',
        unique_marker="val Button = 13.dp    // component spec (9): Primary/Secondary button, exact value",
        desc="add AugustRadius.Button",
    )

    print("==> Updating AugustElevation doc comment + adding ButtonShadow tokens")
    apply_edit(
        AUGUST_TOKENS,
        old='''/**
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
}''',
        new='''/**
 * Section 6.4 shadow recipes (integration phases 2-3). Compose's `shadow()`
 * takes an elevation, not an explicit CSS-style blur radius/spread, so
 * there's no exact 1:1 port of the doc's `0 14px 34px rgba(27,30,48,.08)` /
 * `0 24px 60px rgba(28,31,49,.15)` / `0 8px 22px rgba(110,92,246,.24)`
 * values -- the dp elevations here were chosen to read similarly at
 * typical phone density rather than copying the px numbers literally. The
 * color + alpha ARE taken directly from the doc. Every shadow here is used
 * alone (ambient == spot, single tint), matching section 6.4's "A component
 * SHOULD have zero or one shadow" -- no stacked or mismatched shadows.
 */
internal object AugustElevation {
    val CardShadowColor = Color(0xFF1B1E30)   // rgba(27,30,48, x)
    const val CardShadowAlpha = 0.08f
    val CardShadowElevation = 12.dp

    val HeroShadowColor = Color(0xFF1C1F31)   // rgba(28,31,49, x)
    const val HeroShadowAlpha = 0.15f
    val HeroShadowElevation = 20.dp

    // "Accent action" shadow (section 6.4): `0 8px 22px rgba(110,92,246,.24)`.
    // rgb(110,92,246) is Accent itself (#6E5CF6) -- this is the one shadow in
    // the whole spec that IS accent-tinted on purpose, reserved for the
    // Primary button per section 9's component table ("accent shadow").
    // Everywhere else (cards) uses a neutral tint -- see CardShadowColor/
    // HeroShadowColor above and their doc comments for why.
    val ButtonShadowColor = AugustColor.Accent
    const val ButtonShadowAlpha = 0.24f
    val ButtonShadowElevation = 10.dp
}''',
        desc="add AugustElevation.ButtonShadow tokens",
    )

    # -- FinalBitLutShell.kt --------------------------------------------
    print("==> Importing AugustElevation + AugustMotion in FinalBitLutShell.kt")
    apply_insertion(
        UI_SHELL,
        anchor="import com.openhealth.sync.ui.theme.AugustColor\nimport com.openhealth.sync.ui.theme.AugustRadius",
        new_with_anchor="import com.openhealth.sync.ui.theme.AugustColor\nimport com.openhealth.sync.ui.theme.AugustElevation\nimport com.openhealth.sync.ui.theme.AugustMotion\nimport com.openhealth.sync.ui.theme.AugustRadius",
        unique_marker="import com.openhealth.sync.ui.theme.AugustElevation\n",
        desc="import AugustElevation, AugustMotion",
    )

    print("==> Swapping dead spring/Spring imports for BorderStroke + animateDpAsState")
    apply_edit(
        UI_SHELL,
        old="import androidx.compose.animation.core.spring\nimport androidx.compose.animation.core.Spring\nimport androidx.compose.animation.core.tween",
        new="import androidx.compose.foundation.BorderStroke\nimport androidx.compose.animation.core.animateDpAsState\nimport androidx.compose.animation.core.tween",
        desc="swap spring/Spring imports for BorderStroke/animateDpAsState (spring's only call site is rewritten below)",
    )

    print("==> Token-purity fix: GoalStepperButton's 10.dp -> AugustRadius.Compact")
    apply_edit(
        UI_SHELL,
        old='''            .size(30.dp)
            .clip(RoundedCornerShape(10.dp))
            .background(accent.copy(alpha = 0.16f))''',
        new='''            .size(30.dp)
            .clip(RoundedCornerShape(AugustRadius.Compact))
            .background(accent.copy(alpha = 0.16f))''',
        desc="GoalStepperButton radius -> AugustRadius.Compact",
    )

    print("==> Fixing pressScale() to use August's standard tween instead of a bouncy spring")
    apply_edit(
        UI_SHELL,
        old='''/**
 * iOS/Apple-Health-style tactile press feedback: scales a tappable surface down
 * slightly while pressed, using spring physics rather than a linear tween so the
 * release has a small natural bounce.
 *
 * Pass the SAME [interactionSource] you give to your own `Modifier.clickable(...)`
 * — this modifier only observes press state, it never intercepts the tap itself,
 * so the real onClick still fires exactly as before.
 */
@Composable
internal fun Modifier.pressScale(interactionSource: MutableInteractionSource): Modifier {
    val pressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.97f else 1f,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessLow
        ),
        label = "pressScale"
    )
    return this.scale(scale)
}

@Composable
private fun PrimaryButton(
    text: String,
    accent: Color,
    enabled: Boolean = true,
    compact: Boolean = false,
    modifier: Modifier = Modifier.fillMaxWidth(),
    onClick: () -> Unit
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier,
        shape = RoundedCornerShape(if (compact) 16.dp else 22.dp),
        colors = ButtonDefaults.buttonColors(containerColor = accent, contentColor = Color.White),
        contentPadding = if (compact) PaddingValues(horizontal = 12.dp, vertical = 6.dp) else ButtonDefaults.ContentPadding
    ) { Text(text, fontWeight = FontWeight.ExtraBold, fontSize = if (compact) 12.sp else 14.sp, maxLines = 1, overflow = TextOverflow.Ellipsis) }
}''',
        new='''/**
 * Tactile press feedback: scales a tappable surface down slightly while
 * pressed.
 *
 * August design system integration, phase 3 (see AugustTokens.kt): was a
 * bouncy spring (small overshoot on release) -- section 7 is explicit that
 * motion "confirms" a state change and rules out bounce/elastic overshoot
 * everywhere, not just on cards (which phase 2 already fixed). This keeps
 * the scale-on-press technique itself, which the doc doesn't rule out, just
 * on its standard tween + easing instead of a spring.
 *
 * Pass the SAME [interactionSource] you give to your own `Modifier.clickable(...)`
 * — this modifier only observes press state, it never intercepts the tap itself,
 * so the real onClick still fires exactly as before.
 */
@Composable
internal fun Modifier.pressScale(interactionSource: MutableInteractionSource): Modifier {
    val pressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.97f else 1f,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "pressScale"
    )
    return this.scale(scale)
}

@Composable
private fun PrimaryButton(
    text: String,
    accent: Color,
    enabled: Boolean = true,
    compact: Boolean = false,
    modifier: Modifier = Modifier.fillMaxWidth(),
    onClick: () -> Unit
) {
    // August design system integration, phase 3 (see AugustTokens.kt).
    // Section 9's component table: "Primary button | 44px minimum height |
    // Purple fill, white text, 13px radius, accent shadow." [compact] isn't
    // a named August variant -- it's this app's own smaller inline usage
    // (e.g. two side-by-side actions in SettingsConnectionCard) -- sized to
    // section 10's "Compact controls: 36px only when spacing preserves a
    // minimum 24px target area", not invented freely.
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val press by animateDpAsState(
        targetValue = if (pressed) 1.dp else 0.dp,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "primaryButtonPress"
    )
    val minHeight = if (compact) 36.dp else 44.dp
    Button(
        onClick = onClick,
        enabled = enabled,
        interactionSource = interactionSource,
        modifier = modifier
            .heightIn(min = minHeight)
            .graphicsLayer { translationY = -press.toPx() }
            .then(
                if (enabled) {
                    Modifier.shadow(
                        elevation = AugustElevation.ButtonShadowElevation,
                        shape = RoundedCornerShape(AugustRadius.Button),
                        ambientColor = AugustElevation.ButtonShadowColor.copy(alpha = AugustElevation.ButtonShadowAlpha),
                        spotColor = AugustElevation.ButtonShadowColor.copy(alpha = AugustElevation.ButtonShadowAlpha)
                    )
                } else {
                    Modifier
                }
            ),
        shape = RoundedCornerShape(AugustRadius.Button),
        colors = ButtonDefaults.buttonColors(containerColor = accent, contentColor = Color.White),
        elevation = ButtonDefaults.buttonElevation(
            defaultElevation = 0.dp,
            pressedElevation = 0.dp,
            disabledElevation = 0.dp
        ),
        contentPadding = if (compact) PaddingValues(horizontal = 12.dp, vertical = 6.dp) else ButtonDefaults.ContentPadding
    ) { Text(text, fontWeight = FontWeight.ExtraBold, fontSize = if (compact) 12.sp else 14.sp, maxLines = 1, overflow = TextOverflow.Ellipsis) }
}

/**
 * August design system integration, phase 3 (see AugustTokens.kt). Section
 * 9's component table: "Secondary button | 40px minimum height | White
 * surface, subtle border, dark text." Introduced this phase for
 * SettingsConnectionCard's secondary action slot (e.g. "Refresh status"
 * next to "Connect"), which previously rendered as a second identical
 * PrimaryButton -- two equally-loud purple actions side by side, when only
 * one of them is really the primary action. No shadow, matching section
 * 9.1 (only Primary gets the accent shadow) and 6.4's "zero or one shadow"
 * -- a bordered, unshadowed button reads as secondary next to a shadowed
 * filled one without needing a second visual language.
 */
@Composable
private fun SecondaryButton(
    text: String,
    palette: BitPalette,
    enabled: Boolean = true,
    compact: Boolean = false,
    modifier: Modifier = Modifier.fillMaxWidth(),
    onClick: () -> Unit
) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val press by animateDpAsState(
        targetValue = if (pressed) 1.dp else 0.dp,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "secondaryButtonPress"
    )
    val minHeight = if (compact) 36.dp else 40.dp
    Button(
        onClick = onClick,
        enabled = enabled,
        interactionSource = interactionSource,
        modifier = modifier
            .heightIn(min = minHeight)
            .graphicsLayer { translationY = -press.toPx() },
        shape = RoundedCornerShape(AugustRadius.Button),
        colors = ButtonDefaults.buttonColors(containerColor = palette.card, contentColor = palette.text),
        border = BorderStroke(1.dp, palette.stroke),
        elevation = ButtonDefaults.buttonElevation(
            defaultElevation = 0.dp,
            pressedElevation = 0.dp,
            disabledElevation = 0.dp
        ),
        contentPadding = if (compact) PaddingValues(horizontal = 12.dp, vertical = 6.dp) else ButtonDefaults.ContentPadding
    ) { Text(text, fontWeight = FontWeight.ExtraBold, fontSize = if (compact) 12.sp else 14.sp, maxLines = 1, overflow = TextOverflow.Ellipsis) }
}''',
        desc="redesign PrimaryButton + add SecondaryButton",
    )

    print("==> Using SecondaryButton for SettingsConnectionCard's secondary action")
    apply_edit(
        UI_SHELL,
        old='''            if (secondaryAction != null && onSecondaryAction != null) {
                PrimaryButton(
                    text = secondaryAction,
                    accent = accent,
                    compact = true,
                    modifier = Modifier.weight(1f),
                    onClick = onSecondaryAction
                )
            }''',
        new='''            if (secondaryAction != null && onSecondaryAction != null) {
                SecondaryButton(
                    text = secondaryAction,
                    palette = palette,
                    compact = true,
                    modifier = Modifier.weight(1f),
                    onClick = onSecondaryAction
                )
            }''',
        desc="SettingsConnectionCard secondary action -> SecondaryButton",
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
        ["git", "commit", "-m", "August design system integration, phase 3: buttons"],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("   (nothing to commit -- all edits were likely already applied)")
        return
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)
    print("==> Done: pushed to origin/main")


if __name__ == "__main__":
    main()
