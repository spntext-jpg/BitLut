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
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.TextAutoSize
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.rounded.KeyboardArrowRight
import androidx.compose.material.icons.rounded.BreakfastDining
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.Cookie
import androidx.compose.material.icons.rounded.DinnerDining
import androidx.compose.material.icons.rounded.LocalDining
import androidx.compose.material.icons.rounded.LunchDining
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.openhealth.sync.config.FoodEntry
import com.openhealth.sync.config.MealType
import com.openhealth.sync.config.NutritionJournalPrefs
import com.openhealth.sync.ui.theme.AugustColor
import com.openhealth.sync.ui.theme.AugustRadius
import java.text.NumberFormat
import java.time.LocalDate
import java.time.LocalTime
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle
import java.util.Locale

/**
 * Nutrition tab (stage 5 of docs/PRODUCT_ROADMAP.md): a manual, local-only food
 * journal with a daily calorie total. Nothing here touches the network, Health
 * Connect or Huawei Health; see [NutritionJournalPrefs] for the storage rules.
 */
@Composable
internal fun NutritionScreen(palette: BitPalette) {
    val context = LocalContext.current
    val journal = remember { NutritionJournalPrefs(context) }
    var entries by remember { mutableStateOf(journal.loadAll()) }
    // 0 = today, -1 = yesterday, ... The journal can be browsed backwards only.
    var dayOffset by rememberSaveable { mutableStateOf(0) }
    var showAddDialog by rememberSaveable { mutableStateOf(false) }

    val locale = LocalConfiguration.current.locales[0]
    val day = LocalDate.now().plusDays(dayOffset.toLong())
    val dayEntries = entries.filter { it.epochDay == day.toEpochDay() }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 14.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        MinimalHeader(palette = palette, title = stringResource(R.string.tab_nutrition))

        DayNavigator(
            palette = palette,
            label = dayLabel(day = day, dayOffset = dayOffset, locale = locale),
            canGoForward = dayOffset < 0,
            onPrevious = { dayOffset -= 1 },
            onNext = { dayOffset += 1 }
        )

        NutritionTotalCard(palette = palette, totalKcal = dayEntries.sumOf { it.kcal }, locale = locale)

        PrimaryButton(
            text = stringResource(R.string.nutrition_add_meal),
            onClick = { showAddDialog = true }
        )

        if (dayEntries.isEmpty()) {
            SoftCard(palette = palette) {
                Icon(
                    imageVector = Icons.Rounded.LocalDining,
                    contentDescription = null,
                    tint = palette.secondaryText,
                    modifier = Modifier
                        .size(28.dp)
                        .align(Alignment.CenterHorizontally)
                )
                Spacer(Modifier.height(10.dp))
                Text(
                    text = stringResource(R.string.nutrition_empty_title),
                    color = palette.text,
                    fontWeight = FontWeight.ExtraBold,
                    fontSize = 16.sp,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    text = stringResource(R.string.nutrition_empty_body),
                    color = palette.secondaryText,
                    fontWeight = FontWeight.Medium,
                    fontSize = 14.sp,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        } else {
            MealType.values().forEach { meal ->
                val mealEntries = dayEntries.filter { it.meal == meal }
                if (mealEntries.isNotEmpty()) {
                    MealSection(
                        palette = palette,
                        meal = meal,
                        entries = mealEntries,
                        locale = locale,
                        onDelete = { id -> entries = journal.remove(id) }
                    )
                }
            }
        }

        Text(
            text = stringResource(R.string.nutrition_privacy_note),
            color = palette.secondaryText,
            fontWeight = FontWeight.Medium,
            fontSize = 12.sp
        )
    }

    if (showAddDialog) {
        AddFoodDialog(
            palette = palette,
            onDismiss = { showAddDialog = false },
            onSave = { meal, name, kcal ->
                entries = journal.add(meal = meal, epochDay = day.toEpochDay(), name = name, kcal = kcal)
                showAddDialog = false
            }
        )
    }
}

@Composable
private fun dayLabel(day: LocalDate, dayOffset: Int, locale: Locale): String = when (dayOffset) {
    0 -> stringResource(R.string.nutrition_day_today)
    -1 -> stringResource(R.string.nutrition_day_yesterday)
    else -> day.format(DateTimeFormatter.ofLocalizedDate(FormatStyle.MEDIUM).withLocale(locale))
}

@Composable
private fun DayNavigator(
    palette: BitPalette,
    label: String,
    canGoForward: Boolean,
    onPrevious: () -> Unit,
    onNext: () -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        DayArrow(
            palette = palette,
            icon = Icons.AutoMirrored.Rounded.KeyboardArrowLeft,
            description = stringResource(R.string.nutrition_prev_day),
            enabled = true,
            onClick = onPrevious
        )
        Text(
            text = label,
            color = palette.text,
            fontWeight = FontWeight.ExtraBold,
            fontSize = 18.sp,
            textAlign = TextAlign.Center,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f)
        )
        DayArrow(
            palette = palette,
            icon = Icons.AutoMirrored.Rounded.KeyboardArrowRight,
            description = stringResource(R.string.nutrition_next_day),
            enabled = canGoForward,
            onClick = onNext
        )
    }
}

