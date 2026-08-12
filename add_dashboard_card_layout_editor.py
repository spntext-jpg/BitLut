NEW_FILE_CONTENT = 'package com.openhealth.sync.config\n\nimport android.content.Context\nimport android.content.SharedPreferences\nimport com.openhealth.sync.data.remote.HuaweiConfig\n\n/**\n * The reorderable/hideable cards on the Today screen, below the pinned Steps\n * hero card (Steps itself is not part of this list -- it always stays first,\n * it\'s the screen\'s anchor). Order here is only the fallback DEFAULT_ORDER;\n * the person\'s actual order/visibility lives in DashboardCardLayoutPrefs.\n */\nenum class DashboardCardType(val key: String) {\n    ACTIVITY_RINGS("activity_rings"),\n    WORKOUT_LATEST("workout_latest"),\n    WORKOUT_PREVIOUS("workout_previous"),\n    LAST_7_DAYS("last_7_days"),\n    PERSONAL_RECORDS("personal_records"),\n    STREAK("streak");\n\n    companion object {\n        val DEFAULT_ORDER: List<DashboardCardType> = listOf(\n            ACTIVITY_RINGS, WORKOUT_LATEST, WORKOUT_PREVIOUS, LAST_7_DAYS, PERSONAL_RECORDS, STREAK\n        )\n\n        fun fromKey(key: String): DashboardCardType? = values().firstOrNull { it.key == key }\n    }\n}\n\n/**\n * Persists the person\'s chosen order and visibility for the reorderable\n * Today-screen cards, edited from the pencil icon on the Today screen\n * itself (not Settings -- this is a different surface from\n * WidgetVisibilityPrefs, which controls the home-screen Glance widget).\n *\n * Unknown keys from a saved order (e.g. a card type removed in a future\n * release) are silently dropped. A brand-new card type introduced in a\n * future update that isn\'t in the saved order yet is appended at the end,\n * so it doesn\'t get silently hidden from people who already customized\n * their layout before that update.\n */\nclass DashboardCardLayoutPrefs(context: Context) {\n\n    private val prefs: SharedPreferences = context.getSharedPreferences(\n        HuaweiConfig.PREFS_NAME,\n        Context.MODE_PRIVATE\n    )\n\n    /** Full ordered list (including hidden cards) -- used by the editor screen. */\n    fun allCardsForEditor(): List<DashboardCardType> {\n        val raw = prefs.getString(KEY_ORDER, null) ?: return DashboardCardType.DEFAULT_ORDER\n        val saved = raw.split(",").mapNotNull { DashboardCardType.fromKey(it) }\n        val missing = DashboardCardType.DEFAULT_ORDER.filter { it !in saved }\n        return saved + missing\n    }\n\n    fun hiddenKeys(): Set<String> = prefs.getStringSet(KEY_HIDDEN, emptySet()).orEmpty()\n\n    /** What the Today screen actually renders: ordered, with hidden cards filtered out. */\n    fun orderedVisibleCards(): List<DashboardCardType> {\n        val hidden = hiddenKeys()\n        return allCardsForEditor().filter { it.key !in hidden }\n    }\n\n    fun setOrder(order: List<DashboardCardType>) {\n        prefs.edit().putString(KEY_ORDER, order.joinToString(",") { it.key }).apply()\n    }\n\n    fun setHidden(type: DashboardCardType, hidden: Boolean) {\n        val current = hiddenKeys().toMutableSet()\n        if (hidden) current.add(type.key) else current.remove(type.key)\n        prefs.edit().putStringSet(KEY_HIDDEN, current).apply()\n    }\n\n    companion object {\n        private const val KEY_ORDER = "dashboard_card_order"\n        private const val KEY_HIDDEN = "dashboard_card_hidden"\n    }\n}\n'

