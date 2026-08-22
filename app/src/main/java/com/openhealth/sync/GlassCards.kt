
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
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import com.openhealth.sync.ui.theme.AugustColor
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
 *   - tintWithAccent remains in the public signature only for compatibility
 *     with existing call sites. August v3 keeps card fill and border neutral;
 *     semantic Lime/Purple accents belong to content, progress, focus, or
 *     actions inside the surface instead of tinting every card boundary.
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
        targetValue = if (hero) AugustColor.NavyRaised else palette.card,
        animationSpec = tween(AugustMotion.FastMs),
        label = "softCardBg"
    )
    // August v3: cards use quiet neutral borders. Brand colors belong inside
    // the component (icon/progress/action), not around every surface.
    val borderColor = if (hero) AugustColor.BorderDark else palette.stroke

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
