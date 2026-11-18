package com.openhealth.sync

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.rounded.KeyboardArrowRight
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.DeleteOutline
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.openhealth.sync.config.*
import com.openhealth.sync.data.CatalogFood
import com.openhealth.sync.data.FoodCatalog
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.NumberFormat
import java.time.LocalDate
import java.time.LocalTime
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle

@Composable
internal fun rememberJournalState(journal: NutritionJournalPrefs): NutritionJournalState {
    val flow = remember(journal) { journal.state() }
    return flow.collectAsStateWithLifecycle(initialValue = NutritionJournalState()).value
}

/** Re-evaluate after resume and at most a minute after midnight/time-zone changes. */
@Composable
private fun journalToday(): LocalDate {
    var today by remember { mutableStateOf(LocalDate.now()) }
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) { today = LocalDate.now() }
    LaunchedEffect(Unit) {
        while (true) { today = LocalDate.now(); delay(60_000) }
    }
    return today
}

@Composable
internal fun NutritionDashboardCard(palette: BitPalette, onOpen: () -> Unit) {
    val context = LocalContext.current
    val journal = remember(context.applicationContext) { NutritionJournalPrefs(context) }
    val state = rememberJournalState(journal)
    val today = journalToday()
    if (state.storageError) {
        SoftCard(palette) { Text(stringResource(R.string.nutrition_storage_error), color = MaterialTheme.colorScheme.error) }
    } else {
        NutritionSummaryCard(palette, NutritionTotals.of(state.entries.filter { it.epochDay == today.toEpochDay() }), state.goalKcal) {
            TextButton(onClick = onOpen) { Text(stringResource(R.string.nutrition_open_log)) }
        }
    }
}

