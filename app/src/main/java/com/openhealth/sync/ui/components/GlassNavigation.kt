package com.openhealth.sync

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.openhealth.sync.ui.theme.AugustColor
import com.openhealth.sync.ui.theme.AugustElevation
import com.openhealth.sync.ui.theme.AugustMotion

private const val SECRET_TAP_COUNT = 5
private const val SECRET_TAP_WINDOW_MS = 2000L

// Nav bar outer margin (2026-08-22): was a flat 16.dp on both axes. Bumped
// horizontally only, to 24.dp, so the two side destination buttons (each
// weight(1f) inside the Row) shrink and the whole pill reads narrower --
// a deliberately conservative first pass rather than the ~44.dp a literal
// "20% narrower" derivation would produce on a typical ~400.dp-wide screen,
// since that number can't be visually verified in this environment. Tune
// this single constant after checking on-device; nothing else needs to
// change to adjust the width further in either direction.
private val NAV_BAR_OUTER_HORIZONTAL_MARGIN = 24.dp
private val NAV_BAR_OUTER_VERTICAL_MARGIN = 8.dp

/**
 * Compact August v3 navigation dock inspired by the 2026 Material 3 Expressive
 * short-navigation pattern: persistent destination labels, strong selected
 * state, generous targets, and motion driven by direct interaction state.
 *
 * Sync remains an action rather than pretending to be a navigation destination.
 * No blur dependency is required.
 */
@Composable
internal fun AugustBottomNav(
    selected: MainTab,
    onSelected: (MainTab) -> Unit,
    onSecretLogViewerTriggered: () -> Unit = {},
    onRefreshClick: () -> Unit = {}
) {
    var secretTapCount by remember { mutableIntStateOf(0) }
    var lastSecretTapAtMs by remember { mutableLongStateOf(0L) }
    val shellShape = remember { RoundedCornerShape(28.dp) }

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
            .padding(horizontal = NAV_BAR_OUTER_HORIZONTAL_MARGIN, vertical = NAV_BAR_OUTER_VERTICAL_MARGIN),
        contentAlignment = Alignment.Center
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .shadow(
                    elevation = AugustElevation.HeroShadowElevation,
                    shape = shellShape,
                    ambientColor = AugustElevation.HeroShadowColor.copy(alpha = AugustElevation.HeroShadowAlpha),
                    spotColor = AugustElevation.HeroShadowColor.copy(alpha = AugustElevation.HeroShadowAlpha)
                )
                .clip(shellShape)
                .background(AugustColor.Navy)
                .border(1.dp, AugustColor.BorderDark, shellShape)
                .padding(horizontal = 8.dp, vertical = 7.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            AugustDestination(
                modifier = Modifier.weight(1f),
                tab = MainTab.Today,
                selected = selected == MainTab.Today,
                onClick = { onSelected(MainTab.Today) }
            )
            AugustSyncAction(onClick = onRefreshClick)
            AugustDestination(
                modifier = Modifier.weight(1f),
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

@Composable
private fun AugustDestination(
    modifier: Modifier,
    tab: MainTab,
    selected: Boolean,
    onClick: () -> Unit
) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val focused by interactionSource.collectIsFocusedAsState()
    val shape = remember { RoundedCornerShape(20.dp) }
    val iconShape = remember { RoundedCornerShape(11.dp) }
    val label = when (tab) {
        MainTab.Today -> stringResource(R.string.tab_today)
        MainTab.Settings -> stringResource(R.string.tab_settings)
    }

    val container by animateColorAsState(
        targetValue = if (selected) AugustColor.Surface else Color.Transparent,
        animationSpec = tween(AugustMotion.DefaultMs, easing = AugustMotion.StandardEasing),
        label = "destinationContainer"
    )
    val contentColor by animateColorAsState(
        targetValue = if (selected) AugustColor.Ink else AugustColor.DarkSecondaryText,
        animationSpec = tween(AugustMotion.DefaultMs, easing = AugustMotion.StandardEasing),
        label = "destinationContent"
    )
    val iconTile by animateColorAsState(
        targetValue = if (selected) AugustColor.Lime else AugustColor.NavySoft,
        animationSpec = tween(AugustMotion.DefaultMs, easing = AugustMotion.StandardEasing),
        label = "destinationIconTile"
    )
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.96f else 1f,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "destinationPressScale"
    )
    val iconSize by animateDpAsState(
        targetValue = if (selected) 21.dp else 20.dp,
        animationSpec = tween(AugustMotion.DefaultMs, easing = AugustMotion.StandardEasing),
        label = "destinationIconSize"
    )

    Column(
        modifier = modifier
            .height(58.dp)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            }
            .clip(shape)
            .background(container)
            .border(
                width = if (focused) 2.dp else 0.dp,
                color = if (focused) AugustColor.Purple else Color.Transparent,
                shape = shape
            )
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                role = Role.Tab,
                onClick = onClick
            )
            .padding(horizontal = 6.dp, vertical = 5.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Box(
            modifier = Modifier
                .size(30.dp)
                .clip(iconShape)
                .background(iconTile),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = tab.icon,
                contentDescription = label,
                tint = if (selected) AugustColor.LimeInk else contentColor,
                modifier = Modifier.size(iconSize)
            )
        }
        Spacer(Modifier.height(3.dp))
        Text(
            text = label,
            color = contentColor,
            fontWeight = if (selected) FontWeight.ExtraBold else FontWeight.SemiBold,
            fontSize = 10.sp,
            maxLines = 1
        )
    }
}

@Composable
private fun AugustSyncAction(onClick: () -> Unit) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val focused by interactionSource.collectIsFocusedAsState()
    val shape = remember { RoundedCornerShape(20.dp) }
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.94f else 1f,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "syncPressScale"
    )
    val rotation by animateFloatAsState(
        targetValue = if (pressed) -24f else 0f,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "syncPressRotation"
    )
    val fill by animateColorAsState(
        // Tangerine (2026-08-22), was Lime/LimeActive. Size bumped 15%
        // (58.dp -> 67.dp, icon 27.dp -> 31.dp: 58*1.15=66.7 rounded to
        // 67.dp) to read as the visually dominant middle action against the
        // now-narrower side destination buttons. The existing press
        // animation (scale to 0.94, -24deg icon rotation, fill darkening)
        // is unchanged -- it already covers the "light press animation"
        // this button needed; only the color/size changed.
        targetValue = if (pressed) AugustColor.TangerineActive else AugustColor.Tangerine,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "syncFill"
    )

    Box(
        modifier = Modifier
            .size(67.dp)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
                translationY = -2.dp.toPx()
            }
            .shadow(
                elevation = AugustElevation.ButtonShadowElevation,
                shape = shape,
                ambientColor = AugustColor.Tangerine.copy(alpha = 0.18f),
                spotColor = AugustColor.Tangerine.copy(alpha = 0.18f)
            )
            .clip(shape)
            .background(fill)
            .border(
                width = if (focused) 2.dp else 0.dp,
                color = if (focused) AugustColor.Purple else Color.Transparent,
                shape = shape
            )
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                role = Role.Button,
                onClick = onClick
            ),
        contentAlignment = Alignment.Center
    ) {
        Icon(
            imageVector = Icons.Rounded.Refresh,
            contentDescription = stringResource(R.string.sync_now),
            tint = AugustColor.Ink,
            modifier = Modifier
                .size(31.dp)
                .graphicsLayer { rotationZ = rotation }
        )
    }
}
