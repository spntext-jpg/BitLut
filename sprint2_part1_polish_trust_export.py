#!/usr/bin/env python3
"""
sprint2_part1_polish_trust_export.py

BitLut patch script -- sprint 2 (2026-07-14), part 1 of 2.

Implements 4 of the 5 items from this sprint's plan:
  (b) Edge-to-edge + predictive back, brought up to date for Android 15/16.
  (c) A "What data is shared" trust screen listing the real 5 Huawei scopes,
      reachable any time from Settings.
  (d) A calm, specific status card for the Huawei 50005 "pending approval"
      wait state, instead of a silent no-op degrade.
  (e) CSV export of the same daily totals + recent workouts BitLut already
      reads for its own dashboard, via the system share sheet.

Item (a), the home screen widget, is deliberately a SEPARATE script
(sprint2_part2_home_widget.py) -- it's the one piece that adds a new Gradle
dependency (androidx.glance) and a new manifest <receiver>, so it's the
highest-risk piece to isolate. Run this script first; part 2 does not
depend on it, but the natural order is polish/trust/export, then widget.

Run from the repo root inside your Codespace:
    python3 sprint2_part1_polish_trust_export.py

Conventions followed (see CLAUDE.md): backs up every touched file first;
every edit is a regex-anchored (exact substring) old_str -> new_str
replacement, count-verified == 1 before applying; idempotent (checks the
OLD anchor's count first, not just whether NEW text is already present --
see the comment on apply_edit() for why that ordering matters); creates 2
new files (CsvExporter.kt, file_paths.xml); best-effort Gradle compile gate
before committing; pushes only if it passes.
"""

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / f"{TIMESTAMP}_sprint2_part1_polish_trust_export"

touched_files = set()
edits_applied = 0
edits_skipped = 0


def log(msg):
    print(f"==> {msg}")


def backup(path: Path):
    if path in touched_files:
        return
    touched_files.add(path)
    rel = path.relative_to(ROOT)
    dest = BACKUP_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, dest)


def apply_edit(rel_path: str, description: str, old: str, new: str):
    """Regex-anchored (exact substring) replace. Idempotent, count-verified.

    Checks the OLD anchor's count FIRST, not the new text's presence -- a
    short/generic `new` fragment can coincidentally already exist in an
    untouched file, which would produce a false "already applied" skip if
    checked first. Old-anchor-absent is the trustworthy signal for
    "already applied", trusted only once the new text's presence is also
    confirmed; aborts loudly if neither is true (file has diverged from
    what this script expects).
    """
    global edits_applied, edits_skipped
    path = ROOT / rel_path
    if not path.exists():
        print(f"    !! ABORT: {rel_path} does not exist")
        sys.exit(1)
    text = path.read_text(encoding="utf-8")

    count = text.count(old)
    if count == 1:
        backup(path)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
        print(f"    OK: {description}")
        edits_applied += 1
        return

    if count == 0:
        if (not new.strip()) or new in text:
            print(f"    (already applied) {description}")
            edits_skipped += 1
            return
        print(f"    !! ABORT: anchor not found in {rel_path}, and replacement text isn't there either")
        print(f"       description: {description}")
        print("       the file may have diverged from what this script expects -- not guessing, stopping here")
        sys.exit(1)

    print(f"    !! ABORT: expected exactly 1 match for anchor in {rel_path}")
    print(f"       description: {description}")
    print(f"       found: {count} match(es) (ambiguous, refusing to guess which one)")
    sys.exit(1)


def create_file(rel_path: str, description: str, content: str):
    global edits_applied, edits_skipped
    path = ROOT / rel_path
    if path.exists() and path.read_text(encoding="utf-8") == content:
        print(f"    (already applied) {description}")
        edits_skipped += 1
        return
    if path.exists():
        backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"    OK: {description}")
    edits_applied += 1


COMMIT_MESSAGE = """Sprint 2 part 1: edge-to-edge/predictive back, trust screen, Huawei pending-approval status, CSV export

See CHANGELOG.md for the full breakdown.
"""

