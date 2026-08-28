#!/usr/bin/env python3
"""
patch_settings_minimalism_v1.py

Settings screen minimalism pass (2026-08-27), plus repo-root script cleanup.

FinalBitLutShell.kt changes:
  1. Data source card: title trimmed to "Data source" / "Источник данных"
     (data_source_section_title, unchanged key, unchanged text). Body
     paragraph dropped. Per-row subtitles dropped -- DataSourceToggleRow's
     `subtitle` parameter removed entirely (verified: only 2 call sites,
     both here, both updated in the same edit).
  2. Connection card merge: the three separate SettingsConnectionCard
     instances (Google connect/refresh, Huawei connect/refresh, manual
     sync/import archive) are merged into a single SoftCard containing
     three button rows. No per-source title text, buttons only, per
     explicit product decision. SettingsConnectionCard itself is deleted
     (verified: those were its only 3 call sites in the codebase).
  3. Workout filtering card removed entirely: title, body copy, minimum-
     duration presets, and per-exercise-type checkboxes. WidgetVisibilityRow
     is deleted alongside it (verified: only used inside this card).
     WorkoutFilterPrefs itself is NOT touched -- it is still read at sync
     time by the real sync path; only this Settings UI card is gone.
  4. "What data is shared?" and "Export my data as CSV" links removed from
     Settings, along with the showDataScopes toggle state. Per explicit
     confirmation, DataScopesScreen (the full-screen destination the first
     link opened) is deleted entirely as dead code (verified:
     OnboardingScopeRow, which DataScopesScreen used, is still used
     elsewhere -- in PermissionsOnboardingScreen -- so it stays).
     onExportCsv itself is left as a real, still-wired parameter
     (MainActivity -> SettingsScreen -> CsvExporter); only the UI trigger
     for it in Settings is gone, since CSV export is a separate, working
     feature outside the scope of this cleanup.

strings.xml / strings-ru.xml changes:
  Removed string resources that became orphaned by the above (verified:
  zero remaining references in FinalBitLutShell.kt after the Kotlin edits):
  workout_filter_section_title/body, workout_filter_min_duration_*,
  workout_filter_type_* (6 keys), manual_sync_title, google_health_connect,
  huawei_health_title, data_source_section_body, data_source_huawei_body,
  data_source_google_fit_body, data_scopes_link, data_scopes_title/body/
  step/distance/activity/activity_record/history_week/destination/close,
  export_csv_link. Deliberately NOT touched: widget_visibility_section_*
  and widget_toggle_steps/workouts, which were already unused before this
  patch and are unrelated to this change (out of scope; not introduced or
  worsened by this patch).

Repo cleanup:
  Removes 32 one-off historical patch/hotfix/verify scripts from the repo
  root and scripts/ that are pure delivery artifacts from past sessions --
  verified via grep against build.gradle.kts, app/build.gradle.kts, and
  settings.gradle.kts that none of them are referenced by the build. Each
  deleted file is backed up to .bitlut_patch_backup/ first, same as any
  other patch, so this remains reversible.

Usage:
    python3 patch_settings_minimalism_v1.py

Behavior:
    1. Backs up every touched/deleted file to .bitlut_patch_backup/
    2. Applies text-anchored edits to FinalBitLutShell.kt (whole-block
       replacements, each anchor verified unique before this script was
       written)
    3. Applies text-anchored edits to both strings.xml files
    4. Deletes the 32 stale scripts (idempotent: already-deleted files are
       skipped, not treated as an error)
    5. Runs :app:compileDebugKotlin as a compile gate
    6. On success: git add -A && git commit && git push origin HEAD:main
    7. On failure: dies with a clear message, no commit, no push
"""

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SHELL_KT = REPO_ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
STRINGS_EN = REPO_ROOT / "app/src/main/res/values/strings.xml"
STRINGS_RU = REPO_ROOT / "app/src/main/res/values-ru/strings.xml"
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"