#!/usr/bin/env python3
"""
BitLut patch: reorderable/hideable dashboard cards + edit-layout pencil icon
(sprint item 2 -- the architecturally biggest piece of the "last sprint").

- New DashboardCardLayoutPrefs (config package): persists order + visibility
  for the reorderable Today-screen cards (Activity rings, both workout
  cards, 7-day summary, personal records, streak). The Steps hero card is
  NOT part of this list -- it stays pinned first, it's the screen's anchor.
- Wires in StreakCard for the first time -- it was fully built (comment:
  "Streak card (v1.9.12, sprint 4)") but never actually called from
  anywhere, same "half-built, never connected" pattern as the rings/goals
  wiring from the previous patch.
- New pencil icon in the Today screen header (top-right), opens a
  full-screen editor: up/down buttons to reorder, a switch to show/hide
  each card. No drag-and-drop -- Compose has no built-in reorder gesture,
  and pulling in a third-party library for it is exactly the kind of new-
  dependency risk this project avoids when there's a simpler alternative.
  Every change (reorder or visibility) is persisted immediately, same
  "no explicit save button" pattern as the rest of Settings.
- The sync-time text in the header now sits to the left of the new pencil
  icon instead of being the rightmost element, per your request.

No new Health Connect permission or Huawei scope.

Every old/new text block in this script was generated and verified
programmatically (byte-diffed against the real source, uniqueness-checked,
and idempotency-checked for the old-remains-a-substring-of-new failure
mode) rather than transcribed by hand.

Run from the repo root:
    python3 add_dashboard_card_layout_editor.py
"""
import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

UI = "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
STRINGS_EN = "app/src/main/res/values/strings.xml"
STRINGS_RU = "app/src/main/res/values-ru/strings.xml"
LAYOUT_PREFS = "app/src/main/java/com/openhealth/sync/config/DashboardCardLayoutPrefs.kt"

TARGET_FILES_MUST_EXIST = [UI, STRINGS_EN, STRINGS_RU]


def die(msg: str) -> None:
    print(f"!! {msg}")
    sys.exit(1)


def backup_file(rel_path: str) -> None:
    src = ROOT / rel_path
    if not src.exists():
        return
    dst = BACKUP_DIR / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def apply_edit(rel_path: str, old: str, new: str, desc: str) -> bool:
    """Regex-anchored (plain substring) replacement, exactly 1 occurrence.

    Checks the OLD anchor's count first; NEW-presence is only consulted as
    a fallback once OLD is confirmed absent.
    """
    path = ROOT / rel_path
    text = path.read_text(encoding="utf-8")

    old_count = text.count(old)
    if old_count == 0:
        if text.count(new) >= 1:
            print(f"   (already applied, skipping) {desc}")
            return False
        die(f"Anchor not found for \'{desc}\' in {rel_path}, and patched text "
            f"is also absent. File may have changed since this script was "
            f"written -- aborting rather than guessing.")

    if old_count != 1:
        die(f"Expected exactly 1 occurrence of anchor for \'{desc}\' in "
            f"{rel_path}, found {old_count}. Aborting rather than guessing "
            f"which one to patch.")

    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"   applied: {desc}")
    return True


def apply_insertion(rel_path: str, anchor: str, new_with_anchor: str, unique_marker: str, desc: str) -> bool:
    """For edits that insert new text between two lines that stay unchanged
    on both sides. `anchor` (spanning both sides) remains a substring of
    `new_with_anchor`, so checking anchor-count-first would never see it as
    "gone" and would reapply forever. Idempotency here is instead decided by
    `unique_marker`, a string that only exists once the insertion has
    happened.
    """
    path = ROOT / rel_path
    text = path.read_text(encoding="utf-8")

    if unique_marker in text:
        print(f"   (already applied, skipping) {desc}")
        return False

    anchor_count = text.count(anchor)
    if anchor_count != 1:
        die(f"Expected exactly 1 occurrence of anchor for \'{desc}\' in "
            f"{rel_path}, found {anchor_count}. Aborting rather than "
            f"guessing which one to patch.")

    path.write_text(text.replace(anchor, new_with_anchor, 1), encoding="utf-8")
    print(f"   applied: {desc}")
    return True


