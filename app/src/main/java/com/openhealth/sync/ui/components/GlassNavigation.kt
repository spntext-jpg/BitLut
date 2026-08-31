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
import androidx.compose.foundation.layout.width
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.openhealth.sync.ui.theme.AugustColor
import com.openhealth.sync.ui.theme.AugustMotion

private const val SECRET_TAP_COUNT = 5
private const val SECRET_TAP_WINDOW_MS = 2000L
private val NAV_BAR_OUTER_HORIZONTAL_MARGIN = 24.dp
private val NAV_BAR_OUTER_VERTICAL_MARGIN = 8.dp

// 2026-08-30: navbar rebuild. The previous resize shrank destination
// buttons' HEIGHT (58->46dp) to make them read as secondary next to the
// Refresh action, but a Row.weight(1f) child's *height* has nothing to do
// with how prominent it looks relative to a sibling -- only *width* does,
// and the 46dp fixed height was too short for a 24dp icon + spacer + 10sp
// label to lay out without the label clipping (confirmed: 24 + 3 + ~13
// text line height already exceeds the 36dp inner budget left after 5dp
// top/bottom padding). Fix: every control in the bar now shares one
// common height so nothing clips or looks vertically lopsided; visual
// hierarchy (Refresh reads as the primary action) comes entirely from
// Refresh being wider than a destination button, not taller.
// BITLUT_NAVBAR_REBUILD_2026_08_30
private val NAV_BAR_CONTROL_HEIGHT = 64.dp
private val NAV_BAR_SYNC_ACTION_WIDTH = 84.dp

/** Compact two-destination dock with one explicit sync action. */
@Composable
internal fun AugustBottomNav(
    selected: MainTab,
    onSelected: (MainTab) -> Unit,
    onSecretLogViewerTriggered: () -> Unit = {},
    onRefreshClick: () -> Unit = {}
) {
    var secretTapCount by remember { mutableIntStateOf(0) }
    var lastSecretTapAtMs by remember { mutableLongStateOf(0L) }
    val shellShape = remember { RoundedCornerShape(30.dp) }

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
                .clip(shellShape)
                .background(AugustColor.Navy)
                .border(1.dp, AugustColor.BorderDark, shellShape)
                .padding(horizontal = 8.dp, vertical = 7.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
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
    val shape = remember { RoundedCornerShape(22.dp) }
    val iconShape = remember { RoundedCornerShape(10.dp) }
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
        targetValue = if (pressed) 0.98f else 1f,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "destinationPressScale"
    )
    val iconSize by animateDpAsState(
        targetValue = if (selected) 18.dp else 17.dp,
        animationSpec = tween(AugustMotion.DefaultMs, easing = AugustMotion.StandardEasing),
        label = "destinationIconSize"
    )

    Column(
        modifier = modifier
            .height(NAV_BAR_CONTROL_HEIGHT)
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
            .padding(horizontal = 6.dp, vertical = 6.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Box(
            modifier = Modifier
                .size(26.dp)
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
        Spacer(Modifier.height(4.dp))
        Text(
            text = label,
            color = contentColor,
            fontWeight = if (selected) FontWeight.ExtraBold else FontWeight.SemiBold,
            fontSize = 11.sp,
            maxLines = 1
        )
    }
}

@Composable
private fun AugustSyncAction(onClick: () -> Unit) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val focused by interactionSource.collectIsFocusedAsState()
    val shape = remember { RoundedCornerShape(24.dp) }
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.97f else 1f,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "syncPressScale"
    )
    val rotation by animateFloatAsState(
        targetValue = if (pressed) -12f else 0f,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "syncPressRotation"
    )
    val fill by animateColorAsState(
        targetValue = if (pressed) AugustColor.TangerineActive else AugustColor.Tangerine,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "syncFill"
    )

    // Same shared height as AugustDestination (NAV_BAR_CONTROL_HEIGHT) so
    // the whole bar aligns on one baseline; a wider fixed width (rather
    // than a taller box) is what makes this read as the primary action,
    // per the 2026-08-30 navbar rebuild note above.
    Box(
        modifier = Modifier
            .width(NAV_BAR_SYNC_ACTION_WIDTH)
            .height(NAV_BAR_CONTROL_HEIGHT)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            }
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
                .size(32.dp)
                .graphicsLayer { rotationZ = rotation }
        )
    }
}
