package com.openhealth.sync.ui.theme

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Paint
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

// ── Mesh background with brand gradient ───────────────────────────────────────

@Composable
fun MeshBackground(modifier: Modifier = Modifier) {
    val infinite = rememberInfiniteTransition(label = "mesh")
    val shift by infinite.animateFloat(
        initialValue = 0f, targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(14000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ), label = "meshShift"
    )

    Box(
        modifier = modifier
            .fillMaxSize()
            .drawBehind {
                // Base: brand gradient #0A1428 → #1D2B53 → #4B1D8C
                drawRect(
                    brush = Brush.linearGradient(
                        colors = listOf(GradStart, GradMid, GradEnd),
                        start = Offset(0f, 0f),
                        end = Offset(size.width, size.height)
                    )
                )
                // Blue nebula top-left — #19AEF9
                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(Color(0x4019AEF9), Color(0x0019AEF9)),
                        center = Offset(size.width * (0.05f + shift * 0.1f), size.height * 0.1f),
                        radius = size.width * 0.5f
                    ),
                    radius = size.width * 0.5f,
                    center = Offset(size.width * (0.05f + shift * 0.1f), size.height * 0.1f)
                )
                // Purple nebula bottom-right — #8B5CF6
                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(Color(0x358B5CF6), Color(0x008B5CF6)),
                        center = Offset(size.width * (0.9f - shift * 0.08f), size.height * (0.8f + shift * 0.05f)),
                        radius = size.width * 0.45f
                    ),
                    radius = size.width * 0.45f,
                    center = Offset(size.width * (0.9f - shift * 0.08f), size.height * (0.8f + shift * 0.05f))
                )
                // Subtle orange accent center — #FF9839
                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(Color(0x18FF9839), Color(0x00FF9839)),
                        center = Offset(size.width * 0.5f, size.height * (0.4f + shift * 0.1f)),
                        radius = size.width * 0.3f
                    ),
                    radius = size.width * 0.3f,
                    center = Offset(size.width * 0.5f, size.height * (0.4f + shift * 0.1f))
                )
            }
    )
}

// ── Glow shadow effect ────────────────────────────────────────────────────────

fun Modifier.glowEffect(color: Color = GlowBlue, radius: Dp = 24.dp): Modifier = this.drawBehind {
    drawIntoCanvas { canvas ->
        val paint = Paint().apply {
            asFrameworkPaint().apply {
                isAntiAlias = true
                this.color = android.graphics.Color.TRANSPARENT
                setShadowLayer(radius.toPx(), 0f, 4f, color.copy(alpha = 0.35f).toArgb())
            }
        }
        canvas.drawRoundRect(0f, 0f, size.width, size.height, 24.dp.toPx(), 24.dp.toPx(), paint)
    }
}

// ── Glass card — rgba(255,255,255,0.04) + border rgba(255,255,255,0.08) ───────

@Composable
fun GlassCard(
    modifier: Modifier = Modifier,
    shape: RoundedCornerShape = RoundedCornerShape(16.dp),
    glowColor: Color = Color.Transparent,
    glowRadius: Dp = 20.dp,
    content: @Composable BoxScope.() -> Unit
) {
    val glowMod = if (glowColor != Color.Transparent) modifier.glowEffect(glowColor, glowRadius) else modifier
    Box(
        modifier = glowMod
            .clip(shape)
            .background(
                Brush.linearGradient(
                    colors = listOf(Color(0x0FFFFFFF), Color(0x06FFFFFF)),
                    start = Offset(0f, 0f),
                    end = Offset(800f, 800f)
                )
            )
            .border(
                BorderStroke(
                    1.dp,
                    Brush.linearGradient(
                        colors = listOf(Color(0x14FFFFFF), Color(0x08FFFFFF), Color(0x10FFFFFF))
                    )
                ),
                shape = shape
            ),
        content = content
    )
}

// ── Pulsing glow border for connected/active state ────────────────────────────

@Composable
fun PulsingGlowBorder(
    color: Color,
    shape: RoundedCornerShape = RoundedCornerShape(16.dp),
    modifier: Modifier = Modifier,
    content: @Composable BoxScope.() -> Unit
) {
    val infinite = rememberInfiniteTransition(label = "pulse")
    val alpha by infinite.animateFloat(
        initialValue = 0.25f, targetValue = 0.7f,
        animationSpec = infiniteRepeatable(
            animation = tween(2200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ), label = "pulseAlpha"
    )
    Box(
        modifier = modifier
            .glowEffect(color.copy(alpha = alpha), 16.dp)
            .clip(shape)
            .background(
                Brush.linearGradient(
                    colors = listOf(Color(0x0FFFFFFF), Color(0x06FFFFFF)),
                    start = Offset(0f, 0f), end = Offset(800f, 800f)
                )
            )
            .border(
                BorderStroke(
                    1.5.dp,
                    Brush.linearGradient(
                        colors = listOf(color.copy(alpha = alpha), color.copy(alpha = alpha * 0.3f), color.copy(alpha = alpha))
                    )
                ),
                shape = shape
            ),
        content = content
    )
}