STALE_SCRIPTS = [
    "bitlut_workout_metrics_aggregate_fix.py",
    "cleanup_repo_stray_backups_v1.py",
    "cleanup_stray_res_backups_v1.py",
    "hotfix_biking_calories_v7.py",
    "hotfix_biking_no_fourth_slot_v8.py",
    "patch_august_v3_dark_theme_v3.py",
    "patch_dark_icons_navbar_bounce_biking_v5.py",
    "patch_docs_refresh_v6.py",
    "patch_hc_recording_method_v10.py",
    "patch_hc_recording_method_v11.py",
    "patch_hc_recording_method_v9.py",
    "patch_hero_tangerine_navbar_v4.py",
    "patch_manifest_total_calories_permission_v1.py",
    "patch_manifest_total_calories_permission_v2.py",
    "patch_session_handoff_2026_08_26_v1.py",
    "patch_stale_cache_and_strength_metrics_v1.py",
    "patch_workout_calorie_estimate_v1.py",
    "patch_workout_card_four_metrics.py",
    "patch_walking_three_slots_v1.py",
    "scripts/verify_august_v3_build_fix.py",
    "scripts/verify_dashboard_persistence_sprint.py",
    "scripts/verify_dashboard_premium.py",
    "scripts/verify_data_source_selector.py",
    "scripts/verify_huawei_truth_fix.py",
    "scripts/verify_insights_goals_onboarding_sprint.py",
    "scripts/verify_reliability_and_design_sprint.py",
    "scripts/verify_sync_august_v3_recovery.py",
    "scripts/verify_sync_integrity_patch.py",
    "scripts/verify_workout_data_august_v3_product_sprint.py",
    "scripts/verify_workout_history_and_goals_removal.py",
    "scripts/verify_workout_metric_boundary_recovery.py",
    "scripts/verify_workout_metrics_aggregate_fix.py",
    "scripts/verify_workout_nav_freshness_sprint.py",
]


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


