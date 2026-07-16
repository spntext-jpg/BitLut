package com.openhealth.sync

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp

@Composable
internal fun Glass20BottomNavigation(
    selected: MainTab,
    palette: BitPalette,
    onSelected: (MainTab) -> Unit
) {
    val shellShape = remember { RoundedCornerShape(34.dp) }
    val shellBackground = remember(palette.card, palette.systemBackground, palette.dark) {
        Brush.linearGradient(
            listOf(
                palette.card.copy(alpha = if (palette.dark) 0.76f else 0.74f),
                palette.card.copy(alpha = if (palette.dark) 0.46f else 0.54f),
                palette.systemBackground.copy(alpha = if (palette.dark) 0.28f else 0.38f)
            )
        )
    }
    val activityGlowColors = remember(palette.activity) {
        listOf(palette.activity.copy(alpha = 0.22f), Color.Transparent)
    }
    val mindGlowColors = remember(palette.mind) {
        listOf(palette.mind.copy(alpha = 0.18f), Color.Transparent)
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
                    elevation = 40.dp,
                    shape = shellShape,
                    ambientColor = Color.Black.copy(alpha = if (palette.dark) 0.34f else 0.09f),
                    spotColor = palette.activity.copy(alpha = if (palette.dark) 0.32f else 0.14f)
                )
                .clip(shellShape)
                .background(shellBackground)
                .drawBehind {
                    drawRect(
                        brush = Brush.radialGradient(
                            colors = activityGlowColors,
                            center = Offset(size.width * 0.14f, size.height * 0.08f),
                            radius = size.maxDimension * 0.72f
                        )
                    )
                    drawRect(
                        brush = Brush.radialGradient(
                            colors = mindGlowColors,
                            center = Offset(size.width * 0.92f, size.height * 0.92f),
                            radius = size.maxDimension * 0.84f
                        )
                    )
                    drawLine(
                        color = Color.White.copy(alpha = if (palette.dark) 0.18f else 0.46f),
                        start = Offset(size.width * 0.08f, 1.2f),
                        end = Offset(size.width * 0.92f, 1.2f),
                        strokeWidth = 1.2f
                    )
                }
                .border(
                    width = 1.dp,
                    color = palette.stroke.copy(alpha = if (palette.dark) 0.72f else 0.52f),
                    shape = shellShape
                )
                .padding(horizontal = 12.dp, vertical = 8.dp)
        ) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                MainTab.values().forEach { tab ->
                    Glass20NavButton(
                        tab = tab,
                        selected = selected == tab,
                        palette = palette,
                        onClick = { onSelected(tab) }
                    )
                }
            }
        }
    }
}

@Composable
private fun Glass20NavButton(
    tab: MainTab,
    selected: Boolean,
    palette: BitPalette,
    onClick: () -> Unit
) {
    val interactionSource = remember { MutableInteractionSource() }
    val shape = remember { RoundedCornerShape(26.dp) }
    val selectedHighlightShape = remember { RoundedCornerShape(99.dp) }
    val iconTint by animateColorAsState(
        targetValue = if (selected) Color.White else palette.secondaryText.copy(alpha = 0.84f),
        label = "glass20NavIconTint"
    )
    val scale by animateFloatAsState(
        targetValue = if (selected) 1.0f else 0.94f,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessLow
        ),
        label = "glass20NavScale"
    )
    val selectedBrush = remember(palette.activity, palette.mind) {
        Brush.linearGradient(
            listOf(
                palette.activity.copy(alpha = 0.98f),
                palette.mind.copy(alpha = 0.76f),
                palette.activity.copy(alpha = 0.30f)
            )
        )
    }
    val idleBrush = remember(palette.card, palette.dark) {
        Brush.linearGradient(
            listOf(
                Color.White.copy(alpha = if (palette.dark) 0.08f else 0.34f),
                palette.card.copy(alpha = if (palette.dark) 0.05f else 0.18f)
            )
        )
    }
    val selectedGlowColors = remember {
        listOf(Color.White.copy(alpha = 0.34f), Color.Transparent)
    }

    Box(
        modifier = Modifier
            .size(54.dp)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            }
            .pressScale(interactionSource)
            .clip(shape)
            .background(if (selected) selectedBrush else idleBrush)
            .drawBehind {
                if (selected) {
                    drawRect(
                        brush = Brush.radialGradient(
                            colors = selectedGlowColors,
                            center = Offset(size.width * 0.34f, size.height * 0.12f),
                            radius = size.maxDimension * 0.70f
                        )
                    )
                }
            }
            .border(
                width = 1.dp,
                color = if (selected) {
                    Color.White.copy(alpha = 0.34f)
                } else {
                    palette.stroke.copy(alpha = if (palette.dark) 0.38f else 0.32f)
                },
                shape = shape
            )
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
            modifier = Modifier.size(if (selected) 27.dp else 24.dp)
        )

        if (selected) {
            Box(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 6.dp)
                    .size(width = 16.dp, height = 3.dp)
                    .clip(selectedHighlightShape)
                    .background(Color.White.copy(alpha = 0.72f))
            )
        }
    }
}
