
#!/usr/bin/env python3
"""
August design system integration -- Phase 4: navigation.

Continuation of phases 1-3. Run this from the repo root AFTER phases 1-3
are applied and compiling green -- it edits the same files they touched
and will not apply cleanly against earlier source.

What this script does:

GlassNavigation.kt was the app's last and heaviest "Glass 2.0" holdout: a
3-stop translucent gradient shell, two accent-tinted radial glow layers, a
specular top-highlight line, a 40dp accent-tinted shadow, an icon that
tilted +/-13deg AND spun 360deg on tap, and five separate bouncy-spring
animations spread across the two button composables. This script replaces
the whole file, rewritten against section 9's literal "Mobile nav: Fixed
floating bar, dark glass surface" plus the blanket rules already applied
elsewhere in this integration: one shadow per component (6.4), no bounce/
elastic overshoot, motion that confirms state rather than performing for
its own sake (7).

Specifics:
- The shell is now a fixed Navy-based "dark glass surface" REGARDLESS of
  the app's own light/dark theme setting -- unlike every other surface in
  this app (which follows BitPalette/the system theme), the doc explicitly
  names the nav bar as a fixed dark anchor. Its border/icon tones now read
  from AugustColor's dark-surface tokens directly rather than
  palette.stroke/palette.secondaryText, which would flip with the app
  theme and stop matching a shell that no longer does. This also means
  Glass20BottomNavigation no longer needs a `palette` parameter at all --
  removed as dead code (verified: it had become genuinely unused inside
  the function, not just re-themed), and its one call site in
  FinalBitLutShell.kt updated to match.
- One shadow per component: the shell keeps a single neutral Hero-style
  shadow (reusing AugustElevation's existing Hero shadow recipe from phase
  2 -- a floating nav bar is a similarly prominent element, and inventing
  a third undocumented shadow recipe for one component wasn't worth it).
  The refresh button gets the doc's "Accent action" shadow (the same one
  Primary buttons use, from phase 3) since it plays the same "single most
  central action" role a Primary button does. Nav tab buttons get NO
  shadow of their own -- they already sit inside the shell's one shadow,
  and stacking a second would violate "zero or one shadow" per component.
- The fixed 360deg spin-on-tap is gone: it played unconditionally on every
  tap regardless of whether a sync actually started, ran, or failed, so it
  was confirming the tap, not the sync -- not what "motion confirms" means
  in section 7. The press-scale that replaces it already confirms the tap
  itself. Wiring the icon to a real spin while a sync is genuinely in
  flight would need this composable to receive that state from its
  caller, which is a data-flow change beyond a visual pass -- left as a
  follow-up, not done speculatively here.
- Selected-tab treatment is now a filled Accent-purple pill behind the
  icon (matching "purple means action/selection") instead of a gradient +
  radial glow. The separate underline indicator strip is gone too -- the
  filled pill is already an unambiguous single signal, and a second
  overlapping indicator was redundant next to it, not additive.

Every old/new text block in this script was hand-edited against a real
extraction of the current (post-phase-1/2/3) codebase first, then
generated from that edited copy's actual diff, and tested for idempotency
(a second run makes zero changes) before being included here.

Run from the repo root:
    python3 august_phase4_navigation.py
"""
import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

NAV = "app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt"
UI_SHELL = "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"

TARGET_FILES = [NAV, UI_SHELL]

