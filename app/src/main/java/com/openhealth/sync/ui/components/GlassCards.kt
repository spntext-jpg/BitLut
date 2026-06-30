package com.openhealth.sync

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.unit.dp

@Composable
internal fun SoftCard(
    palette: BitPalette,
    modifier: Modifier = Modifier.fillMaxWidth(),
    accent: Color = palette.activity,
    hero: Boolean = false,
    tintWithAccent: Boolean = false,
    content: @Composable ColumnScope.() -> Unit
) {
    val shape = remember(hero) { RoundedCornerShape(if (hero) 34.dp else 28.dp) }
    val targetCardColor = if (palette.dark) {
        lerp(palette.card, accent, if (hero || tintWithAccent) 0.12f else 0.07f)
    } else {
        lerp(palette.card, accent, if (hero || tintWithAccent) 0.045f else 0.025f)
    }
    val bg by animateColorAsState(targetCardColor, label = "glass20CardBg")
    val backgroundBrush = remember(bg, palette.systemBackground, palette.dark) {
        Brush.linearGradient(
            listOf(
                bg.copy(alpha = if (palette.dark) 0.86f else 0.90f),
                bg.copy(alpha = if (palette.dark) 0.62f else 0.72f),
                palette.systemBackground.copy(alpha = if (palette.dark) 0.16f else 0.28f)
            )
        )
    }
    val accentGlowColors = remember(accent, hero) {
        listOf(accent.copy(alpha = if (hero) 0.22f else 0.15f), Color.Transparent)
    }
    val mindGlowColors = remember(palette.mind, hero) {
        listOf(palette.mind.copy(alpha = if (hero) 0.14f else 0.08f), Color.Transparent)
    }

    Column(
        modifier = modifier
            .shadow(
                elevation = if (hero) 36.dp else 24.dp,
                shape = shape,
                ambientColor = Color.Black.copy(alpha = if (palette.dark) 0.32f else 0.06f),
                spotColor = accent.copy(alpha = if (palette.dark) 0.24f else 0.12f)
            )
            .clip(shape)
            .background(backgroundBrush)
            .drawBehind {
                drawRect(
                    brush = Brush.radialGradient(
                        colors = accentGlowColors,
                        center = Offset(size.width * 0.88f, size.height * 0.08f),
                        radius = size.maxDimension * 0.62f
                    )
                )
                drawRect(
                    brush = Brush.radialGradient(
                        colors = mindGlowColors,
                        center = Offset(size.width * 0.10f, size.height * 0.98f),
                        radius = size.maxDimension * 0.58f
                    )
                )
                drawLine(
                    color = Color.White.copy(alpha = if (palette.dark) 0.15f else 0.36f),
                    start = Offset(size.width * 0.08f, 1.1f),
                    end = Offset(size.width * 0.92f, 1.1f),
                    strokeWidth = 1.1f
                )
            }
            .border(
                width = 1.dp,
                color = palette.stroke.copy(alpha = if (palette.dark) 0.70f else 0.50f),
                shape = shape
            )
            .padding(if (hero) 24.dp else 16.dp),
        content = content
    )
}