@Composable
private fun DayArrow(
    palette: BitPalette,
    icon: ImageVector,
    description: String,
    enabled: Boolean,
    onClick: () -> Unit
) {
    Box(
        modifier = Modifier
            .size(48.dp)
            .clip(RoundedCornerShape(AugustRadius.Pill))
            .background(if (palette.dark) AugustColor.NavySoft else AugustColor.Soft)
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick),
        contentAlignment = Alignment.Center
    ) {
        Icon(
            imageVector = icon,
            contentDescription = description,
            tint = palette.secondaryText.copy(alpha = if (enabled) 1f else 0.35f),
            modifier = Modifier.size(24.dp)
        )
    }
}

@Composable
private fun NutritionTotalCard(palette: BitPalette, totalKcal: Int, locale: Locale) {
    SoftCard(palette = palette) {
        Text(
            text = stringResource(R.string.nutrition_total_label),
            color = palette.secondaryText,
            fontWeight = FontWeight.SemiBold,
            fontSize = 13.sp
        )
        Spacer(Modifier.height(4.dp))
        Row(verticalAlignment = Alignment.Bottom) {
            Text(
                text = NumberFormat.getIntegerInstance(locale).format(totalKcal),
                color = palette.text,
                fontWeight = FontWeight.ExtraBold,
                // Same rule as the hero number: the size follows the measured width.
                autoSize = TextAutoSize.StepBased(minFontSize = 24.sp, maxFontSize = 44.sp, stepSize = 1.sp),
                maxLines = 1,
                softWrap = false,
                modifier = Modifier.weight(1f, fill = false)
            )
            Spacer(Modifier.width(6.dp))
            Text(
                text = stringResource(R.string.hero_unit_kcal),
                color = palette.secondaryText,
                fontWeight = FontWeight.Bold,
                fontSize = 14.sp,
                maxLines = 1,
                modifier = Modifier.padding(bottom = 6.dp)
            )
        }
    }
}

private fun mealIcon(meal: MealType): ImageVector = when (meal) {
    MealType.BREAKFAST -> Icons.Rounded.BreakfastDining
    MealType.LUNCH -> Icons.Rounded.LunchDining
    MealType.DINNER -> Icons.Rounded.DinnerDining
    MealType.SNACK -> Icons.Rounded.Cookie
}

@Composable
private fun mealLabel(meal: MealType): String = stringResource(
    when (meal) {
        MealType.BREAKFAST -> R.string.nutrition_meal_breakfast
        MealType.LUNCH -> R.string.nutrition_meal_lunch
        MealType.DINNER -> R.string.nutrition_meal_dinner
        MealType.SNACK -> R.string.nutrition_meal_snack
    }
)

@Composable
private fun MealSection(
    palette: BitPalette,
    meal: MealType,
    entries: List<FoodEntry>,
    locale: Locale,
    onDelete: (Long) -> Unit
) {
    val unnamed = stringResource(R.string.nutrition_unnamed_entry)
    val deleteDescription = stringResource(R.string.nutrition_delete_entry)
    val kcalFormat = NumberFormat.getIntegerInstance(locale)
    SoftCard(palette = palette) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(32.dp)
                    .clip(RoundedCornerShape(AugustRadius.Pill))
                    .background(AugustColor.Lime),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = mealIcon(meal),
                    contentDescription = null,
                    tint = AugustColor.Ink,
                    modifier = Modifier.size(18.dp)
                )
            }
            Spacer(Modifier.width(10.dp))
            Text(
                text = mealLabel(meal),
                color = palette.text,
                fontWeight = FontWeight.ExtraBold,
                fontSize = 16.sp,
                modifier = Modifier.weight(1f)
            )
            Text(
                text = kcalFormat.format(entries.sumOf { it.kcal }) + " " + stringResource(R.string.hero_unit_kcal),
                color = palette.secondaryText,
                fontWeight = FontWeight.Bold,
                fontSize = 13.sp,
                maxLines = 1
            )
        }
        entries.forEach { entry ->
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 48.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = entry.name.ifBlank { unnamed },
                    color = palette.text,
                    fontWeight = FontWeight.Medium,
                    fontSize = 15.sp,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f)
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    text = kcalFormat.format(entry.kcal),
                    color = palette.text,
                    fontWeight = FontWeight.Bold,
                    fontSize = 15.sp,
                    maxLines = 1
                )
                Box(
                    modifier = Modifier
                        .size(48.dp)
                        .clip(RoundedCornerShape(AugustRadius.Pill))
                        .clickable(role = Role.Button, onClick = { onDelete(entry.id) }),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Rounded.Close,
                        contentDescription = deleteDescription,
                        tint = palette.secondaryText,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }
        }
    }
}

