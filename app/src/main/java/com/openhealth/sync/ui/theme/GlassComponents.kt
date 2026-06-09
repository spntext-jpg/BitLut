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

@Composable
fun MeshBackground(modifier: Modifier = Modifier) {
    val infinite = rememberInfiniteTransition(label = "mesh")
    val shift by infinite.animateFloat(
        initialValue = 0f, targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(12000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ), label = "meshShift"
    )
    Box(
        modifier = modifier
            .fillMaxSize()
            .drawBehind {
                drawRect(color = Void)
                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(Color(0x556366F1), Color(0x006366F1)),
                        center = Offset(size.width * (0.1f + shift * 0.15f), size.height * (0.05f + shift * 0.1f)),
                        radius = size.width * 0.55f
                    ),
                    radius = size.width * 0.55f,
                    center = Offset(size.width * (0.1f + shift * 0.15f), size.height * (0.05f + shift * 0.1f))
                )
                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(Color(0x2234D399), Color(0x0034D399)),
                        center = Offset(size.width * (0.85f - shift * 0.1f), size.height * (0.75f + shift * 0.08f)),
                        radius = size.width * 0.45f
                    ),
                    radius = size.width * 0.45f,
                    center = Offset(size.width * (0.85f - shift * 0.1f), size.height * (0.75f + shift * 0.08f))
                )
                drawRect(
                    brush = Brush.linearGradient(
                        colors = listOf(Color(0x00000000), Color(0x156366F1), Color(0x00000000)),
                        start = Offset(0f, size.height * 0.35f),
                        end = Offset(size.width, size.height * 0.65f)
                    )
                )
            }
    )
}

fun Modifier.glowEffect(color: Color = GlowIndigo, radius: Dp = 20.dp): Modifier = this.drawBehind {
    drawIntoCanvas { canvas ->
        val paint = Paint().apply {
            asFrameworkPaint().apply {
                isAntiAlias = true
                this.color = android.graphics.Color.TRANSPARENT
                setShadowLayer(radius.toPx(), 0f, 0f, color.copy(alpha = 0.4f).toArgb())
            }
        }
        canvas.drawRoundRect(0f, 0f, size.width, size.height, 24.dp.toPx(), 24.dp.toPx(), paint)
    }
}

@Composable
fun GlassCard(
    modifier: Modifier = Modifier,
    shape: RoundedCornerShape = RoundedCornerShape(24.dp),
    glowColor: Color = GlowIndigo,
    glowRadius: Dp = 24.dp,
    content: @Composable BoxScope.() -> Unit
) {
    Box(
        modifier = modifier
            .glowEffect(glowColor, glowRadius)
            .clip(shape)
            .background(
                Brush.linearGradient(
                    colors = listOf(Color(0x1AFFFFFF), Color(0x08FFFFFF)),
                    start = Offset(0f, 0f),
                    end = Offset(1000f, 1000f)
                )
            )
            .border(
                BorderStroke(
                    width = 1.dp,
                    brush = Brush.linearGradient(
                        colors = listOf(Color(0x30FFFFFF), Color(0x08FFFFFF), Color(0x18FFFFFF))
                    )
                ),
                shape = shape
            ),
        content = content
    )
}

@Composable
fun PulsingGlowBorder(
    color: Color,
    shape: RoundedCornerShape = RoundedCornerShape(24.dp),
    modifier: Modifier = Modifier,
    content: @Composable BoxScope.() -> Unit
) {
    val infinite = rememberInfiniteTransition(label = "glow_pulse")
    val alpha by infinite.animateFloat(
        initialValue = 0.3f, targetValue = 0.8f,
        animationSpec = infiniteRepeatable(
            animation = tween(2000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ), label = "glowAlpha"
    )
    Box(
        modifier = modifier
            .glowEffect(color.copy(alpha = alpha), 16.dp)
            .clip(shape)
            .background(
                Brush.linearGradient(
                    colors = listOf(Color(0x1AFFFFFF), Color(0x08FFFFFF)),
                    start = Offset(0f, 0f), end = Offset(1000f, 1000f)
                )
            )
            .border(
                BorderStroke(
                    width = 1.5.dp,
                    brush = Brush.linearGradient(
                        colors = listOf(
                            color.copy(alpha = alpha),
                            color.copy(alpha = alpha * 0.3f),
                            color.copy(alpha = alpha)
                        )
                    )
                ),
                shape = shape
            ),
        content = content
    )
}
