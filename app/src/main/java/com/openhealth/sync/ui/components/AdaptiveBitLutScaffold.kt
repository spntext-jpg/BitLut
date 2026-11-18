package com.openhealth.sync

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.FitnessCenter
import androidx.compose.material.icons.rounded.Home
import androidx.compose.material.icons.rounded.Restaurant
import androidx.compose.material.icons.rounded.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.openhealth.sync.ui.theme.AugustColor

/** Uses the actual available window, including split-screen, rather than physical device size. */
@Composable
internal fun AdaptiveBitLutScaffold(
    selected: MainTab,
    onSelected: (MainTab) -> Unit,
    containerColor: Color,
    bottomBar: @Composable () -> Unit,
    content: @Composable (PaddingValues) -> Unit
) {
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val expanded = maxWidth >= 600.dp
        Row(Modifier.fillMaxSize()) {
            if (expanded) NavigationRail(containerColor = AugustColor.Navy, contentColor = AugustColor.Surface) {
                Spacer(Modifier.height(24.dp))
                MainTab.entries.forEach { tab ->
                    val label = stringResource(when (tab) {
                        MainTab.Today -> R.string.tab_today; MainTab.Workouts -> R.string.tab_workouts
                        MainTab.Nutrition -> R.string.tab_nutrition; MainTab.Settings -> R.string.tab_settings
                    })
                    NavigationRailItem(
                        selected = selected == tab, onClick = { onSelected(tab) },
                        icon = { Icon(when (tab) {
                            MainTab.Today -> Icons.Rounded.Home; MainTab.Workouts -> Icons.Rounded.FitnessCenter
                            MainTab.Nutrition -> Icons.Rounded.Restaurant; MainTab.Settings -> Icons.Rounded.Settings
                        }, contentDescription = null) },
                        label = { Text(label) },
                        colors = NavigationRailItemDefaults.colors(
                            selectedIconColor = AugustColor.Lime, selectedTextColor = AugustColor.Lime,
                            unselectedIconColor = AugustColor.DarkSecondaryText, unselectedTextColor = AugustColor.DarkSecondaryText,
                            indicatorColor = Color.Transparent
                        )
                    )
                }
            }
            Scaffold(
                modifier = Modifier.weight(1f), containerColor = containerColor,
                bottomBar = { if (!expanded) bottomBar() }
            ) { padding ->
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.TopCenter) {
                    Box(Modifier.widthIn(max = 840.dp).fillMaxSize()) { content(padding) }
                }
            }
        }
    }
}