GLASS_NAVIGATION_CONTENT = '''
package com.openhealth.sync

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp
import com.openhealth.sync.ui.theme.AugustColor
import com.openhealth.sync.ui.theme.AugustElevation
import com.openhealth.sync.ui.theme.AugustMotion
import com.openhealth.sync.ui.theme.AugustRadius

/**
 * Hidden diagnostic log viewer trigger: 5 taps on the Settings nav icon
 * within [SECRET_TAP_WINDOW_MS] of each other open the log viewer. The
 * window resets on any tap slower than that, so 5 *ordinary*, spaced-out
 * Settings visits over a day never accidentally trigger it -- only a
 * deliberate rapid-tap gesture does.
 *
 * Lives at the [Glass20BottomNavigation] level (not inside
 * [Glass20NavButton]) so it can distinguish which tab was tapped without
 * needing every nav button to know about this feature.
 */
private const val SECRET_TAP_COUNT = 5
private const val SECRET_TAP_WINDOW_MS = 2000L

/**
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
 * "Dark glass surface" is why this shell is Navy-based regardless of the
 * app's own light/dark setting -- unlike every other surface in this app
 * (which follows BitPalette / the system theme), the doc names the nav bar
 * as a fixed dark anchor, the same role Navy plays for the sidebar/hero in
 * the doc's own reference layouts. Border and icon tones below use
 * AugustColor's dark-surface tokens directly for the same reason, not
 * palette.stroke/palette.secondaryText (which would flip with the app
 * theme and stop matching a shell that no longer does).
 */
@Composable
internal fun Glass20BottomNavigation(
    selected: MainTab,
    onSelected: (MainTab) -> Unit,
    onSecretLogViewerTriggered: () -> Unit = {},
    onRefreshClick: () -> Unit = {}
) {
    val shellShape = remember { RoundedCornerShape(AugustRadius.Pill) }

    var secretTapCount by remember { mutableIntStateOf(0) }
    var lastSecretTapAtMs by remember { mutableLongStateOf(0L) }

    fun onSettingsTabTapped() {
        val now = System.currentTimeMillis()
        secretTapCount = if (now - lastSecretTapAtMs <= SECRET_TAP_WINDOW_MS) secretTapCount + 1 else 1
        lastSecretTapAtMs = now
        if (secretTapCount >= SECRET_TAP_COUNT) {
            secretTapCount = 0
            onSecretLogViewerTriggered()
        }
    }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .navigationBarsPadding()
            .padding(horizontal = 22.dp, vertical = 10.dp),
        contentAlignment = Alignment.Center
    ) {
        Box(
            modifier = Modifier
                .shadow(
                    elevation = AugustElevation.HeroShadowElevation,
                    shape = shellShape,
                    ambientColor = AugustElevation.HeroShadowColor.copy(alpha = AugustElevation.HeroShadowAlpha),
                    spotColor = AugustElevation.HeroShadowColor.copy(alpha = AugustElevation.HeroShadowAlpha)
                )
                .clip(shellShape)
                .background(AugustColor.Navy.copy(alpha = 0.94f))
                .border(width = 1.dp, color = AugustColor.BorderDark, shape = shellShape)
                .padding(horizontal = 12.dp, vertical = 8.dp)
        ) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Sprint (2026-07-09): only 2 tabs remain (Today, Settings)
                // since History was removed, so this is now an explicit
                // 3-slot row -- tab, big centered refresh button, tab --
                // instead of a generic MainTab.values() loop.
                Glass20NavButton(
                    tab = MainTab.Today,
                    selected = selected == MainTab.Today,
                    onClick = { onSelected(MainTab.Today) }
                )
                Glass20RefreshButton(onClick = onRefreshClick)
                Glass20NavButton(
                    tab = MainTab.Settings,
                    selected = selected == MainTab.Settings,
                    onClick = {
                        onSettingsTabTapped()
                        onSelected(MainTab.Settings)
                    }
                )
            }
        }
    }
}

/**
 * August design system integration, phase 1 (see AugustTokens.kt). Was a
 * warm orange (sprint 2026-07-09) chosen specifically to be distinct from
 * every other accent in the app at the time. Under August, that rationale
 * inverts: "purple means action" (section 1.3, principle 4) makes the one
 * true Accent purple the *correct* color for the app's single most central
 * tappable action, not a mismatch -- so this is now literally
 * AugustColor.Accent rather than a fourth hue invented to stand apart from
 * activity/mind/violet (which are themselves now Accent/Accent Dark, see
 * HealthAccent in FinalBitLutShell.kt). Phase 4 widened its use to also
 * fill the selected tab in Glass20NavButton -- "action" and "selection"
 * are the same one-purple language under this system, not two competing
 * accents.
 */
private val NavAccent = AugustColor.Accent

/**
 * Centered, larger manual refresh button (sprint 2026-07-09), sitting
 * between the two tab buttons in the bottom nav. Reuses the same "sync now"
 * action as the Settings screen's manual sync button.
 *
 * August design system integration, phase 4 (see AugustTokens.kt): dropped
 * the fixed 360deg spin-on-tap -- it played unconditionally on every tap
 * regardless of whether a sync actually started, ran, or failed, so it was
 * confirming the tap, not the sync (the doc's "motion confirms" principle,
 * section 7). The press-scale below already confirms the tap. Wiring the
 * icon to a real spin while a sync is genuinely in flight would need this
 * composable to receive that state from its caller, which is a data-flow
 * change beyond this visual pass -- left as a follow-up, not done
 * speculatively here. Shadow is now the doc's "Accent action" shadow (see
 * AugustElevation.ButtonShadow* and PrimaryButton in FinalBitLutShell.kt),
 * since this button plays the same "single most central action" role a
 * Primary button does.
 */
@Composable
private fun Glass20RefreshButton(onClick: () -> Unit) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val shape = remember { RoundedCornerShape(30.dp) }

    val buttonScale by animateFloatAsState(
        targetValue = if (pressed) 0.92f else 1f,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "refreshButtonScale"
    )

    Box(
        modifier = Modifier
            .size(66.dp)
            .graphicsLayer {
                scaleX = buttonScale
                scaleY = buttonScale
            }
            .shadow(
                elevation = AugustElevation.ButtonShadowElevation,
                shape = shape,
                ambientColor = AugustElevation.ButtonShadowColor.copy(alpha = AugustElevation.ButtonShadowAlpha),
                spotColor = AugustElevation.ButtonShadowColor.copy(alpha = AugustElevation.ButtonShadowAlpha)
            )
            .clip(shape)
            .background(NavAccent)
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                onClick = onClick
            ),
        contentAlignment = Alignment.Center
    ) {
        Icon(
            imageVector = Icons.Rounded.Refresh,
            contentDescription = null,
            tint = Color.White,
            modifier = Modifier.size(30.dp)
        )
    }
}

@Composable
private fun Glass20NavButton(
    tab: MainTab,
    selected: Boolean,
    onClick: () -> Unit
) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val shape = remember { RoundedCornerShape(AugustRadius.Pill) }

    val iconTint by animateColorAsState(
        targetValue = if (selected) Color.White else AugustColor.DarkSecondaryText,
        animationSpec = tween(AugustMotion.DefaultMs, easing = AugustMotion.StandardEasing),
        label = "glass20NavIconTint"
    )
    val buttonScale by animateFloatAsState(
        targetValue = if (pressed) 0.92f else 1f,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "glass20NavButtonScale"
    )
    val fillAlpha by animateFloatAsState(
        targetValue = if (selected) 1f else 0f,
        animationSpec = tween(AugustMotion.DefaultMs, easing = AugustMotion.StandardEasing),
        label = "glass20NavFillAlpha"
    )

    Box(
        modifier = Modifier
            .size(54.dp)
            .graphicsLayer {
                scaleX = buttonScale
                scaleY = buttonScale
            }
            .clip(shape)
            .background(NavAccent.copy(alpha = fillAlpha))
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                onClick = onClick
            ),
        contentAlignment = Alignment.Center
    ) {
        Icon(
            imageVector = tab.icon,
            contentDescription = null,
            tint = iconTint,
            modifier = Modifier.size(24.dp)
        )
    }
}
'''


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
                f"after phases 1-3 have been applied)")

    print(f"==> Backing up touched files to {BACKUP_DIR.relative_to(ROOT)}")
    for rel in TARGET_FILES:
        backup_file(rel)

    print("==> Rewriting GlassNavigation.kt (August 'dark glass surface' nav)")
    path = ROOT / NAV
    current = path.read_text(encoding="utf-8")
    if current == GLASS_NAVIGATION_CONTENT:
        print("   (already applied, skipping) GlassNavigation.kt rewrite")
    else:
        path.write_text(GLASS_NAVIGATION_CONTENT, encoding="utf-8")
        print("   applied: GlassNavigation.kt rewrite")

    print("==> Removing now-dead palette param from Glass20BottomNavigation's call site")
    apply_edit(
        UI_SHELL,
        old='''            Glass20BottomNavigation(
                selected = selected,
                palette = palette,
                onSelected = { selected = it },
                onSecretLogViewerTriggered = { showLogViewer = true },
                onRefreshClick = onSyncNow
            )''',
        new='''            Glass20BottomNavigation(
                selected = selected,
                onSelected = { selected = it },
                onSecretLogViewerTriggered = { showLogViewer = true },
                onRefreshClick = onSyncNow
            )''',
        desc="remove palette argument (Glass20BottomNavigation no longer uses it)",
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
        ["git", "commit", "-m", "August design system integration, phase 4: navigation"],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("   (nothing to commit -- all edits were likely already applied)")
        return
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)
    print("==> Done: pushed to origin/main")


if __name__ == "__main__":
    main()
