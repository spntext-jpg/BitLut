package com.openhealth.sync

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.DirectionsWalk
import androidx.compose.material.icons.automirrored.rounded.TrendingUp
import androidx.compose.material.icons.rounded.FitnessCenter
import androidx.compose.material.icons.rounded.Info
import androidx.compose.material.icons.rounded.KeyboardArrowDown
import androidx.compose.material.icons.rounded.KeyboardArrowUp
import androidx.compose.material.icons.rounded.LocalDrink
import androidx.compose.material.icons.rounded.LocalFireDepartment
import androidx.compose.material.icons.rounded.Schedule
import androidx.compose.material.icons.rounded.SelfImprovement
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.openhealth.sync.ui.theme.AugustColor
import com.openhealth.sync.ui.theme.AugustRadius

/**
 * One expandable tip on the Workouts tab. The text lives in string resources
 * (EN + RU) so the owner can edit or extend the list without touching layout code.
 */
private class WorkoutTip(
    val icon: ImageVector,
    val titleRes: Int,
    val bodyRes: Int
)

private val WORKOUT_TIPS = listOf(
    WorkoutTip(Icons.Rounded.LocalFireDepartment, R.string.workout_tip_warmup_title, R.string.workout_tip_warmup_body),
    WorkoutTip(Icons.AutoMirrored.Rounded.TrendingUp, R.string.workout_tip_gradual_title, R.string.workout_tip_gradual_body),
    WorkoutTip(Icons.AutoMirrored.Rounded.DirectionsWalk, R.string.workout_tip_walking_title, R.string.workout_tip_walking_body),
    WorkoutTip(Icons.Rounded.FitnessCenter, R.string.workout_tip_strength_title, R.string.workout_tip_strength_body),
    WorkoutTip(Icons.Rounded.SelfImprovement, R.string.workout_tip_rest_title, R.string.workout_tip_rest_body),
    WorkoutTip(Icons.Rounded.LocalDrink, R.string.workout_tip_water_title, R.string.workout_tip_water_body),
    WorkoutTip(Icons.Rounded.Schedule, R.string.workout_tip_cooldown_title, R.string.workout_tip_cooldown_body),
    WorkoutTip(Icons.Rounded.Info, R.string.workout_tip_listen_title, R.string.workout_tip_listen_body)
)

/**
 * Workouts tab (stage 4 of docs/PRODUCT_ROADMAP.md): static, bundled, offline
 * training tips. No network, no account, no data from the person's health
 * records. One tip is expanded at a time.
 */
@Composable
internal fun WorkoutsScreen(palette: BitPalette) {
    var expandedIndex by rememberSaveable { mutableStateOf(-1) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 14.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        MinimalHeader(palette = palette, title = stringResource(R.string.tab_workouts))
        Text(
            text = stringResource(R.string.workouts_intro),
            color = palette.secondaryText,
            fontWeight = FontWeight.Medium,
            fontSize = 14.sp
        )
        WORKOUT_TIPS.forEachIndexed { index, tip ->
            WorkoutTipCard(
                palette = palette,
                tip = tip,
                expanded = expandedIndex == index,
                onToggle = { expandedIndex = if (expandedIndex == index) -1 else index }
            )
        }
        Text(
            text = stringResource(R.string.workouts_disclaimer),
            color = palette.secondaryText,
            fontWeight = FontWeight.Medium,
            fontSize = 12.sp
        )
    }
}

@Composable
private fun WorkoutTipCard(
    palette: BitPalette,
    tip: WorkoutTip,
    expanded: Boolean,
    onToggle: () -> Unit
) {
    SoftCard(palette = palette) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 48.dp)
                .clickable(role = Role.Button, onClick = onToggle),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Lime chip with an Ink icon: the same pairing as the hero stat
            // tiles (Ink on Lime 15.74:1).
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(RoundedCornerShape(AugustRadius.Pill))
                    .background(AugustColor.Lime),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = tip.icon,
                    contentDescription = null,
                    tint = AugustColor.Ink,
                    modifier = Modifier.size(22.dp)
                )
            }
            Spacer(Modifier.width(14.dp))
            Text(
                text = stringResource(tip.titleRes),
                color = palette.text,
                fontWeight = FontWeight.ExtraBold,
                fontSize = 16.sp,
                modifier = Modifier.weight(1f)
            )
            Icon(
                imageVector = if (expanded) Icons.Rounded.KeyboardArrowUp else Icons.Rounded.KeyboardArrowDown,
                contentDescription = null,
                tint = palette.secondaryText
            )
        }
        if (expanded) {
            Spacer(Modifier.height(10.dp))
            Text(
                text = stringResource(tip.bodyRes),
                color = palette.secondaryText,
                fontWeight = FontWeight.Medium,
                fontSize = 14.sp,
                lineHeight = 20.sp
            )
        }
    }
}
