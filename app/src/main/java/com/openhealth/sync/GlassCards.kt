package com.openhealth.sync

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.ui.unit.dp
import com.openhealth.sync.ui.theme.AugustColor
import com.openhealth.sync.ui.theme.AugustElevation
import com.openhealth.sync.ui.theme.AugustRadius
import com.openhealth.sync.ui.theme.AugustSpace

/**
 * Canonical BitLut card surface.
 *
 * Cards are deliberately quiet: neutral fill, one subtle outline and no
 * interaction animation unless the caller itself is clickable. Hero cards keep
 * a restrained shadow to preserve hierarchy. This prevents non-actionable
 * dashboard cards from behaving like buttons and keeps the surface model close
 * to modern, content-first mobile UI.
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
    val borderColor = if (hero) AugustColor.BorderDark else palette.stroke
    val shadowModifier = if (hero) {
        Modifier.shadow(
            elevation = AugustElevation.HeroShadowElevation,
            shape = shape,
            ambientColor = AugustElevation.HeroShadowColor.copy(alpha = AugustElevation.HeroShadowAlpha),
            spotColor = AugustElevation.HeroShadowColor.copy(alpha = AugustElevation.HeroShadowAlpha)
        )
    } else {
        Modifier
    }

    Column(
        modifier = modifier
            .then(shadowModifier)
            .clip(shape)
            .background(background)
            .border(width = 1.dp, color = borderColor, shape = shape)
            .padding(if (hero) AugustSpace.s24 else AugustSpace.s18),
        content = content
    )
}
