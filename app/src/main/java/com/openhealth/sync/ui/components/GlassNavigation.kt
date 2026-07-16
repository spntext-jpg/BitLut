package com.openhealth.sync

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.animateDpAsState
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
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp

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

@Composable
internal fun Glass20BottomNavigation(
    selected: MainTab,
    palette: BitPalette,
    onSelected: (MainTab) -> Unit,
    onSecretLogViewerTriggered: () -> Unit = {},
    onRefreshClick: () -> Unit = {}
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
                // Sprint (2026-07-09): only 2 tabs remain (Today, Settings)
                // since History was removed, so this is now an explicit
                // 3-slot row -- tab, big centered refresh button, tab --
                // instead of a generic MainTab.values() loop.
                Glass20NavButton(
                    tab = MainTab.Today,
                    selected = selected == MainTab.Today,
                    palette = palette,
                    onClick = { onSelected(MainTab.Today) }
                )
                Glass20RefreshButton(onClick = onRefreshClick)
                Glass20NavButton(
                    tab = MainTab.Settings,
                    selected = selected == MainTab.Settings,
                    palette = palette,
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
 * Warm orange, sprint 2026-07-09: distinct from every existing accent
 * (activity/mind/violet) on purpose, so the refresh button reads as its
 * own clearly-tappable action rather than belonging to either tab.
 */
private val WarmRefreshOrange = Color(0xFFFF8A34)

/**
 * Centered, larger, warm-orange manual refresh button (sprint 2026-07-09),
 * sitting between the two tab buttons in the bottom nav. Reuses the same
 * "sync now" action as the Settings screen's manual sync button.
 */
@Composable
private fun Glass20RefreshButton(onClick: () -> Unit) {
    val interactionSource = remember { MutableInteractionSource() }
    val shape = remember { RoundedCornerShape(30.dp) }
    val brush = remember {
        Brush.linearGradient(
            listOf(WarmRefreshOrange, WarmRefreshOrange.copy(alpha = 0.84f))
        )
    }
    val glowColors = remember {
        listOf(Color.White.copy(alpha = 0.30f), Color.Transparent)
    }
    Box(
        modifier = Modifier
            .size(66.dp)
            .shadow(
                elevation = 16.dp,
                shape = shape,
                ambientColor = WarmRefreshOrange.copy(alpha = 0.40f),
                spotColor = WarmRefreshOrange.copy(alpha = 0.55f)
            )
            .pressScale(interactionSource)
            .clip(shape)
            .background(brush)
            .drawBehind {
                drawRect(
                    brush = Brush.radialGradient(
                        colors = glowColors,
                        center = Offset(size.width * 0.32f, size.height * 0.14f),
                        radius = size.maxDimension * 0.66f
                    )
                )
            }
            .border(width = 1.dp, color = Color.White.copy(alpha = 0.30f), shape = shape)
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
    // Animated: was a hard `if (selected) 27.dp else 24.dp` snap with no
    // transition -- every other state change in this button (tint, scale,
    // glow) animates smoothly, so the icon instantly jumping 3dp on tab
    // switch was the one visibly "cheap" moment. Same spring profile as the
    // button's own selection [scale] below, so both animations read as one
    // coordinated motion.
    val iconSize by animateDpAsState(
        targetValue = if (selected) 27.dp else 24.dp,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessLow
        ),
        label = "glass20NavIconSize"
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
            modifier = Modifier.size(iconSize)
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
