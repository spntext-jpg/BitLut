
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp
import com.openhealth.sync.ui.theme.AugustColor
import com.openhealth.sync.ui.theme.AugustElevation
import com.openhealth.sync.ui.theme.AugustGlass
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
                .background(AugustGlass.ShellUndertint)
                .background(Brush.verticalGradient(listOf(AugustGlass.ShellTint, Color.Transparent)))
                .border(
                    width = AugustGlass.ShellBorderWidth,
                    brush = Brush.verticalGradient(listOf(AugustGlass.SpecularTop, AugustGlass.SpecularBottom)),
                    shape = shellShape
                )
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