def backup_file(path: Path) -> None:
    if not path.exists():
        die(f"Cannot back up missing file: {path}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:10]
    dest = BACKUP_DIR / f"{path.name}.{digest}.bak"
    if not dest.exists():
        shutil.copy2(path, dest)
        print(f"Backed up {path} -> {dest}")
    else:
        print(f"Backup already exists at {dest}, leaving it in place")


def apply_edit(path: Path, old: str, new: str) -> bool:
    """
    Genuine replacement helper (exact-occurrence-count check on old_str
    only). Returns True if applied, False if already applied (idempotent
    skip). Dies on any other state.

    Deliberately does NOT cross-check new_str's occurrence count as a
    pre-patch signal: several of this script's edits are near-pure
    insertions/deletions where new_str is a substring of old_str (e.g.
    removing a single line from a larger anchor). In that case new_str's
    count is already >=1 in the untouched file, which would falsely read
    as "already applied" under a new_count-based check. old_str's count is
    the only reliable signal: 1 means unpatched, 0 means patched (since
    old_str itself is the thing this edit removes/replaces), anything else
    is a real anomaly worth stopping for.
    """
    text = path.read_text(encoding="utf-8")
    old_count = text.count(old)

    if old_count == 1:
        text = text.replace(old, new, 1)
        path.write_text(text, encoding="utf-8")
        return True

    if old_count == 0:
        return False

    die(
        "Unexpected file state for edit.\n"
        f"  old_str occurrences: {old_count} (expected exactly 1 pre-patch or 0 post-patch)\n"
        f"  file: {path}\n"
        "Refusing to guess; inspect the file manually."
    )


def run(cmd: list, cwd: Path) -> None:
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        die(f"Command failed ({result.returncode}): {' '.join(cmd)}")


# ---------------------------------------------------------------------------
# FinalBitLutShell.kt edits
# ---------------------------------------------------------------------------

KT_EDIT_1_OLD = '''        Text(
            text = stringResource(R.string.data_source_section_title),
            color = palette.text,
            fontWeight = FontWeight.ExtraBold,
            fontSize = 18.sp
        )
        SoftCard(palette = palette, accent = HealthAccent.violet(), hero = false, tintWithAccent = true) {
            Text(
                text = stringResource(R.string.data_source_section_body),
                color = palette.secondaryText,
                fontWeight = FontWeight.Medium,
                fontSize = 13.sp,
                lineHeight = 18.sp
            )
            Spacer(Modifier.height(10.dp))
            DataSourceToggleRow(
                palette = palette,
                title = stringResource(R.string.data_source_huawei_title),
                subtitle = stringResource(R.string.data_source_huawei_body),
                accent = HealthAccent.activity(),
                selected = syncState.selectedDataSource == HealthDataSource.HUAWEI_HEALTH,
                onSelect = { onDataSourceSelected(HealthDataSource.HUAWEI_HEALTH) }
            )
            DataSourceToggleRow(
                palette = palette,
                title = stringResource(R.string.data_source_google_fit_title),
                subtitle = stringResource(R.string.data_source_google_fit_body),
                accent = HealthAccent.mind(),
                selected = syncState.selectedDataSource == HealthDataSource.GOOGLE_FIT,
                onSelect = { onDataSourceSelected(HealthDataSource.GOOGLE_FIT) },
                isLast = true
            )
        }

        SettingsConnectionCard(
            palette = palette,
            title = stringResource(R.string.google_health_connect),
            accent = HealthAccent.mind(),
            icon = Icons.Rounded.Cloud,
            primaryAction = stringResource(R.string.connect_google_button),
            onPrimaryAction = onRequestGoogle,
            secondaryAction = stringResource(R.string.refresh_status),
            onSecondaryAction = onSyncNow
        )

        SettingsConnectionCard(
            palette = palette,
            title = stringResource(R.string.huawei_health_title),
            accent = HealthAccent.activity(),
            icon = Icons.Rounded.Watch,
            primaryAction = stringResource(R.string.connect_huawei_button),
            onPrimaryAction = onRequestHuawei,
            secondaryAction = stringResource(R.string.refresh_status),
            onSecondaryAction = onRefresh
        )'''

KT_EDIT_1_NEW = '''        Text(
            text = stringResource(R.string.data_source_section_title),
            color = palette.text,
            fontWeight = FontWeight.ExtraBold,
            fontSize = 18.sp
        )
        SoftCard(palette = palette, accent = HealthAccent.violet(), hero = false, tintWithAccent = true) {
            DataSourceToggleRow(
                palette = palette,
                title = stringResource(R.string.data_source_huawei_title),
                accent = HealthAccent.activity(),
                selected = syncState.selectedDataSource == HealthDataSource.HUAWEI_HEALTH,
                onSelect = { onDataSourceSelected(HealthDataSource.HUAWEI_HEALTH) }
            )
            DataSourceToggleRow(
                palette = palette,
                title = stringResource(R.string.data_source_google_fit_title),
                accent = HealthAccent.mind(),
                selected = syncState.selectedDataSource == HealthDataSource.GOOGLE_FIT,
                onSelect = { onDataSourceSelected(HealthDataSource.GOOGLE_FIT) },
                isLast = true
            )
        }

        // Sprint (2026-08-27): all three connect/refresh/sync/import actions
        // merged into one card, buttons only -- no per-source title and no
        // captioning text. Previously three separate SettingsConnectionCard
        // instances (Google, Huawei, manual sync), each with its own title
        // row; the title added no information the button text didn't already
        // convey (e.g. "Google Health Connect" heading above a "Connect
        // Google Health" button), so it was dropped as part of the same
        // minimalism pass as the Data source card above.
        SoftCard(palette = palette, accent = HealthAccent.violet(), hero = false, tintWithAccent = true) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                PrimaryButton(
                    text = stringResource(R.string.connect_google_button),
                    compact = true,
                    modifier = Modifier.weight(1f),
                    onClick = onRequestGoogle
                )
                SecondaryButton(
                    text = stringResource(R.string.refresh_status),
                    palette = palette,
                    compact = true,
                    modifier = Modifier.weight(1f),
                    onClick = onSyncNow
                )
            }
            Spacer(Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                PrimaryButton(
                    text = stringResource(R.string.connect_huawei_button),
                    compact = true,
                    modifier = Modifier.weight(1f),
                    onClick = onRequestHuawei
                )
                SecondaryButton(
                    text = stringResource(R.string.refresh_status),
                    palette = palette,
                    compact = true,
                    modifier = Modifier.weight(1f),
                    onClick = onRefresh
                )
            }
            Spacer(Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                PrimaryButton(
                    text = stringResource(R.string.sync_now),
                    compact = true,
                    modifier = Modifier.weight(1f),
                    onClick = onSyncNow
                )
                SecondaryButton(
                    text = stringResource(R.string.import_archive_title),
                    palette = palette,
                    compact = true,
                    modifier = Modifier.weight(1f),
                    onClick = onImportArchive
                )
            }
        }'''

KT_EDIT_1B_OLD = '''        SettingsConnectionCard(
            palette = palette,
            title = stringResource(R.string.manual_sync_title),
            accent = HealthAccent.violet(),
            icon = Icons.Rounded.CloudSync,
            primaryAction = stringResource(R.string.sync_now),
            onPrimaryAction = onSyncNow,
            secondaryAction = stringResource(R.string.import_archive_title),
            onSecondaryAction = onImportArchive
        )

        Text(
            text = stringResource(R.string.dashboard_goals_section_title),'''

KT_EDIT_1B_NEW = '''        Text(
            text = stringResource(R.string.dashboard_goals_section_title),'''

KT_EDIT_2_OLD = '''    var showDataScopes by androidx.compose.runtime.remember { androidx.compose.runtime.mutableStateOf(false) }

    // Settings exposes only the steps goal because it is the only daily goal
    // currently used by the product. Other health targets must not exist as
    // decorative controls without downstream behavior.
    Box(modifier = Modifier.fillMaxSize()) {
    Column(
        modifier = Modifier'''

KT_EDIT_2_NEW = '''    // Settings exposes only the steps goal because it is the only daily goal
    // currently used by the product. Other health targets must not exist as
    // decorative controls without downstream behavior.
    Box(modifier = Modifier.fillMaxSize()) {
    Column(
        modifier = Modifier'''

KT_EDIT_3_OLD = '''        Text(
            text = stringResource(R.string.workout_filter_section_title),
            color = palette.text,
            fontWeight = FontWeight.ExtraBold,
            fontSize = 18.sp
        )
        SoftCard(palette = palette, accent = HealthAccent.activity(), tintWithAccent = true) {
            val context = LocalContext.current
            val workoutFilterPrefs = remember { com.openhealth.sync.config.WorkoutFilterPrefs(context) }
            var minDurationMinutes by remember { mutableStateOf(workoutFilterPrefs.minDurationMinutes()) }
            var excludedTypes by remember { mutableStateOf(workoutFilterPrefs.excludedExerciseTypes()) }

            Text(
                text = stringResource(R.string.workout_filter_section_body),
                color = palette.secondaryText,
                fontWeight = FontWeight.Medium,
                fontSize = 13.sp,
                lineHeight = 18.sp
            )
            Spacer(Modifier.height(14.dp))
            Text(
                text = stringResource(R.string.workout_filter_min_duration_label),
                color = palette.text,
                fontWeight = FontWeight.Bold,
                fontSize = 13.sp
            )
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                com.openhealth.sync.config.WorkoutFilterPrefs.MIN_DURATION_PRESETS_MINUTES.forEach { minutes ->
                    val selected = minDurationMinutes == minutes
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(99.dp))
                            .background(if (selected) HealthAccent.activity() else palette.stroke.copy(alpha = 0.3f))
                            .clickable {
                                minDurationMinutes = minutes
                                workoutFilterPrefs.setMinDurationMinutes(minutes)
                            }
                            .padding(horizontal = 12.dp, vertical = 7.dp)
                    ) {
                        Text(
                            text = if (minutes == 0) {
                                stringResource(R.string.workout_filter_min_duration_off)
                            } else {
                                stringResource(R.string.workout_filter_min_duration_value, minutes)
                            },
                            color = if (selected) Color.White else palette.text,
                            fontWeight = FontWeight.Bold,
                            fontSize = 12.sp
                        )
                    }
                }
            }
            Spacer(Modifier.height(16.dp))
            val categories = listOf(
                stringResource(R.string.workout_filter_type_walking) to listOf(ExerciseSessionRecord.EXERCISE_TYPE_WALKING),
                stringResource(R.string.workout_filter_type_running) to listOf(ExerciseSessionRecord.EXERCISE_TYPE_RUNNING),
                stringResource(R.string.workout_filter_type_biking) to listOf(ExerciseSessionRecord.EXERCISE_TYPE_BIKING),
                stringResource(R.string.workout_filter_type_swimming) to listOf(
                    ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_POOL,
                    ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_OPEN_WATER
                ),
                stringResource(R.string.workout_filter_type_strength) to listOf(ExerciseSessionRecord.EXERCISE_TYPE_STRENGTH_TRAINING),
                stringResource(R.string.workout_filter_type_hiking) to listOf(ExerciseSessionRecord.EXERCISE_TYPE_HIKING)
            )
            categories.forEachIndexed { index, (label, exerciseTypes) ->
                WidgetVisibilityRow(
                    palette = palette,
                    label = label,
                    accent = HealthAccent.activity(),
                    checked = exerciseTypes.none { it in excludedTypes },
                    onCheckedChange = { checked ->
                        val updated = if (checked) {
                            excludedTypes - exerciseTypes.toSet()
                        } else {
                            excludedTypes + exerciseTypes.toSet()
                        }
                        excludedTypes = updated
                        workoutFilterPrefs.setExcludedExerciseTypes(updated)
                    },
                    isLast = index == categories.lastIndex
                )
            }
        }

        Text(
            text = stringResource(R.string.data_scopes_link),
            color = palette.secondaryText,
            fontWeight = FontWeight.SemiBold,
            fontSize = 13.sp,
            textDecoration = androidx.compose.ui.text.style.TextDecoration.Underline,
            modifier = Modifier
                .padding(top = 4.dp)
                .clickable { showDataScopes = true }
        )

        Text(
            text = stringResource(R.string.export_csv_link),
            color = palette.secondaryText,
            fontWeight = FontWeight.SemiBold,
            fontSize = 13.sp,
            textDecoration = androidx.compose.ui.text.style.TextDecoration.Underline,
            modifier = Modifier
                .padding(top = 2.dp, bottom = 8.dp)
                .clickable { onExportCsv() }
        )
    }

    if (showDataScopes) {
        DataScopesScreen(palette = palette, onClose = { showDataScopes = false })
    }
    }
}'''

KT_EDIT_3_NEW = '''    }
    }
}'''

KT_EDIT_4_OLD = '''/**
 * Trust screen (sprint 2026-07-14): a plain-language, complete list of the
 * exact 5 Huawei Health Kit scopes BitLut requests -- not a marketing
 * summary, the actual list, matching requestedScopeNames() in
 * HuaweiHealthManager verbatim in substance (5 items, same order). Answers
 * the single most common complaint pattern seen in reviews of similar sync
 * apps: "I don't understand what's being synced where." No dismiss-and-never
 * shown-again state -- this is meant to be checked back in on, so it's
 * reachable any time from Settings rather than a one-time onboarding step.
 */
@Composable
private fun DataScopesScreen(palette: BitPalette, onClose: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(palette.backgroundBrush)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp, vertical = 32.dp),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            Column {
                Icon(
                    Icons.Rounded.Cloud,
                    contentDescription = null,
                    tint = HealthAccent.mind(),
                    modifier = Modifier.size(40.dp)
                )
                Spacer(Modifier.height(20.dp))
                Text(
                    text = stringResource(R.string.data_scopes_title),
                    color = palette.text,
                    fontWeight = FontWeight.ExtraBold,
                    fontSize = 26.sp
                )
                Spacer(Modifier.height(10.dp))
                Text(
                    text = stringResource(R.string.data_scopes_body),
                    color = palette.secondaryText,
                    fontWeight = FontWeight.Medium,
                    fontSize = 15.sp,
                    lineHeight = 21.sp
                )
                Spacer(Modifier.height(24.dp))
                OnboardingScopeRow(palette = palette, icon = Icons.Rounded.DirectionsRun, text = stringResource(R.string.data_scopes_step))
                OnboardingScopeRow(palette = palette, icon = Icons.Rounded.TrendingUp, text = stringResource(R.string.data_scopes_distance))
                OnboardingScopeRow(palette = palette, icon = Icons.Rounded.Watch, text = stringResource(R.string.data_scopes_activity))
                OnboardingScopeRow(palette = palette, icon = Icons.Rounded.LocalFireDepartment, text = stringResource(R.string.data_scopes_activity_record))
                OnboardingScopeRow(palette = palette, icon = Icons.Rounded.Schedule, text = stringResource(R.string.data_scopes_history_week))
                Spacer(Modifier.height(16.dp))
                Text(
                    text = stringResource(R.string.data_scopes_destination),
                    color = palette.secondaryText,
                    fontWeight = FontWeight.Medium,
                    fontSize = 12.sp,
                    lineHeight = 17.sp
                )
            }

            PrimaryButton(
                text = stringResource(R.string.data_scopes_close),
                onClick = onClose
            )
        }
    }
}

@Composable
private fun'''

KT_EDIT_4_NEW = '''@Composable
private fun'''

KT_EDIT_5_OLD = '''/** Single toggle row inside the Widgets settings card: label + Switch. [isLast]
 *  suppresses the bottom spacer so the card doesn't end with extra trailing gap. */
@Composable
private fun WidgetVisibilityRow(
    palette: BitPalette,
    label: String,
    accent: Color,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
    isLast: Boolean = false
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = label,
            color = palette.text,
            fontWeight = FontWeight.SemiBold,
            fontSize = 14.sp
        )
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            colors = SwitchDefaults.colors(
                checkedThumbColor = AugustColor.Surface,
                checkedTrackColor = AugustColor.Tangerine,
                uncheckedThumbColor = Color.White,
                uncheckedTrackColor = palette.stroke
            )
        )
    }
    if (!isLast) {
        Spacer(Modifier.height(8.dp))
    }
}

/**
 * Existing metric/decorative accents mapped onto August v3 Purple.'''

KT_EDIT_5_NEW = '''/**
 * Existing metric/decorative accents mapped onto August v3 Purple.'''

KT_EDIT_6_OLD = '''@Composable
private fun SettingsConnectionCard(
    palette: BitPalette,
    title: String,
    accent: Color,
    icon: ImageVector,
    primaryAction: String,
    onPrimaryAction: () -> Unit,
    secondaryAction: String? = null,
    onSecondaryAction: (() -> Unit)? = null
) {
    // Sprint (2026-07-08): dropped the body/status text entirely (title +
    // icon only per request) and replaced the wrapping FlowRow with a plain
    // Row so the two actions are always on one line, each taking half the
    // width, instead of sometimes wrapping to a second line.
    SoftCard(palette = palette, accent = accent, hero = false, tintWithAccent = true) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(32.dp)
                    .clip(RoundedCornerShape(16.dp))
                    .background(accent.copy(alpha = 0.16f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(icon, contentDescription = null, tint = accent, modifier = Modifier.size(16.dp))
            }
            Spacer(Modifier.width(10.dp))
            Text(
                text = title,
                color = palette.text,
                fontWeight = FontWeight.ExtraBold,
                fontSize = 15.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f)
            )
        }
        Spacer(Modifier.height(10.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            PrimaryButton(
                text = primaryAction,
                compact = true,
                modifier = Modifier.weight(1f),
                onClick = onPrimaryAction
            )
            if (secondaryAction != null && onSecondaryAction != null) {
                SecondaryButton(
                    text = secondaryAction,
                    palette = palette,
                    compact = true,
                    modifier = Modifier.weight(1f),
                    onClick = onSecondaryAction
                )
            }
        }
    }
}

internal data class BitPalette('''

KT_EDIT_6_NEW = '''internal data class BitPalette('''

KT_EDIT_7_OLD = '''private fun DataSourceToggleRow(
    palette: BitPalette,
    title: String,
    subtitle: String,
    accent: Color,
    selected: Boolean,
    onSelect: () -> Unit,
    isLast: Boolean = false
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f).padding(end = 12.dp)) {
            Text(
                text = title,
                color = palette.text,
                fontWeight = FontWeight.Bold,
                fontSize = 14.sp
            )
            Text(
                text = subtitle,
                color = palette.secondaryText,
                fontWeight = FontWeight.Medium,
                fontSize = 12.sp,
                lineHeight = 16.sp
            )
        }
        Switch('''

KT_EDIT_7_NEW = '''private fun DataSourceToggleRow(
    palette: BitPalette,
    title: String,
    accent: Color,
    selected: Boolean,
    onSelect: () -> Unit,
    isLast: Boolean = false
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = title,
            color = palette.text,
            fontWeight = FontWeight.Bold,
            fontSize = 14.sp,
            modifier = Modifier.weight(1f).padding(end = 12.dp)
        )
        Switch('''

KT_EDITS = [
    ("data source card simplification + connection card merge", KT_EDIT_1_OLD, KT_EDIT_1_NEW),
    ("remove now-merged manual sync SettingsConnectionCard", KT_EDIT_1B_OLD, KT_EDIT_1B_NEW),
    ("remove showDataScopes state", KT_EDIT_2_OLD, KT_EDIT_2_NEW),
    ("remove workout filter card + data scope/export links", KT_EDIT_3_OLD, KT_EDIT_3_NEW),
    ("delete DataScopesScreen composable", KT_EDIT_4_OLD, KT_EDIT_4_NEW),
    ("delete WidgetVisibilityRow composable", KT_EDIT_5_OLD, KT_EDIT_5_NEW),
    ("delete SettingsConnectionCard composable", KT_EDIT_6_OLD, KT_EDIT_6_NEW),
    ("drop subtitle param from DataSourceToggleRow", KT_EDIT_7_OLD, KT_EDIT_7_NEW),
]

# ---------------------------------------------------------------------------
# strings.xml (EN) edits
# ---------------------------------------------------------------------------

EN_EDITS = [
    (
        "remove workout_filter_* keys (EN)",
        '''    <string name="workout_speed_value">%1$s km/h</string>
    <string name="workout_swim_pace_value">%1$s /100 m</string>
    <string name="workout_filter_section_title">Workout filtering</string>
    <string name="workout_filter_section_body">Choose which workouts get synced as their own workout cards. Steps, distance, and calories for that time still sync either way.</string>
    <string name="workout_filter_min_duration_label">Minimum duration</string>
    <string name="workout_filter_min_duration_off">Off</string>
    <string name="workout_filter_min_duration_value">%1$d min</string>
    <string name="workout_filter_type_walking">Walking</string>
    <string name="workout_filter_type_running">Running</string>
    <string name="workout_filter_type_biking">Biking</string>
    <string name="workout_filter_type_swimming">Swimming</string>
    <string name="workout_filter_type_strength">Strength training</string>
    <string name="workout_filter_type_hiking">Hiking</string>
    <string name="widget_visibility_section_title">Widgets</string>''',
        '''    <string name="workout_speed_value">%1$s km/h</string>
    <string name="workout_swim_pace_value">%1$s /100 m</string>
    <string name="widget_visibility_section_title">Widgets</string>''',
    ),
    (
        "remove manual_sync_title (EN)",
        '''    <string name="manual_sync_title">Manual sync</string>
    <string name="import_archive_title">Import archive</string>''',
        '''    <string name="import_archive_title">Import archive</string>''',
    ),
    (
        "remove google_health_connect / huawei_health_title (EN)",
        '''    <string name="summary_short_title">Summary</string>
    <string name="google_health_connect">Google Health Connect</string>
    <string name="huawei_health_title">Huawei Health</string>
    <string name="huawei_pending_approval_title">Waiting for Huawei\\'s approval</string>''',
        '''    <string name="summary_short_title">Summary</string>
    <string name="huawei_pending_approval_title">Waiting for Huawei\\'s approval</string>''',
    ),
    (
        "remove data_source_*_body keys (EN)",
        '''    <string name="data_source_section_title">Data source</string>
    <string name="data_source_section_body">Choose one source for the Dashboard. The other source is excluded so steps and distance are not counted twice.</string>
    <string name="data_source_huawei_title">Huawei Health</string>
    <string name="data_source_huawei_body">Imported by BitLut; the Dashboard shows only BitLut records.</string>
    <string name="data_source_google_fit_title">Google Fit</string>
    <string name="data_source_google_fit_body">The Dashboard reads only Google Fit records from Health Connect.</string>''',
        '''    <string name="data_source_section_title">Data source</string>
    <string name="data_source_huawei_title">Huawei Health</string>
    <string name="data_source_google_fit_title">Google Fit</string>''',
    ),
    (
        "remove data_scopes_* and export_csv_link keys (EN)",
        '''    <string name="onboarding_privacy_note">BitLut never reads or shares sleep, heart rate, or any other health data. Only activity metrics move from Huawei Health into Google Health Connect, and stay on your device.</string>
    <string name="data_scopes_link">What data is shared?</string>
    <string name="data_scopes_title">What moves, and where</string>
    <string name="data_scopes_body">BitLut asks Huawei Health Kit for exactly 5 permissions. Nothing more is requested, read, or stored.</string>
    <string name="data_scopes_step">Daily step count</string>
    <string name="data_scopes_distance">Distance walked or run</string>
    <string name="data_scopes_activity">Workout type and time (e.g. running, cycling)</string>
    <string name="data_scopes_activity_record">Live workout details — duration, active calories</string>
    <string name="data_scopes_history_week">The last 7 days of history, to back-fill on first sync</string>
    <string name="data_scopes_destination">All of it goes to one place: Google Health Connect, on this device. No BitLut server, no BitLut account, no ads, nothing sent anywhere else.</string>
    <string name="data_scopes_close">Got it</string>
    <string name="export_csv_link">Export my data as CSV</string>
    <string name="widget_steps_label">steps</string>''',
        '''    <string name="onboarding_privacy_note">BitLut never reads or shares sleep, heart rate, or any other health data. Only activity metrics move from Huawei Health into Google Health Connect, and stay on your device.</string>
    <string name="widget_steps_label">steps</string>''',
    ),
]

RU_EDITS = [
    (
        "remove workout_filter_* keys (RU)",
        '''    <string name="workout_speed_value">%1$s км/ч</string>
    <string name="workout_swim_pace_value">%1$s /100 м</string>
    <string name="workout_filter_section_title">Фильтр тренировок</string>
    <string name="workout_filter_section_body">Выбери, какие тренировки синкать отдельными карточками. Шаги, дистанция и калории за это время синкаются в любом случае.</string>
    <string name="workout_filter_min_duration_label">Минимальная длительность</string>
    <string name="workout_filter_min_duration_off">Выкл.</string>
    <string name="workout_filter_min_duration_value">%1$d мин</string>
    <string name="workout_filter_type_walking">Ходьба</string>
    <string name="workout_filter_type_running">Бег</string>
    <string name="workout_filter_type_biking">Велосипед</string>
    <string name="workout_filter_type_swimming">Плавание</string>
    <string name="workout_filter_type_strength">Силовая тренировка</string>
    <string name="workout_filter_type_hiking">Поход</string>''',
        '''    <string name="workout_speed_value">%1$s км/ч</string>
    <string name="workout_swim_pace_value">%1$s /100 м</string>''',
    ),
    (
        "remove manual_sync_title (RU)",
        '''    <string name="manual_sync_title">Ручная синхронизация</string>
    <string name="import_archive_title">Импорт архива</string>''',
        '''    <string name="import_archive_title">Импорт архива</string>''',
    ),
    (
        "remove google_health_connect / huawei_health_title (RU)",
        '''    <string name="summary_short_title">Сводка</string>
    <string name="google_health_connect">Google Health Connect</string>
    <string name="huawei_health_title">Huawei Health</string>
    <string name="huawei_pending_approval_title">Ждём подтверждения от Huawei</string>''',
        '''    <string name="summary_short_title">Сводка</string>
    <string name="huawei_pending_approval_title">Ждём подтверждения от Huawei</string>''',
    ),
    (
        "remove data_source_*_body keys (RU)",
        '''    <string name="data_source_section_title">Источник данных</string>
    <string name="data_source_section_body">Выберите один источник для Dashboard. Второй источник исключается, чтобы шаги и дистанция не суммировались дважды.</string>
    <string name="data_source_huawei_title">Huawei Health</string>
    <string name="data_source_huawei_body">Импорт через BitLut; Dashboard показывает только записи BitLut.</string>
    <string name="data_source_google_fit_title">Google Fit</string>
    <string name="data_source_google_fit_body">Dashboard читает только записи Google Fit из Health Connect.</string>''',
        '''    <string name="data_source_section_title">Источник данных</string>
    <string name="data_source_huawei_title">Huawei Health</string>
    <string name="data_source_google_fit_title">Google Fit</string>''',
    ),
    (
        "remove data_scopes_* and export_csv_link keys (RU)",
        '''    <string name="onboarding_privacy_note">BitLut никогда не читает и не передаёт данные о сне, пульсе или другие показатели здоровья. Из Huawei Health в Google Health Connect передаются только данные активности, и они остаются на вашем устройстве.</string>
    <string name="data_scopes_link">Что именно передаётся?</string>
    <string name="data_scopes_title">Что и куда уходит</string>
    <string name="data_scopes_body">BitLut запрашивает у Huawei Health Kit ровно 5 разрешений. Больше ничего не запрашивается, не читается и не хранится.</string>
    <string name="data_scopes_step">Количество шагов за день</string>
    <string name="data_scopes_distance">Пройденное или пробежанное расстояние</string>
    <string name="data_scopes_activity">Тип и время тренировки (бег, велосипед и т.д.)</string>
    <string name="data_scopes_activity_record">Детали тренировки в реальном времени — длительность, активные калории</string>
    <string name="data_scopes_history_week">Последние 7 дней истории — нужно для первой синхронизации</string>
    <string name="data_scopes_destination">Всё это уходит в одно место: Google Health Connect на этом же устройстве. Нет сервера BitLut, нет аккаунта BitLut, нет рекламы, никуда больше ничего не отправляется.</string>
    <string name="data_scopes_close">Понятно</string>
    <string name="export_csv_link">Экспортировать мои данные в CSV</string>
    <string name="widget_steps_label">шагов</string>''',
        '''    <string name="onboarding_privacy_note">BitLut никогда не читает и не передаёт данные о сне, пульсе или другие показатели здоровья. Из Huawei Health в Google Health Connect передаются только данные активности, и они остаются на вашем устройстве.</string>
    <string name="widget_steps_label">шагов</string>''',
    ),
]


def apply_edit_group(label: str, path: Path, edits: list) -> bool:
    if not path.exists():
        die(f"Target file not found: {path}")
    backup_file(path)
    any_applied = False
    for name, old, new in edits:
        applied = apply_edit(path, old, new)
        print(f"  [{label}] {name}: {'applied' if applied else 'already applied, skipped'}")
        any_applied = any_applied or applied
    return any_applied


def remove_stale_scripts() -> bool:
    any_removed = False
    for rel_path in STALE_SCRIPTS:
        path = REPO_ROOT / rel_path
        if not path.exists():
            print(f"  [cleanup] {rel_path}: already removed, skipping")
            continue
        backup_file(path)
        path.unlink()
        print(f"  [cleanup] {rel_path}: removed")
        any_removed = True
    return any_removed


def main() -> None:
    changed = False

    changed |= apply_edit_group("FinalBitLutShell.kt", SHELL_KT, KT_EDITS)
    changed |= apply_edit_group("strings.xml", STRINGS_EN, EN_EDITS)
    changed |= apply_edit_group("strings.xml (ru)", STRINGS_RU, RU_EDITS)
    changed |= remove_stale_scripts()

    if not changed:
        print("Already applied -- nothing to do, skipping compile/commit/push.")
        return

    gradlew = REPO_ROOT / "gradlew"
    if not gradlew.exists():
        die(f"gradlew not found at {gradlew}; cannot run compile gate.")

    run(
        [
            str(gradlew),
            ":app:compileDebugKotlin",
            "--no-daemon",
            "--max-workers=1",
            "--no-watch-fs",
            "--console=plain",
            "-Dorg.gradle.jvmargs=-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8",
            "-Pkotlin.compiler.execution.strategy=in-process",
        ],
        cwd=REPO_ROOT,
    )

    print("Compile gate passed. Committing and pushing.")
    run(["git", "add", "-A"], cwd=REPO_ROOT)
    run(
        [
            "git",
            "commit",
            "-m",
            "Simplify Settings screen (minimal data source card, merged connection "
            "card, remove workout filter card and data-scope/export links); "
            "remove stale one-off patch scripts",
        ],
        cwd=REPO_ROOT,
    )
    run(["git", "push", "origin", "HEAD:main"], cwd=REPO_ROOT)
    print("Done.")


if __name__ == "__main__":
    main()