@Composable
internal fun NutritionSummaryCard(
    palette: BitPalette,
    totals: NutritionTotals,
    goal: Int,
    action: @Composable () -> Unit = {}
) {
    val locale = LocalConfiguration.current.locales[0]
    val numbers = remember(locale) { NumberFormat.getNumberInstance(locale).apply { maximumFractionDigits = 1 } }
    SoftCard(palette) {
        Text(stringResource(R.string.nutrition_total_label), color = palette.secondaryText, style = MaterialTheme.typography.titleMedium)
        Text(
            stringResource(R.string.nutrition_energy_format, numbers.format(totals.kcal)),
            color = palette.text, style = MaterialTheme.typography.headlineLarge
        )
        if (goal > 0) {
            LinearProgressIndicator(
                progress = { (totals.kcal / goal).toFloat().coerceIn(0f, 1f) },
                modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
                color = palette.heroAccent, trackColor = palette.soft
            )
            Text(stringResource(R.string.nutrition_goal_balance, numbers.format(goal), numbers.format(goal - totals.kcal)), color = palette.secondaryText)
        }
        Spacer(Modifier.height(12.dp))
        val known = totals.entries == 0 || totals.unknownMacros < totals.entries
        // Separate lines remain readable at 200% font size and on narrow phones.
        listOf(R.string.nutrition_protein to totals.protein, R.string.nutrition_fat to totals.fat, R.string.nutrition_carbs to totals.carbs).forEach { (label, amount) ->
            Row(Modifier.fillMaxWidth().padding(vertical = 3.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(stringResource(label), color = palette.secondaryText)
                Text(if (known) stringResource(R.string.nutrition_grams_format, numbers.format(amount)) else stringResource(R.string.no_data_short), color = palette.text)
            }
        }
        if (totals.unknownMacros > 0) Text(stringResource(R.string.nutrition_incomplete_macros, totals.unknownMacros), color = palette.secondaryText, style = MaterialTheme.typography.bodySmall)
        action()
    }
}

@Composable
internal fun NutritionScreen(palette: BitPalette) {
    val context = LocalContext.current
    val journal = remember(context.applicationContext) { NutritionJournalPrefs(context) }
    val state = rememberJournalState(journal)
    val scope = rememberCoroutineScope()
    val snackbar = remember { SnackbarHostState() }
    val locale = LocalConfiguration.current.locales[0]
    val today = journalToday()
    var dayOffset by rememberSaveable { mutableIntStateOf(0) }
    var editorOpen by rememberSaveable { mutableStateOf(false) }
    var saving by remember { mutableStateOf(false) }
    var editingId by rememberSaveable { mutableStateOf<Long?>(null) }
    var goalOpen by rememberSaveable { mutableStateOf(false) }
    var catalogRetry by remember { mutableIntStateOf(0) }
    val catalog by produceState<Result<List<CatalogFood>>?>(null, catalogRetry) {
        value = withContext(Dispatchers.IO) { runCatching { FoodCatalog.load(context) } }
    }
    val day = today.plusDays(dayOffset.toLong())
    val entries = state.entries.filter { it.epochDay == day.toEpochDay() }
    val saveError = stringResource(R.string.nutrition_save_error)
    val deleted = stringResource(R.string.nutrition_deleted)
    val undo = stringResource(R.string.nutrition_undo)
    Scaffold(containerColor = palette.systemBackground, snackbarHost = { SnackbarHost(snackbar) }) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item { MinimalHeader(palette, stringResource(R.string.tab_nutrition)) }
            item {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    IconButton(onClick = { dayOffset-- }) { Icon(Icons.AutoMirrored.Rounded.KeyboardArrowLeft, stringResource(R.string.nutrition_prev_day)) }
                    Text(
                        when (dayOffset) { 0 -> stringResource(R.string.nutrition_day_today); -1 -> stringResource(R.string.nutrition_day_yesterday); else -> day.format(DateTimeFormatter.ofLocalizedDate(FormatStyle.MEDIUM).withLocale(locale)) },
                        modifier = Modifier.weight(1f), color = palette.text, style = MaterialTheme.typography.titleMedium
                    )
                    IconButton(onClick = { dayOffset++ }, enabled = dayOffset < 0) { Icon(Icons.AutoMirrored.Rounded.KeyboardArrowRight, stringResource(R.string.nutrition_next_day)) }
                }
            }
            if (state.storageError) item { Text(stringResource(R.string.nutrition_storage_error), color = MaterialTheme.colorScheme.error) }
            else {
                item {
                    NutritionSummaryCard(palette, NutritionTotals.of(entries), state.goalKcal) {
                        TextButton(onClick = { goalOpen = true }) { Text(stringResource(R.string.nutrition_set_goal)) }
                    }
                }
                item { PrimaryButton(stringResource(R.string.nutrition_add_meal), onClick = { editingId = null; editorOpen = true }) }
                if (entries.isEmpty()) item {
                    SoftCard(palette) {
                        Text(stringResource(R.string.nutrition_empty_title), style = MaterialTheme.typography.titleMedium, color = palette.text)
                        Text(stringResource(R.string.nutrition_empty_body), color = palette.secondaryText)
                    }
                }
                MealType.entries.forEach { meal ->
                    val meals = entries.filter { it.meal == meal }
                    if (meals.isNotEmpty()) {
                        item(key = "meal-${meal.key}") { Text(mealLabel(meal), style = MaterialTheme.typography.titleMedium, color = palette.text) }
                        items(meals, key = { it.id }) { entry ->
                            SoftCard(palette) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Column(Modifier.weight(1f).clickable { editingId = entry.id; editorOpen = true }.padding(vertical = 12.dp)) {
                                        Text(entry.name.ifBlank { stringResource(R.string.nutrition_unnamed_entry) }, color = palette.text, style = MaterialTheme.typography.titleMedium)
                                        val value = NumberFormat.getNumberInstance(locale).apply { maximumFractionDigits = 1 }
                                        Text(
                                            stringResource(R.string.nutrition_energy_format, value.format(entry.kcal)) + (entry.grams?.let { " · " + stringResource(R.string.nutrition_grams_format, value.format(it)) } ?: ""),
                                            color = palette.secondaryText
                                        )
                                        if (entry.hasMacros) Text(
                                            stringResource(R.string.nutrition_entry_macros, value.format(entry.protein), value.format(entry.fat), value.format(entry.carbs)),
                                            color = palette.secondaryText, style = MaterialTheme.typography.bodySmall
                                        )
                                        Text(stringResource(R.string.nutrition_tap_edit), color = palette.secondaryText, style = MaterialTheme.typography.bodySmall)
                                    }
                                    IconButton(onClick = {
                                        scope.launch {
                                            try {
                                                withContext(Dispatchers.IO) { journal.remove(entry.id) }
                                                if (snackbar.showSnackbar(deleted, undo) == SnackbarResult.ActionPerformed) withContext(Dispatchers.IO) { journal.upsert(entry) }
                                            } catch (cancel: kotlinx.coroutines.CancellationException) { throw cancel }
                                            catch (_: Exception) { snackbar.showSnackbar(saveError) }
                                        }
                                    }) { Icon(Icons.Rounded.DeleteOutline, stringResource(R.string.nutrition_delete_entry), tint = palette.secondaryText) }
                                }
                            }
                        }
                    }
                }
            }
            item { Text(stringResource(R.string.nutrition_reference_note), color = palette.secondaryText, style = MaterialTheme.typography.bodySmall) }
            item { Text(stringResource(R.string.nutrition_privacy_note), color = palette.secondaryText, style = MaterialTheme.typography.bodySmall) }
        }
    }
    if (goalOpen) GoalDialog(state.goalKcal, onDismiss = { goalOpen = false }) { goal ->
        scope.launch {
            try { withContext(Dispatchers.IO) { journal.setGoal(goal) }; goalOpen = false }
            catch (cancel: kotlinx.coroutines.CancellationException) { throw cancel }
            catch (_: Exception) { snackbar.showSnackbar(saveError) }
        }
    }
    if (editorOpen && !state.storageError) FoodEditor(
        palette = palette, foods = catalog?.getOrNull().orEmpty(), loading = catalog == null,
        catalogError = catalog?.isFailure == true, onRetry = { catalogRetry++ },
        initial = state.entries.firstOrNull { it.id == editingId }, epochDay = day.toEpochDay(), saving = saving,
        onDismiss = { if (!saving) editorOpen = false }, onSave = { entry ->
            if (!saving) {
                saving = true
                scope.launch {
                    try { withContext(Dispatchers.IO) { journal.upsert(entry) }; editorOpen = false }
                    catch (cancel: kotlinx.coroutines.CancellationException) { throw cancel }
                    catch (_: Exception) { snackbar.showSnackbar(saveError) }
                    finally { saving = false }
                }
            }
        }
    )
}