/** A sensible default meal for the time of day, so most entries need no extra tap. */
private fun defaultMealForNow(): MealType = when (LocalTime.now().hour) {
    in 5..10 -> MealType.BREAKFAST
    in 11..15 -> MealType.LUNCH
    in 16..21 -> MealType.DINNER
    else -> MealType.SNACK
}

@Composable
private fun AddFoodDialog(
    palette: BitPalette,
    onDismiss: () -> Unit,
    onSave: (MealType, String, Int) -> Unit
) {
    val meals = MealType.values()
    var mealIndex by rememberSaveable { mutableStateOf(defaultMealForNow().ordinal) }
    var name by rememberSaveable { mutableStateOf("") }
    var kcalText by rememberSaveable { mutableStateOf("") }
    val kcal = kcalText.toIntOrNull()
    val kcalValid = kcal != null && kcal in NutritionJournalPrefs.MIN_KCAL..NutritionJournalPrefs.MAX_KCAL

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = palette.card,
        titleContentColor = palette.text,
        textContentColor = palette.text,
        title = {
            Text(
                text = stringResource(R.string.nutrition_add_meal),
                fontWeight = FontWeight.ExtraBold
            )
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                // Two rows of two so every meal label has room in a dialog.
                for (rowStart in meals.indices step 2) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        for (index in rowStart until minOf(rowStart + 2, meals.size)) {
                            MealChoice(
                                palette = palette,
                                label = mealLabel(meals[index]),
                                selected = mealIndex == index,
                                modifier = Modifier.weight(1f),
                                onClick = { mealIndex = index }
                            )
                        }
                    }
                }
                OutlinedTextField(
                    value = kcalText,
                    onValueChange = { input -> kcalText = input.filter { it.isDigit() }.take(4) },
                    label = { Text(stringResource(R.string.nutrition_field_kcal)) },
                    singleLine = true,
                    isError = kcalText.isNotEmpty() && !kcalValid,
                    supportingText = {
                        if (kcalText.isNotEmpty() && !kcalValid) {
                            Text(stringResource(R.string.nutrition_kcal_error))
                        }
                    },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it.take(NutritionJournalPrefs.MAX_NAME_LENGTH) },
                    label = { Text(stringResource(R.string.nutrition_field_name)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            PrimaryButton(
                text = stringResource(R.string.nutrition_save),
                enabled = kcalValid,
                compact = true,
                modifier = Modifier,
                onClick = { kcal?.let { onSave(meals[mealIndex], name, it) } }
            )
        },
        dismissButton = {
            SecondaryButton(
                text = stringResource(R.string.nutrition_cancel),
                palette = palette,
                compact = true,
                modifier = Modifier,
                onClick = onDismiss
            )
        }
    )
}

@Composable
private fun MealChoice(
    palette: BitPalette,
    label: String,
    selected: Boolean,
    modifier: Modifier,
    onClick: () -> Unit
) {
    Box(
        modifier = modifier
            .heightIn(min = 40.dp)
            .clip(RoundedCornerShape(AugustRadius.Pill))
            .background(
                when {
                    selected -> AugustColor.Lime
                    palette.dark -> AugustColor.NavySoft
                    else -> AugustColor.Soft
                }
            )
            .selectable(selected = selected, role = Role.RadioButton, onClick = onClick)
            .padding(horizontal = 8.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = label,
            color = if (selected) AugustColor.Ink else palette.text,
            fontWeight = FontWeight.Bold,
            autoSize = TextAutoSize.StepBased(minFontSize = 10.sp, maxFontSize = 13.sp, stepSize = 1.sp),
            maxLines = 1,
            softWrap = false
        )
    }
}
