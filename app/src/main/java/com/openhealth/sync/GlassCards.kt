package com.openhealth.sync

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import com.openhealth.sync.ui.theme.AugustColor
import com.openhealth.sync.ui.theme.AugustElevation
import com.openhealth.sync.ui.theme.AugustRadius
import com.openhealth.sync.ui.theme.AugustSpace

/**
 * Canonical BitLut card surface.
 *
 * 2026 minimalist pass: cards are borderless, separated from the
 * background by a soft ambient shadow instead of a 1dp stroke (Apple
 * Health / iOS card convention). No interaction animation unless the
 * caller itself is clickable. Hero cards keep their own, stronger shadow
 * to preserve hierarchy.
 */
@Composable
internal fun SoftCard(
    palette: BitPalette,
    modifier: Modifier = Modifier.fillMaxWidth(),
    hero: Boolean = false,
    content: @Composable ColumnScope.() -> Unit
) {
    val shape = remember(hero) {
        RoundedCornerShape(if (hero) AugustRadius.Hero else AugustRadius.Card)
    }
    val background = if (hero) AugustColor.NavyRaised else palette.card
    val shadowElevation = if (hero) AugustElevation.HeroShadowElevation else AugustElevation.CardShadowElevation
    val shadowColor = if (hero) AugustElevation.HeroShadowColor else AugustElevation.CardShadowColor
    val shadowAlpha = if (hero) AugustElevation.HeroShadowAlpha else AugustElevation.CardShadowAlpha

    Column(
        modifier = modifier
            .shadow(
                elevation = shadowElevation,
                shape = shape,
                ambientColor = shadowColor.copy(alpha = shadowAlpha),
                spotColor = shadowColor.copy(alpha = shadowAlpha)
            )
            .clip(shape)
            .background(background)
            .padding(if (hero) AugustSpace.s28 else AugustSpace.s20),
        content = content
    )
}