@Composable
private fun mealLabel(meal: MealType): String = stringResource(when (meal) {
    MealType.BREAKFAST -> R.string.nutrition_meal_breakfast; MealType.LUNCH -> R.string.nutrition_meal_lunch
    MealType.DINNER -> R.string.nutrition_meal_dinner; MealType.SNACK -> R.string.nutrition_meal_snack
})

private fun parsedAmount(value: String): Double? = value.replace(',', '.').toDoubleOrNull()?.takeIf { it.isFinite() && it >= 0 }

@Composable
private fun AmountField(value: String, label: String, onChange: (String) -> Unit, valid: Boolean = true) {
    OutlinedTextField(
        value = value, onValueChange = { onChange(it.take(12)) }, label = { Text(label) },
        singleLine = true, isError = !valid, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
        modifier = Modifier.fillMaxWidth()
    )
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun FoodEditor(
    palette: BitPalette, foods: List<CatalogFood>, loading: Boolean, catalogError: Boolean, onRetry: () -> Unit,
    initial: FoodEntry?, epochDay: Long, saving: Boolean, onDismiss: () -> Unit, onSave: (FoodEntry) -> Unit
) {
    val locale = LocalConfiguration.current.locales[0]
    var selectedId by rememberSaveable { mutableStateOf(initial?.foodId) }
    var custom by rememberSaveable { mutableStateOf(initial != null && initial.foodId == null) }
    var query by rememberSaveable { mutableStateOf("") }
    var name by rememberSaveable { mutableStateOf(initial?.name.orEmpty()) }
    var grams by rememberSaveable { mutableStateOf(initial?.grams?.toString() ?: if (initial != null) "" else "100") }
    var kcal by rememberSaveable { mutableStateOf(initial?.kcal?.toString().orEmpty()) }
    var protein by rememberSaveable { mutableStateOf(initial?.protein?.toString().orEmpty()) }
    var fat by rememberSaveable { mutableStateOf(initial?.fat?.toString().orEmpty()) }
    var carbs by rememberSaveable { mutableStateOf(initial?.carbs?.toString().orEmpty()) }
    var meal by rememberSaveable { mutableStateOf(initial?.meal ?: when (LocalTime.now().hour) { in 5..10 -> MealType.BREAKFAST; in 11..15 -> MealType.LUNCH; in 16..21 -> MealType.DINNER; else -> MealType.SNACK }) }
    val selected = foods.firstOrNull { it.id == selectedId }
    val weight = parsedAmount(grams)?.takeIf { it > 0 && it <= 5000 }
    val portion = if (!custom && selected != null && weight != null) selected.portion(weight) else null
    val energy = if (custom) parsedAmount(kcal) else portion?.kcal
    val p = if (custom) parsedAmount(protein) else portion?.protein
    val f = if (custom) parsedAmount(fat) else portion?.fat
    val c = if (custom) parsedAmount(carbs) else portion?.carbs
    val manualMacrosValid = listOf(protein, fat, carbs).all { it.isBlank() || parsedAmount(it)?.let { n -> n <= 5000 } == true }
    val valid = energy != null && energy <= NutritionJournalPrefs.MAX_KCAL &&
        (if (custom) manualMacrosValid && name.isNotBlank() && (grams.isBlank() || weight != null) else portion != null) &&
        (weight == null || listOfNotNull(p, f, c).sum() <= weight + 0.5)
    val results = remember(foods, query, locale) { FoodCatalog.search(foods, query, locale) }
    Dialog(onDismissRequest = onDismiss, properties = DialogProperties(usePlatformDefaultWidth = false)) {
        Surface(
            modifier = Modifier.widthIn(max = 600.dp).fillMaxWidth().fillMaxHeight(0.94f).imePadding(),
            color = palette.card, shape = MaterialTheme.shapes.extraLarge
        ) {
            Column(Modifier.padding(16.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(stringResource(if (initial == null) R.string.nutrition_add_meal else R.string.nutrition_edit_food), modifier = Modifier.weight(1f), style = MaterialTheme.typography.titleLarge)
                    IconButton(onClick = onDismiss) { Icon(Icons.Rounded.Close, stringResource(R.string.nutrition_cancel)) }
                }
                LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(12.dp), contentPadding = PaddingValues(bottom = 16.dp)) {
                    item {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            FilterChip(modifier = Modifier.heightIn(min = 48.dp), selected = !custom, onClick = { custom = false }, label = { Text(stringResource(R.string.nutrition_catalog)) })
                            FilterChip(modifier = Modifier.heightIn(min = 48.dp), selected = custom, onClick = { custom = true }, label = { Text(stringResource(R.string.nutrition_custom)) })
                        }
                    }
                    item {
                        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            MealType.entries.forEach { slot -> FilterChip(selected = slot == meal, onClick = { meal = slot }, label = { Text(mealLabel(slot)) }, modifier = Modifier.heightIn(min = 48.dp)) }
                        }
                    }
                    if (custom) {
                        item { Text(stringResource(R.string.nutrition_custom_hint), style = MaterialTheme.typography.bodySmall) }
                        item { OutlinedTextField(value = name, onValueChange = { name = it.take(NutritionJournalPrefs.MAX_NAME_LENGTH) }, label = { Text(stringResource(R.string.nutrition_field_name)) }, modifier = Modifier.fillMaxWidth()) }
                        item { AmountField(kcal, stringResource(R.string.nutrition_field_kcal), { kcal = it }, kcal.isBlank() || energy != null) }
                        item { AmountField(grams, stringResource(R.string.nutrition_weight_optional), { grams = it }, grams.isBlank() || weight != null) }
                        item { AmountField(protein, stringResource(R.string.nutrition_protein), { protein = it }, protein.isBlank() || p != null) }
                        item { AmountField(fat, stringResource(R.string.nutrition_fat), { fat = it }, fat.isBlank() || f != null) }
                        item { AmountField(carbs, stringResource(R.string.nutrition_carbs), { carbs = it }, carbs.isBlank() || c != null) }
                    } else if (selected != null) {
                        item {
                            Text(selected.name(locale), style = MaterialTheme.typography.titleMedium)
                            Text(selected.sourceDescription, style = MaterialTheme.typography.bodySmall, color = palette.secondaryText)
                            TextButton(onClick = { selectedId = null }) { Text(stringResource(R.string.nutrition_change_food)) }
                        }
                        item { AmountField(grams, stringResource(R.string.nutrition_weight), { grams = it }, weight != null) }
                        if (portion != null) item { NutritionSummaryCard(palette, NutritionTotals(portion.kcal, portion.protein, portion.fat, portion.carbs, 0, 1), 0) }
                    } else {
                        item { OutlinedTextField(value = query, onValueChange = { query = it.take(100) }, label = { Text(stringResource(R.string.nutrition_search)) }, modifier = Modifier.fillMaxWidth(), singleLine = true) }
                        if (loading) item { CircularProgressIndicator() }
                        else if (catalogError) item { Text(stringResource(R.string.nutrition_catalog_error)); TextButton(onClick = onRetry) { Text(stringResource(R.string.nutrition_retry)) } }
                        else if (results.isEmpty()) item { Text(stringResource(R.string.nutrition_no_results)) }
                        items(results, key = { it.id }) { food ->
                            ListItem(
                                headlineContent = { Text(food.name(locale)) },
                                supportingContent = { Text(stringResource(R.string.nutrition_per_100g, food.kcalPer100g.toInt())) },
                                modifier = Modifier.clickable { selectedId = food.id; grams = "100" }.heightIn(min = 64.dp),
                                colors = ListItemDefaults.colors(containerColor = palette.card)
                            )
                        }
                    }
                }
                PrimaryButton(stringResource(R.string.nutrition_save), enabled = valid && !saving, onClick = {
                    onSave(FoodEntry(
                        id = initial?.id ?: 0, epochDay = initial?.epochDay ?: epochDay, meal = meal,
                        name = if (custom) name.trim() else requireNotNull(selected).name(locale),
                        kcal = requireNotNull(energy), grams = if (custom && grams.isBlank()) null else weight,
                        protein = p, fat = f, carbs = c, foodId = if (custom) null else selectedId
                    ))
                })
                if (!valid && (selected != null || custom)) Text(stringResource(R.string.nutrition_input_hint), color = palette.secondaryText, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun GoalDialog(current: Int, onDismiss: () -> Unit, onSave: (Int) -> Unit) {
    var text by rememberSaveable { mutableStateOf(if (current > 0) current.toString() else "") }
    val value = if (text.isBlank()) 0 else text.toIntOrNull()
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.nutrition_set_goal)) },
        text = { Column(Modifier.verticalScroll(rememberScrollState())) {
            Text(stringResource(R.string.nutrition_goal_hint))
            AmountField(text, stringResource(R.string.nutrition_field_kcal), { text = it })
        } },
        confirmButton = { TextButton(enabled = value != null && value in 0..NutritionJournalPrefs.MAX_KCAL, onClick = { value?.let(onSave) }) { Text(stringResource(R.string.nutrition_save)) } },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.nutrition_cancel)) } }
    )
}
