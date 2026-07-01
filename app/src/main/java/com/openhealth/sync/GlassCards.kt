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

/**
 * Warm slate shadow tone for light theme (v1.9.11), used instead of pure
 * black. A pure-black ambient shadow on a near-white card reads as a flat,
 * generic Material default; a warm, slightly tinted shadow (the same trick
 * Linear/Apple-style premium UIs use) gives the card a sense of being lit
 * from a real light source instead of just "darkened at the edges".
 */
private val LightShadowTint = Color(0xFF2B2620)

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
        // Light-theme tint strengthened (v1.9.11): 0.045f/0.025f read as
        // almost untinted white next to dark theme's much richer 0.12f/0.07f,
        // which is the single biggest reason light mode felt visibly less
        // premium than dark mode. This keeps the card unmistakably white at a
        // glance (still far below dark mode's saturation) while making the
        // accent hue actually perceptible instead of nearly invisible.
        lerp(palette.card, accent, if (hero || tintWithAccent) 0.085f else 0.05f)
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
    val accentGlowColors = remember(accent, hero, palette.dark) {
        listOf(accent.copy(alpha = if (hero) (if (palette.dark) 0.22f else 0.16f) else (if (palette.dark) 0.15f else 0.11f)), Color.Transparent)
    }
    val mindGlowColors = remember(palette.mind, hero, palette.dark) {
        listOf(palette.mind.copy(alpha = if (hero) (if (palette.dark) 0.14f else 0.10f) else (if (palette.dark) 0.08f else 0.06f)), Color.Transparent)
    }

    Column(
        modifier = modifier
            .shadow(
                elevation = if (hero) 36.dp else 24.dp,
                shape = shape,
                // Light-theme shadow strengthened from a near-invisible 0.06f
                // pure-black ambient to a warm slate tone with real presence,
                // matching dark theme's sense of physical depth instead of
                // sitting almost flush with the page.
                ambientColor = if (palette.dark) Color.Black.copy(alpha = 0.32f) else LightShadowTint.copy(alpha = 0.14f),
                spotColor = accent.copy(alpha = if (palette.dark) 0.24f else 0.16f)
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
                color = palette.stroke.copy(alpha = if (palette.dark) 0.70f else 0.62f),
                shape = shape
            )
            .padding(if (hero) 24.dp else 16.dp),
        content = content
    )
}