def create_layout_prefs_file() -> None:
    path = ROOT / LAYOUT_PREFS
    if path.exists():
        print(f"   (already exists, skipping) create {LAYOUT_PREFS}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(NEW_FILE_CONTENT, encoding="utf-8")
    print(f"   created: {LAYOUT_PREFS}")


def main() -> None:
    print("==> Checking target files exist")
    for rel in TARGET_FILES_MUST_EXIST:
        if not (ROOT / rel).exists():
            die(f"Expected file not found: {rel} (run this from the repo root)")

    print(f"==> Backing up touched files to {BACKUP_DIR.relative_to(ROOT)}")
    for rel in TARGET_FILES_MUST_EXIST + [LAYOUT_PREFS]:
        backup_file(rel)

    print("==> Creating DashboardCardLayoutPrefs.kt")
    create_layout_prefs_file()

    print("==> Applying edits")
    apply_edit(
        UI,
        old='import androidx.compose.foundation.lazy.items\nimport androidx.compose.foundation.shape.RoundedCornerShape\n',
        new='import androidx.compose.foundation.lazy.items\nimport androidx.compose.foundation.lazy.itemsIndexed\nimport androidx.compose.foundation.shape.RoundedCornerShape\n',
        desc='add Edit/KeyboardArrowUp/KeyboardArrowDown/AutoMirrored-ArrowBack icon imports',
    )

    apply_edit(
        UI,
        old='import androidx.compose.ui.draw.clip\nimport androidx.compose.ui.draw.drawBehind\n',
        new='import androidx.compose.ui.draw.clip\nimport androidx.compose.ui.draw.alpha\nimport androidx.compose.ui.draw.drawBehind\n',
        desc='add itemsIndexed import',
    )

    apply_edit(
        UI,
        old='import androidx.compose.material.icons.rounded.DonutLarge\nimport androidx.compose.material3.Icon\n',
        new='import androidx.compose.material.icons.rounded.DonutLarge\nimport androidx.compose.material.icons.rounded.Edit\nimport androidx.compose.material.icons.rounded.KeyboardArrowUp\nimport androidx.compose.material.icons.rounded.KeyboardArrowDown\nimport androidx.compose.material.icons.automirrored.rounded.ArrowBack\nimport androidx.compose.material3.Icon\n',
        desc='add alpha draw-modifier import',
    )

    apply_edit(
        UI,
        old='    var showArchiveImport by rememberSaveable { mutableStateOf(false) }\n    var showPermissionsOnboarding by rememberSaveable { mutableStateOf(false) }\n',
        new='    var showArchiveImport by rememberSaveable { mutableStateOf(false) }\n    var showCardLayoutEditor by rememberSaveable { mutableStateOf(false) }\n    var cardLayoutVersion by rememberSaveable { mutableStateOf(0) }\n    var showPermissionsOnboarding by rememberSaveable { mutableStateOf(false) }\n',
        desc='add showCardLayoutEditor + cardLayoutVersion state',
    )

    apply_insertion(
        UI,
        anchor='                )\n            } else when (selected) {\n',
        new_with_anchor='                )\n            } else if (showCardLayoutEditor) {\n                CardLayoutEditorScreen(\n                    palette = palette,\n                    onBack = {\n                        showCardLayoutEditor = false\n                        cardLayoutVersion++\n                    }\n                )\n            } else when (selected) {\n',
        unique_marker='showCardLayoutEditor = false\n                        cardLayoutVersion++',
        desc='wire the card layout editor overlay into the tab-content switch',
    )

    apply_edit(
        UI,
        old='            } else when (selected) {\n                MainTab.Today -> SummaryScreen(palette, dashboardState, syncState.selectedDataSource, syncState.lastSyncTime, onRefresh, wrappedOnRequestGoogle)\n                MainTab.Settings -> SettingsScreen(palette, syncState, onRefresh, wrappedOnRequestGoogle, onRequestHuawei, onSyncNow,\n',
        new='            } else when (selected) {\n                MainTab.Today -> SummaryScreen(\n                    palette, dashboardState, syncState.selectedDataSource, syncState.lastSyncTime, onRefresh, wrappedOnRequestGoogle,\n                    onEditLayout = { showCardLayoutEditor = true },\n                    cardLayoutVersion = cardLayoutVersion\n                )\n                MainTab.Settings -> SettingsScreen(palette, syncState, onRefresh, wrappedOnRequestGoogle, onRequestHuawei, onSyncNow,\n',
        desc='pass onEditLayout/cardLayoutVersion into the SummaryScreen call site',
    )

    apply_edit(
        UI,
        old='    onRefresh: () -> Unit,\n    onRequestGoogle: () -> Unit\n) {\n',
        new='    onRefresh: () -> Unit,\n    onRequestGoogle: () -> Unit,\n    onEditLayout: () -> Unit,\n    cardLayoutVersion: Int\n) {\n',
        desc="add onEditLayout/cardLayoutVersion params to SummaryScreen's signature",
    )

    apply_edit(
        UI,
        old='                title = stringResource(R.string.summary_short_title),\n                trailing = formatDashboardSourceStatus(dataSource, lastSyncTime)\n            )\n',
        new='                title = stringResource(R.string.summary_short_title),\n                trailing = formatDashboardSourceStatus(dataSource, lastSyncTime),\n                onEditClick = onEditLayout\n            )\n',
        desc="wire onEditClick into SummaryScreen's MinimalHeader call",
    )

    apply_edit(
        UI,
        old='\n                item {\n                    ActivityRingsCard(palette = palette, state = state)\n                }\n',
        new='\n                val context = LocalContext.current\n                val orderedCards = remember(cardLayoutVersion) {\n                    com.openhealth.sync.config.DashboardCardLayoutPrefs(context).orderedVisibleCards()\n                }\n',
        desc='swap the hardcoded ActivityRingsCard item for the ordered-cards setup',
    )

    apply_edit(
        UI,
        old='                }\n\n                item {\n                    WorkoutRecencyCard(\n                        palette = palette,\n                        label = stringResource(R.string.dashboard_latest_workout),\n                        emptyText = stringResource(R.string.dashboard_workout_empty_latest),\n                        position = 1,\n                        session = state.recentWorkouts.getOrNull(0),\n                        accent = HealthAccent.mind\n                    )\n                }\n\n                item {\n                    WorkoutRecencyCard(\n                        palette = palette,\n                        label = stringResource(R.string.dashboard_previous_workout),\n                        emptyText = stringResource(R.string.dashboard_workout_empty_previous),\n                        position = 2,\n                        session = state.recentWorkouts.getOrNull(1),\n                        accent = HealthAccent.violet\n                    )\n                }\n\n                item { LastSevenDaysCard(palette = palette, state = state) }\n                item {\n                    PersonalRecordsCard(\n                        palette = palette,\n                        bestStepsDay = state.bestStepsDay,\n                        bestDistanceDay = state.bestDistanceDay,\n                        bestCaloriesDay = state.bestCaloriesDay,\n                        bestElevationDay = state.bestElevationDay,\n                        bestWorkoutDuration = state.bestWorkoutDuration,\n                        isStepsRecordToday = state.isStepsRecordToday\n                    )\n                }\n',
        new='                }\n                orderedCards.forEach { cardType ->\n                    item {\n                        DashboardOrderedCard(palette = palette, state = state, cardType = cardType)\n                    }\n                }\n',
        desc='replace the remaining hardcoded workout/7-day/records items with the ordered-cards loop',
    )

    apply_insertion(
        UI,
        anchor='                }\n            }\n        }\n    }\n}\n\n@Composable\nprivate fun LastSevenDaysCard(palette: BitPalette, state: DashboardUiState) {\n',
        new_with_anchor='                }\n            }\n        }\n    }\n}\n\n/** Dispatches to the right card composable for a DashboardCardType -- the reorderable set edited from the pencil icon. */\n@Composable\nprivate fun DashboardOrderedCard(palette: BitPalette, state: DashboardUiState, cardType: com.openhealth.sync.config.DashboardCardType) {\n    when (cardType) {\n        com.openhealth.sync.config.DashboardCardType.ACTIVITY_RINGS ->\n            ActivityRingsCard(palette = palette, state = state)\n\n        com.openhealth.sync.config.DashboardCardType.WORKOUT_LATEST ->\n            WorkoutRecencyCard(\n                palette = palette,\n                label = stringResource(R.string.dashboard_latest_workout),\n                emptyText = stringResource(R.string.dashboard_workout_empty_latest),\n                position = 1,\n                session = state.recentWorkouts.getOrNull(0),\n                accent = HealthAccent.mind\n            )\n\n        com.openhealth.sync.config.DashboardCardType.WORKOUT_PREVIOUS ->\n            WorkoutRecencyCard(\n                palette = palette,\n                label = stringResource(R.string.dashboard_previous_workout),\n                emptyText = stringResource(R.string.dashboard_workout_empty_previous),\n                position = 2,\n                session = state.recentWorkouts.getOrNull(1),\n                accent = HealthAccent.violet\n            )\n\n        com.openhealth.sync.config.DashboardCardType.LAST_7_DAYS ->\n            LastSevenDaysCard(palette = palette, state = state)\n\n        com.openhealth.sync.config.DashboardCardType.PERSONAL_RECORDS ->\n            PersonalRecordsCard(\n                palette = palette,\n                bestStepsDay = state.bestStepsDay,\n                bestDistanceDay = state.bestDistanceDay,\n                bestCaloriesDay = state.bestCaloriesDay,\n                bestElevationDay = state.bestElevationDay,\n                bestWorkoutDuration = state.bestWorkoutDuration,\n                isStepsRecordToday = state.isStepsRecordToday\n            )\n\n        com.openhealth.sync.config.DashboardCardType.STREAK ->\n            StreakCard(palette = palette, streak = state.streak, stepsGoal = state.stepsGoal)\n    }\n}\n\n/**\n * Full-screen editor reached from the pencil icon on the Today screen.\n * Reorders with up/down buttons rather than drag-and-drop -- Compose has no\n * built-in drag-reorder, and pulling in a third-party library for it is\n * exactly the kind of new-dependency risk worth avoiding for a first pass.\n * Every change (reorder or visibility toggle) is persisted immediately, the\n * same "no explicit save button" pattern already used everywhere else in\n * Settings (goals, workout filter).\n */\n@Composable\nprivate fun CardLayoutEditorScreen(palette: BitPalette, onBack: () -> Unit) {\n    val context = LocalContext.current\n    val prefs = remember { com.openhealth.sync.config.DashboardCardLayoutPrefs(context) }\n    var cards by remember { mutableStateOf(prefs.allCardsForEditor()) }\n    var hidden by remember { mutableStateOf(prefs.hiddenKeys()) }\n\n    Column(\n        modifier = Modifier\n            .fillMaxSize()\n            .background(palette.backgroundBrush)\n            .padding(horizontal = 20.dp, vertical = 14.dp)\n    ) {\n        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {\n            Box(\n                modifier = Modifier\n                    .size(34.dp)\n                    .clip(RoundedCornerShape(12.dp))\n                    .clickable(onClick = onBack),\n                contentAlignment = Alignment.Center\n            ) {\n                Icon(Icons.AutoMirrored.Rounded.ArrowBack, contentDescription = null, tint = palette.text)\n            }\n            Spacer(Modifier.width(10.dp))\n            Text(\n                text = stringResource(R.string.dashboard_edit_layout_title),\n                color = palette.text,\n                fontWeight = FontWeight.ExtraBold,\n                fontSize = 22.sp\n            )\n        }\n        Spacer(Modifier.height(6.dp))\n        Text(\n            text = stringResource(R.string.dashboard_edit_layout_body),\n            color = palette.secondaryText,\n            fontWeight = FontWeight.Medium,\n            fontSize = 13.sp,\n            lineHeight = 18.sp\n        )\n        Spacer(Modifier.height(16.dp))\n        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {\n            itemsIndexed(cards, key = { _, item -> item.key }) { index, cardType ->\n                CardLayoutRow(\n                    palette = palette,\n                    label = dashboardCardLabel(cardType),\n                    visible = cardType.key !in hidden,\n                    canMoveUp = index > 0,\n                    canMoveDown = index < cards.lastIndex,\n                    onToggleVisible = { checked ->\n                        hidden = if (checked) hidden - cardType.key else hidden + cardType.key\n                        prefs.setHidden(cardType, !checked)\n                    },\n                    onMoveUp = {\n                        cards = cards.toMutableList().apply { add(index - 1, removeAt(index)) }\n                        prefs.setOrder(cards)\n                    },\n                    onMoveDown = {\n                        cards = cards.toMutableList().apply { add(index + 1, removeAt(index)) }\n                        prefs.setOrder(cards)\n                    }\n                )\n            }\n        }\n    }\n}\n\n@Composable\nprivate fun CardLayoutRow(\n    palette: BitPalette,\n    label: String,\n    visible: Boolean,\n    canMoveUp: Boolean,\n    canMoveDown: Boolean,\n    onToggleVisible: (Boolean) -> Unit,\n    onMoveUp: () -> Unit,\n    onMoveDown: () -> Unit\n) {\n    SoftCard(palette = palette, accent = HealthAccent.activity) {\n        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {\n            Text(\n                text = label,\n                color = palette.text,\n                fontWeight = FontWeight.SemiBold,\n                fontSize = 14.sp,\n                maxLines = 1,\n                overflow = TextOverflow.Ellipsis,\n                modifier = Modifier.weight(1f)\n            )\n            Box(\n                modifier = Modifier\n                    .size(28.dp)\n                    .clip(RoundedCornerShape(8.dp))\n                    .then(if (canMoveUp) Modifier.clickable(onClick = onMoveUp) else Modifier)\n                    .alpha(if (canMoveUp) 1f else 0.3f),\n                contentAlignment = Alignment.Center\n            ) {\n                Icon(Icons.Rounded.KeyboardArrowUp, contentDescription = null, tint = palette.secondaryText, modifier = Modifier.size(18.dp))\n            }\n            Spacer(Modifier.width(4.dp))\n            Box(\n                modifier = Modifier\n                    .size(28.dp)\n                    .clip(RoundedCornerShape(8.dp))\n                    .then(if (canMoveDown) Modifier.clickable(onClick = onMoveDown) else Modifier)\n                    .alpha(if (canMoveDown) 1f else 0.3f),\n                contentAlignment = Alignment.Center\n            ) {\n                Icon(Icons.Rounded.KeyboardArrowDown, contentDescription = null, tint = palette.secondaryText, modifier = Modifier.size(18.dp))\n            }\n            Spacer(Modifier.width(10.dp))\n            Switch(\n                checked = visible,\n                onCheckedChange = onToggleVisible,\n                colors = SwitchDefaults.colors(\n                    checkedThumbColor = Color.White,\n                    checkedTrackColor = HealthAccent.activity,\n                    uncheckedThumbColor = Color.White,\n                    uncheckedTrackColor = palette.stroke\n                )\n            )\n        }\n    }\n}\n\n@Composable\nprivate fun dashboardCardLabel(type: com.openhealth.sync.config.DashboardCardType): String = when (type) {\n    com.openhealth.sync.config.DashboardCardType.ACTIVITY_RINGS -> stringResource(R.string.dashboard_rings_title)\n    com.openhealth.sync.config.DashboardCardType.WORKOUT_LATEST -> stringResource(R.string.dashboard_latest_workout)\n    com.openhealth.sync.config.DashboardCardType.WORKOUT_PREVIOUS -> stringResource(R.string.dashboard_previous_workout)\n    com.openhealth.sync.config.DashboardCardType.LAST_7_DAYS -> stringResource(R.string.dashboard_last_7_days_title)\n    com.openhealth.sync.config.DashboardCardType.PERSONAL_RECORDS -> stringResource(R.string.insights_personal_records_title)\n    com.openhealth.sync.config.DashboardCardType.STREAK -> stringResource(R.string.dashboard_card_streak_label)\n}\n\n@Composable\nprivate fun LastSevenDaysCard(palette: BitPalette, state: DashboardUiState) {\n',
        unique_marker='private fun CardLayoutEditorScreen(palette: BitPalette, onBack: () -> Unit) {',
        desc='add DashboardOrderedCard/CardLayoutEditorScreen/CardLayoutRow/dashboardCardLabel composables',
    )

    apply_edit(
        UI,
        old='    subtitle: String? = null,\n    trailing: String? = null\n) {\n',
        new='    subtitle: String? = null,\n    trailing: String? = null,\n    onEditClick: (() -> Unit)? = null\n) {\n',
        desc="add onEditClick param to MinimalHeader's signature",
    )

    apply_edit(
        UI,
        old='                    maxLines = 1\n                )\n            }\n        }\n',
        new='                    maxLines = 1\n                )\n            }\n            if (onEditClick != null) {\n                Spacer(Modifier.width(10.dp))\n                Box(\n                    modifier = Modifier\n                        .size(30.dp)\n                        .clip(RoundedCornerShape(10.dp))\n                        .clickable(onClick = onEditClick),\n                    contentAlignment = Alignment.Center\n                ) {\n                    Icon(\n                        Icons.Rounded.Edit,\n                        contentDescription = stringResource(R.string.dashboard_edit_layout),\n                        tint = palette.secondaryText,\n                        modifier = Modifier.size(19.dp)\n                    )\n                }\n            }\n        }\n',
        desc='render the pencil icon in MinimalHeader when onEditClick is provided',
    )

    apply_edit(
        STRINGS_EN,
        old='    <string name="dashboard_rings_calories">Calories</string>\n    <string name="no_data_short">—</string>\n',
        new='    <string name="dashboard_rings_calories">Calories</string>\n    <string name="dashboard_edit_layout">Edit dashboard layout</string>\n    <string name="dashboard_edit_layout_title">Edit layout</string>\n    <string name="dashboard_edit_layout_body">Show, hide, and reorder the cards on your dashboard. Changes apply right away.</string>\n    <string name="dashboard_card_streak_label">Streak</string>\n    <string name="no_data_short">—</string>\n',
        desc='add card-layout-editor strings (EN)',
    )

    apply_edit(
        STRINGS_RU,
        old='    <string name="dashboard_rings_calories">Калории</string>\n    <string name="no_data_short">—</string>\n',
        new='    <string name="dashboard_rings_calories">Калории</string>\n    <string name="dashboard_edit_layout">Редактировать главный экран</string>\n    <string name="dashboard_edit_layout_title">Редактирование экрана</string>\n    <string name="dashboard_edit_layout_body">Показывай, скрывай и меняй местами карточки на главном экране. Изменения применяются сразу.</string>\n    <string name="dashboard_card_streak_label">Серия дней</string>\n    <string name="no_data_short">—</string>\n',
        desc='add card-layout-editor strings (RU)',
    )

    print("==> Best-effort compile check")
    gradlew = ROOT / "gradlew"
    if gradlew.exists():
        result = subprocess.run(
            ["./gradlew", ":app:compileDebugKotlin", "--console=plain"],
            cwd=ROOT,
        )
        if result.returncode != 0:
            die("compileDebugKotlin failed -- NOT committing or pushing. "
                "Fix the error above (or paste it back) before re-running.")
        print("==> Compile check passed")
    else:
        print("   gradlew not found -- skipping compile check (unexpected outside "
              "a throwaway sandbox; NOT committing automatically).")
        return

    print("==> git add / commit / push")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    commit = subprocess.run(
        ["git", "commit", "-m",
         "Add reorderable/hideable dashboard cards with an edit-layout pencil icon"],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("   (nothing to commit -- all edits were likely already applied)")
        return
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)
    print("==> Done: pushed to origin/main")


if __name__ == "__main__":
    main()