log("Step 1/9: feature (b) -- edge-to-edge + predictive back")
apply_edit(
    "app/src/main/java/com/openhealth/sync/MainActivity.kt",
    "import enableEdgeToEdge",
    old='''import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.health.connect.client.PermissionController''',
    new='''import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.health.connect.client.PermissionController''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/MainActivity.kt",
    "call enableEdgeToEdge() before setContent in onCreate()",
    old='''    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setupPeriodicSync()

        setContent {''',
    new='''    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Sprint (2026-07-14): targetSdk 35 already forces edge-to-edge on
        // real Android 15+ devices with or without this call (that's the
        // whole point of the platform enforcement) -- what enableEdgeToEdge()
        // actually buys us is (a) the same look on Android 8-14 devices,
        // which would otherwise render with old-style opaque system bars,
        // and (b) correct light/dark status- and navigation-bar icon
        // contrast that auto-follows system dark mode, matching how
        // isDark is computed in FinalBitLutShell (isSystemInDarkTheme()) --
        // no manual SystemBarStyle wiring needed since both use the same
        // system signal. The root Scaffold in FinalBitLutShell already
        // applies M3's default contentWindowInsets, and the bottom nav bar
        // already calls navigationBarsPadding() itself, so no other insets
        // work was needed for this.
        enableEdgeToEdge()

        setupPeriodicSync()

        setContent {''',
)
apply_edit(
    "app/src/main/AndroidManifest.xml",
    "enable predictive back gesture (android:enableOnBackInvokedCallback)",
    old='''        android:label="BitLut"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/Theme.BitLut">

        <meta-data android:name="com.huawei.hms.client.appid" android:value="appid=${huaweiAppId}" />''',
    new='''        android:label="BitLut"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:enableOnBackInvokedCallback="true"
        android:theme="@style/Theme.BitLut">

        <meta-data android:name="com.huawei.hms.client.appid" android:value="appid=${huaweiAppId}" />''',
)
log("Step 2/9: feature (d) -- Huawei pending-approval status card")
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/SyncViewModel.kt",
    "add isHuaweiPendingApproval to SyncUiState",
    old='''    val hasGooglePermissions: Boolean = false,
    val needsPermissionRefresh: Boolean = false,
    val isHuaweiAuthorized: Boolean = false,
    val isSyncing: Boolean = false,
    val syncStatus: String = "sync_status_idle",
    val lastSyncTime: String = "sync_no_data"''',
    new='''    val hasGooglePermissions: Boolean = false,
    val needsPermissionRefresh: Boolean = false,
    val isHuaweiAuthorized: Boolean = false,
    val isHuaweiPendingApproval: Boolean = false,
    val isSyncing: Boolean = false,
    val syncStatus: String = "sync_status_idle",
    val lastSyncTime: String = "sync_no_data"''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/SyncViewModel.kt",
    "populate isHuaweiPendingApproval in refreshStatuses()",
    old='''                    hasGooglePermissions = hasPerms,
                    needsPermissionRefresh = isAvailable && !hasPerms,
                    isHuaweiAuthorized = huaweiHealthManager.isAuthorized(),
                    lastSyncTime = savedTime
                )
            }''',
    new='''                    hasGooglePermissions = hasPerms,
                    needsPermissionRefresh = isAvailable && !hasPerms,
                    isHuaweiAuthorized = huaweiHealthManager.isAuthorized(),
                    isHuaweiPendingApproval = huaweiHealthManager.isPendingApproval(),
                    lastSyncTime = savedTime
                )
            }''',
)
log("Step 6/9: strings.xml (en) -- huawei_pending_approval_* + data_scopes_*/export_csv_link")
apply_edit(
    "app/src/main/res/values/strings.xml",
    "add huawei_pending_approval_title/body (en)",
    old='''    <string name="summary_short_title">Summary</string>
    <string name="google_health_connect">Google Health Connect</string>
    <string name="huawei_health_title">Huawei Health</string>
    <string name="manual_sync_title">Manual sync</string>
    <string name="import_archive_title">Import archive</string>
    <string name="import_archive_selected">Huawei Health archive selected</string>''',
    new='''    <string name="summary_short_title">Summary</string>
    <string name="google_health_connect">Google Health Connect</string>
    <string name="huawei_health_title">Huawei Health</string>
    <string name="huawei_pending_approval_title">Waiting for Huawei\\'s approval</string>
    <string name="huawei_pending_approval_body">This isn\\'t a bug. Huawei reviews every app\\'s data access request before it can start syncing — this can take a few days. BitLut will start working automatically the moment it\\'s approved, with nothing for you to do in the meantime.</string>
    <string name="manual_sync_title">Manual sync</string>
    <string name="import_archive_title">Import archive</string>
    <string name="import_archive_selected">Huawei Health archive selected</string>''',
)
log("Step 7/9: strings.xml (ru) -- huawei_pending_approval_* + data_scopes_*/export_csv_link")
apply_edit(
    "app/src/main/res/values-ru/strings.xml",
    "add huawei_pending_approval_title/body (ru)",
    old='''    <string name="summary_short_title">Сводка</string>
    <string name="google_health_connect">Google Health Connect</string>
    <string name="huawei_health_title">Huawei Health</string>
    <string name="manual_sync_title">Ручная синхронизация</string>
    <string name="import_archive_title">Импорт архива</string>
    <string name="import_archive_selected">Архив Huawei Health выбран</string>''',
    new='''    <string name="summary_short_title">Сводка</string>
    <string name="google_health_connect">Google Health Connect</string>
    <string name="huawei_health_title">Huawei Health</string>
    <string name="huawei_pending_approval_title">Ждём подтверждения от Huawei</string>
    <string name="huawei_pending_approval_body">Это не ошибка. Huawei проверяет запрос на доступ к данным у каждого приложения, прежде чем синхронизация сможет заработать — это может занять несколько дней. BitLut заработает автоматически, как только заявка будет одобрена, делать ничего не нужно.</string>
    <string name="manual_sync_title">Ручная синхронизация</string>
    <string name="import_archive_title">Импорт архива</string>
    <string name="import_archive_selected">Архив Huawei Health выбран</string>''',
)
log("Step 3/9: features (c)/(d)/(e) UI -- FinalBitLutShell.kt")
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "add Schedule icon import (used by the pending-approval card and trust screen)",
    old='''import androidx.compose.material.icons.rounded.DirectionsRun
import androidx.compose.material.icons.rounded.EmojiEvents
import androidx.compose.material.icons.rounded.LocalFireDepartment
import androidx.compose.material3.Icon
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.style.TextOverflow''',
    new='''import androidx.compose.material.icons.rounded.DirectionsRun
import androidx.compose.material.icons.rounded.EmojiEvents
import androidx.compose.material.icons.rounded.LocalFireDepartment
import androidx.compose.material.icons.rounded.Schedule
import androidx.compose.material3.Icon
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.style.TextOverflow''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "add onExportCsv parameter to FinalBitLutShell()",
    old='''    onRequestHuawei: () -> Unit,
    onSyncNow: () -> Unit,
    onImportArchive: () -> Unit = {},
    onWidgetVisibilityChanged: (DashboardWidget, Boolean) -> Unit = { _, _ -> },
    onStepsGoalChanged: (Long) -> Unit = {},
    onDistanceGoalChanged: (Double) -> Unit = {},''',
    new='''    onRequestHuawei: () -> Unit,
    onSyncNow: () -> Unit,
    onImportArchive: () -> Unit = {},
    onExportCsv: () -> Unit = {},
    onWidgetVisibilityChanged: (DashboardWidget, Boolean) -> Unit = { _, _ -> },
    onStepsGoalChanged: (Long) -> Unit = {},
    onDistanceGoalChanged: (Double) -> Unit = {},''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "wire onExportCsv through the SettingsScreen call site",
    old='''                MainTab.Today -> SummaryScreen(palette, dashboardState, onRefresh, wrappedOnRequestGoogle)
                MainTab.Settings -> SettingsScreen(palette, syncState, dashboardState, onRefresh, wrappedOnRequestGoogle, onRequestHuawei, onSyncNow,
                    onImportArchive = { showArchiveImport = true },
                    onWidgetVisibilityChanged = onWidgetVisibilityChanged,
                    onStepsGoalChanged = onStepsGoalChanged,
                    onDistanceGoalChanged = onDistanceGoalChanged,''',
    new='''                MainTab.Today -> SummaryScreen(palette, dashboardState, onRefresh, wrappedOnRequestGoogle)
                MainTab.Settings -> SettingsScreen(palette, syncState, dashboardState, onRefresh, wrappedOnRequestGoogle, onRequestHuawei, onSyncNow,
                    onImportArchive = { showArchiveImport = true },
                    onExportCsv = onExportCsv,
                    onWidgetVisibilityChanged = onWidgetVisibilityChanged,
                    onStepsGoalChanged = onStepsGoalChanged,
                    onDistanceGoalChanged = onDistanceGoalChanged,''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "add DataScopesScreen composable (trust screen listing the real 5 Huawei scopes)",
    old='''@Composable
private fun OnboardingScopeRow(palette: BitPalette, icon: ImageVector, text: String) {
    Row(
        modifier = Modifier.padding(vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = null, tint = HealthAccent.activity, modifier = Modifier.size(16.dp))
        Spacer(Modifier.width(10.dp))
        Text(text, color = palette.text, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
    }
}

@Composable
private fun SummaryScreen(''',
    new='''@Composable
private fun OnboardingScopeRow(palette: BitPalette, icon: ImageVector, text: String) {
    Row(
        modifier = Modifier.padding(vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = null, tint = HealthAccent.activity, modifier = Modifier.size(16.dp))
        Spacer(Modifier.width(10.dp))
        Text(text, color = palette.text, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
    }
}

/**
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
                    tint = HealthAccent.mind,
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
                accent = HealthAccent.mind,
                onClick = onClose
            )
        }
    }
}

@Composable
private fun SummaryScreen(''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "SettingsScreen: add onExportCsv param, wrap body in Box + local showDataScopes state",
    old='''    onRequestHuawei: () -> Unit,
    onSyncNow: () -> Unit,
    onImportArchive: () -> Unit,
    onWidgetVisibilityChanged: (DashboardWidget, Boolean) -> Unit,
    onStepsGoalChanged: (Long) -> Unit,
    onDistanceGoalChanged: (Double) -> Unit,
    onActiveMinutesGoalChanged: (Int) -> Unit,
    onCaloriesGoalChanged: (Double) -> Unit
) {
    // Sprint (2026-07-08): Daily goals moved to the top (right under the
    // header), calories dropped from it. The three connection cards below
    // lost their explanatory body text and status line (title + icon only
    // now) and their two actions are a single compact row instead of a
    // wrapping FlowRow. The widget-visibility toggle section was removed
    // entirely -- Summary's widget set is fixed now, not user-configurable.
    Column(
        modifier = Modifier
            .fillMaxSize()''',
    new='''    onRequestHuawei: () -> Unit,
    onSyncNow: () -> Unit,
    onImportArchive: () -> Unit,
    onExportCsv: () -> Unit,
    onWidgetVisibilityChanged: (DashboardWidget, Boolean) -> Unit,
    onStepsGoalChanged: (Long) -> Unit,
    onDistanceGoalChanged: (Double) -> Unit,
    onActiveMinutesGoalChanged: (Int) -> Unit,
    onCaloriesGoalChanged: (Double) -> Unit
) {
    var showDataScopes by androidx.compose.runtime.remember { androidx.compose.runtime.mutableStateOf(false) }

    // Sprint (2026-07-08): Daily goals moved to the top (right under the
    // header), calories dropped from it. The three connection cards below
    // lost their explanatory body text and status line (title + icon only
    // now) and their two actions are a single compact row instead of a
    // wrapping FlowRow. The widget-visibility toggle section was removed
    // entirely -- Summary's widget set is fixed now, not user-configurable.
    Box(modifier = Modifier.fillMaxSize()) {
    Column(
        modifier = Modifier
            .fillMaxSize()''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "SettingsScreen: insert HuaweiPendingApprovalCard conditionally after the Huawei connection card",
    old='''            onSecondaryAction = onRefresh
        )

        SettingsConnectionCard(
            palette = palette,
            title = stringResource(R.string.manual_sync_title),''',
    new='''            onSecondaryAction = onRefresh
        )

        // Sprint (2026-07-14): a calm, specific explanation instead of a
        // silent no-op degrade. Huawei's server-side scope review can take
        // days; without this, a new install just sees zero data flowing
        // with no indication of why, which reads as "broken" rather than
        // "waiting." Only shown while genuinely pending (confirmed via a
        // real 50005 response, not guessed) and not yet authorized.
        if (syncState.isHuaweiPendingApproval && !syncState.isHuaweiAuthorized) {
            HuaweiPendingApprovalCard(palette = palette)
        }

        SettingsConnectionCard(
            palette = palette,
            title = stringResource(R.string.manual_sync_title),''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "SettingsScreen: add data-scopes/export-csv trigger links, close Box with conditional DataScopesScreen overlay, add HuaweiPendingApprovalCard composable",
    old='''            secondaryAction = stringResource(R.string.import_archive_title),
            onSecondaryAction = onImportArchive
        )
    }
}
''',
    new='''            secondaryAction = stringResource(R.string.import_archive_title),
            onSecondaryAction = onImportArchive
        )

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
}

/**
 * Explains the 50005 / "scope not authorized" wait state in plain language
 * instead of leaving a new install to wonder why no Huawei data is showing
 * up. This is a review-queue wait, not a permission the person needs to
 * grant again -- re-tapping Connect won't skip the queue, so this card
 * intentionally has no primary action, only the explanation.
 */
@Composable
private fun HuaweiPendingApprovalCard(palette: BitPalette) {
    SoftCard(palette = palette, accent = HealthAccent.activity, hero = false, tintWithAccent = true) {
        Row(verticalAlignment = Alignment.Top) {
            Icon(
                Icons.Rounded.Schedule,
                contentDescription = null,
                tint = HealthAccent.activity,
                modifier = Modifier.size(20.dp)
            )
            Spacer(Modifier.width(10.dp))
            Column {
                Text(
                    text = stringResource(R.string.huawei_pending_approval_title),
                    color = palette.text,
                    fontWeight = FontWeight.ExtraBold,
                    fontSize = 15.sp
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    text = stringResource(R.string.huawei_pending_approval_body),
                    color = palette.secondaryText,
                    fontWeight = FontWeight.Medium,
                    fontSize = 13.sp,
                    lineHeight = 18.sp
                )
            }
        }
    }
}
''',
)
log("Step 4/9: feature (e) -- readDailyTotals() in GoogleHealthManager.kt")
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt",
    "add DailyTotal data class next to ActivitySessionData",
    old='''    val exerciseType: Int = ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT
)

data class GoogleDashboardSnapshot(
    val stepsToday: Long,
    val distanceMeters: Double,''',
    new='''    val exerciseType: Int = ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT
)

/** One row of the CSV export (sprint 2026-07-14): a single calendar day's
 *  activity totals, read the same raw-records-and-sum way as "today" on the
 *  dashboard (see the comment on readDashboardSnapshot for why -- aggregate()
 *  is not used here either, for the same staleness reason). */
data class DailyTotal(
    val date: LocalDate,
    val steps: Long,
    val distanceMeters: Double,
    val caloriesKcal: Double
)

data class GoogleDashboardSnapshot(
    val stepsToday: Long,
    val distanceMeters: Double,''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt",
    "add readDailyTotals() after readRecentWorkouts()",
    old='''        }
    }

    suspend fun readWorkoutMinutesToday(): Long {
        val client = resolveClient() ?: return 0L
        return try {''',
    new='''        }
    }

    /**
     * Feeds the CSV export (sprint 2026-07-14). One row per calendar day,
     * oldest first, for the last [daysBack] days including today. Reads
     * plain per-day records and sums in-app -- exactly the readDashboardSnapshot
     * pattern, not aggregate() -- so an export taken right after a sync
     * shows the same numbers as the dashboard, not a stale cached total.
     *
     * Sequential (not parallel) by design: this only runs on an explicit,
     * infrequent user tap, so the ~3x daysBack Health Connect calls it makes
     * are not a rate-limit concern the way a call inside load() would be
     * (see CLAUDE.md Gotcha 4) -- correctness and simplicity here matter
     * more than shaving a second off a manual export.
     */
    suspend fun readDailyTotals(daysBack: Int = 30): List<DailyTotal> {
        val client = resolveClient() ?: return emptyList()
        val today = LocalDate.now()
        val zone = ZoneId.systemDefault()
        val out = ArrayList<DailyTotal>(daysBack)

        for (offset in (daysBack - 1) downTo 0) {
            val day = today.minusDays(offset.toLong())
            val dayStart = day.atStartOfDay(zone).toInstant()
            val dayEnd = day.plusDays(1).atStartOfDay(zone).toInstant()
            val range = TimeRangeFilter.between(dayStart, dayEnd)

            try {
                val steps = client.readRecords(
                    ReadRecordsRequest(recordType = StepsRecord::class, timeRangeFilter = range)
                ).records.sumOf { it.count }
                val distance = client.readRecords(
                    ReadRecordsRequest(recordType = DistanceRecord::class, timeRangeFilter = range)
                ).records.sumOf { it.distance.inMeters }
                val calories = client.readRecords(
                    ReadRecordsRequest(recordType = ActiveCaloriesBurnedRecord::class, timeRangeFilter = range)
                ).records.sumOf { it.energy.inKilocalories }
                out.add(DailyTotal(day, steps, distance, calories))
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                AppLogger.e(TAG, "readDailyTotals failed for $day: ${e.message}", e)
                out.add(DailyTotal(day, 0L, 0.0, 0.0))
            }
        }

        return out
    }

    suspend fun readWorkoutMinutesToday(): Long {
        val client = resolveClient() ?: return 0L
        return try {''',
)
log("Step 5/9: feature (e) -- wire CSV export in MainActivity.kt")
apply_edit(
    "app/src/main/java/com/openhealth/sync/MainActivity.kt",
    "wire onExportCsv callback into the FinalBitLutShell() call",
    old='''                    onRequestHuawei = { startHuaweiAuthorization() },
                    onSyncNow = { triggerImmediateSync() },
                    onImportArchive = { openHuaweiArchiveImport() },
                    onWidgetVisibilityChanged = { widget, visible ->
                        dashboardViewModel.setWidgetVisible(widget, visible)
                    },''',
    new='''                    onRequestHuawei = { startHuaweiAuthorization() },
                    onSyncNow = { triggerImmediateSync() },
                    onImportArchive = { openHuaweiArchiveImport() },
                    onExportCsv = { exportCsv() },
                    onWidgetVisibilityChanged = { widget, visible ->
                        dashboardViewModel.setWidgetVisible(widget, visible)
                    },''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/MainActivity.kt",
    "add exportCsv() private function",
    old='''            archiveImportLauncher.launch(intent)
        } catch (t: Throwable) {
            AppLogger.e("MainActivity", "Archive picker failed: ${t.message}", t)
            Toast.makeText(this, getString(R.string.status_error), Toast.LENGTH_LONG).show()
        }
    }

    private fun setupPeriodicSync() {''',
    new='''            archiveImportLauncher.launch(intent)
        } catch (t: Throwable) {
            AppLogger.e("MainActivity", "Archive picker failed: ${t.message}", t)
            Toast.makeText(this, getString(R.string.status_error), Toast.LENGTH_LONG).show()
        }
    }

    /**
     * Sprint (2026-07-14): exports exactly what BitLut already reads for its
     * own dashboard (daily steps/distance/calories + recent workouts) as a
     * CSV via the system share sheet. Read work happens off the main thread
     * in lifecycleScope, same as every other Health Connect read in this
     * class; CsvExporter.writeAndShare does its own file I/O synchronously
     * but is only ever called here, already off the main thread.
     */
    private fun exportCsv() {
        lifecycleScope.launch {
            val app = application as SyncApplication
            // readDailyTotals()/readRecentWorkouts() are plain GoogleHealthManager
            // functions, not part of the HealthConnectManager interface that
            // AppContainer.googleHealthManager is declared as (same reason
            // SyncWorker only ever calls the interface's readDashboardSnapshot()).
            // AppContainer always constructs a real GoogleHealthManager, so this
            // cast is safe in practice; the null-check is defensive only.
            val googleManager = app.container.googleHealthManager as? com.openhealth.sync.data.GoogleHealthManager
            if (googleManager == null) {
                Toast.makeText(this@MainActivity, getString(R.string.status_error), Toast.LENGTH_LONG).show()
                return@launch
            }
            val dailyTotals = googleManager.readDailyTotals(30)
            val workouts = googleManager.readRecentWorkouts(100)
            com.openhealth.sync.util.CsvExporter.writeAndShare(this@MainActivity, dailyTotals, workouts)
        }
    }

    private fun setupPeriodicSync() {''',
)
log("Step 8/9: strings.xml (en+ru) -- data_scopes_* (trust screen) + export_csv_link")
apply_edit(
    "app/src/main/res/values/strings.xml",
    "add data_scopes_*/export_csv_link strings (en)",
    old='''    <string name="onboarding_privacy_note">BitLut never reads or shares sleep, heart rate, or any other health data. Only activity metrics move from Huawei Health into Google Health Connect, and stay on your device.</string>
    <string name="onboarding_continue_button">Continue</string>''',
    new='''    <string name="onboarding_privacy_note">BitLut never reads or shares sleep, heart rate, or any other health data. Only activity metrics move from Huawei Health into Google Health Connect, and stay on your device.</string>
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
    <string name="onboarding_continue_button">Continue</string>''',
)
apply_edit(
    "app/src/main/res/values-ru/strings.xml",
    "add data_scopes_*/export_csv_link strings (ru)",
    old='''    <string name="onboarding_privacy_note">BitLut никогда не читает и не передаёт данные о сне, пульсе или другие показатели здоровья. Из Huawei Health в Google Health Connect передаются только данные активности, и они остаются на вашем устройстве.</string>
    <string name="onboarding_continue_button">Продолжить</string>''',
    new='''    <string name="onboarding_privacy_note">BitLut никогда не читает и не передаёт данные о сне, пульсе или другие показатели здоровья. Из Huawei Health в Google Health Connect передаются только данные активности, и они остаются на вашем устройстве.</string>
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
    <string name="onboarding_continue_button">Продолжить</string>''',
)
log("Step 9/9: AndroidManifest.xml -- register FileProvider for CSV export")
apply_edit(
    "app/src/main/AndroidManifest.xml",
    "add FileProvider provider entry for CSV export",
    old='''        </activity-alias>
</application>''',
    new='''        </activity-alias>

        <!-- Sprint (2026-07-14): backs the CSV export feature. Lets BitLut
             hand a cache-dir CSV file to the share sheet without exposing a
             raw file:// path (blocked by FileProvider/StrictMode on modern
             Android). No new dependency: FileProvider ships in androidx.core,
             already a transitive dependency via androidx.core:core-ktx. -->
        <provider
            android:name="androidx.core.content.FileProvider"
            android:authorities="${applicationId}.fileprovider"
            android:exported="false"
            android:grantUriPermissions="true">
            <meta-data
                android:name="android.support.FILE_PROVIDER_PATHS"
                android:resource="@xml/file_paths" />
        </provider>
</application>''',
)
log("Step 10/9(!)/final: create new files for CSV export")
create_file(
    "app/src/main/res/xml/file_paths.xml",
    "create file_paths.xml (FileProvider path spec for CSV export)",
    '''<?xml version="1.0" encoding="utf-8"?>
<!--
  Sprint (2026-07-14): backs the CSV export feature. Exported files live in
  the app's cache dir (export/) rather than files dir: they're disposable,
  regenerated-on-demand copies of data that already lives permanently in
  Health Connect, not something BitLut itself needs to keep around.
-->
<paths xmlns:android="http://schemas.android.com/apk/res/android">
    <cache-path name="export" path="export/" />
</paths>
''',
)
create_file(
    "app/src/main/java/com/openhealth/sync/util/CsvExporter.kt",
    "create CsvExporter.kt",
    '''package com.openhealth.sync.util

import android.content.Context
import android.content.Intent
import androidx.core.content.FileProvider
import com.openhealth.sync.data.ActivitySessionData
import com.openhealth.sync.data.DailyTotal
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * CSV export (sprint 2026-07-14). Exports exactly what BitLut already reads
 * from Health Connect for its own dashboard -- daily steps/distance/calories
 * totals plus recent workouts -- as a plain CSV file, then opens the system
 * share sheet so the person can save it wherever they like (Drive, email,
 * a file manager, another app). No BitLut server involved at any point;
 * the file is written straight to this device's cache dir and handed off
 * via FileProvider.
 *
 * This is deliberately not a general Health Connect data browser: it only
 * ever exports the same activity-only fields BitLut syncs in the first
 * place (see CLAUDE.md on the sleep/HR/SpO2/stress platform-tier limit --
 * none of that exists to export either).
 */
object CsvExporter {

    private const val TAG = "CsvExporter"

    fun writeAndShare(context: Context, dailyTotals: List<DailyTotal>, workouts: List<ActivitySessionData>) {
        try {
            val exportDir = File(context.cacheDir, "export").apply { mkdirs() }
            val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
            val file = File(exportDir, "bitlut_export_$timestamp.csv")

            file.bufferedWriter().use { writer ->
                writer.appendLine("# BitLut export -- generated ${Date()}")
                writer.appendLine("# Daily totals: ${dailyTotals.size} day(s)")
                writer.appendLine()
                writer.appendLine("date,steps,distance_meters,calories_kcal")
                dailyTotals.sortedBy { it.date }.forEach { day ->
                    writer.appendLine(
                        "${day.date},${day.steps}," +
                            "${"%.1f".format(Locale.US, day.distanceMeters)}," +
                            "${"%.1f".format(Locale.US, day.caloriesKcal)}"
                    )
                }
                writer.appendLine()
                writer.appendLine("workout_title,start,end,duration_minutes")
                val dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US)
                workouts.sortedByDescending { it.startTimeMs }.forEach { w ->
                    val durationMinutes = (w.endTimeMs - w.startTimeMs) / 60000L
                    val safeTitle = w.title.replace(",", ";").replace("\\n", " ")
                    writer.appendLine(
                        "$safeTitle,${dateFormat.format(Date(w.startTimeMs))}," +
                            "${dateFormat.format(Date(w.endTimeMs))},$durationMinutes"
                    )
                }
            }

            val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
            val shareIntent = Intent(Intent.ACTION_SEND).apply {
                type = "text/csv"
                putExtra(Intent.EXTRA_STREAM, uri)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            val chooser = Intent.createChooser(shareIntent, "BitLut export").apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(chooser)
        } catch (e: Exception) {
            AppLogger.e(TAG, "CSV export failed: ${e.message}", e)
        }
    }
}
''',
)

# ---------------------------------------------------------------------------
log(f"Done: {edits_applied} edit(s) applied, {edits_skipped} already up to date")

if edits_applied == 0:
    log("Nothing to do -- repo already matches the target state. Exiting without touching git.")
    sys.exit(0)

log(f"Backups written to {BACKUP_DIR.relative_to(ROOT)}")

gradlew = ROOT / "gradlew"
build_ok = None
if gradlew.exists():
    log("Running best-effort Gradle compile gate (compileDebugKotlin + processDebugResources)...")
    try:
        result = subprocess.run(
            ["./gradlew", "--console=plain", ":app:compileDebugKotlin", ":app:processDebugResources"],
            cwd=ROOT,
        )
        build_ok = result.returncode == 0
    except OSError as e:
        log(f"Could not run ./gradlew ({e}) -- skipping the compile gate.")
        build_ok = None

    if build_ok is False:
        log("Gradle check FAILED. Working tree is left patched (see backups above to revert if needed).")
        log("Not committing or pushing. Fix the reported error and re-run this script -- it is idempotent.")
        sys.exit(1)
    elif build_ok is True:
        log("Gradle check passed.")
else:
    log("No ./gradlew found in this directory -- skipping the compile gate (expected in a sandbox/test run).")

log("Committing and pushing...")
subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
commit = subprocess.run(
    ["git", "commit", "-m", COMMIT_MESSAGE],
    cwd=ROOT,
)
if commit.returncode != 0:
    log("git commit reported nothing to commit or failed -- check git status manually.")
    sys.exit(1)

push = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT)
if push.returncode != 0:
    log("git push failed -- the commit is local; push manually once resolved (e.g. auth/network).")
    sys.exit(1)

log("Pushed to origin/main. Done.")
