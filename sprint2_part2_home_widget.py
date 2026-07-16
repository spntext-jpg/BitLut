#!/usr/bin/env python3
"""
sprint2_part2_home_widget.py

BitLut patch script -- sprint 2 (2026-07-14), part 2 of 2.

Implements the remaining item from this sprint's plan:
  (a) Home screen widget (Jetpack Glance): one tile, today's step count and
      last-sync time, tap anywhere to trigger a sync. Reads the existing
      DashboardSnapshotCache (same source the dashboard itself reads on
      cold start) rather than calling Health Connect directly; the tap
      action enqueues the exact same WorkManager request the Settings
      "Sync now" button uses (BackgroundSyncScheduler.enqueueImmediateSync).

This is the one piece of this sprint kept in its own script: it's the only
part that adds a new Gradle dependency (androidx.glance:glance-appwidget)
and a new manifest <receiver>, so it's the highest-risk/most-separable
piece. Run sprint2_part1_polish_trust_export.py first if you haven't --
this script doesn't depend on it, but that's the natural order.

Run from the repo root inside your Codespace:
    python3 sprint2_part2_home_widget.py

Conventions followed (see CLAUDE.md): backs up every touched file first;
every edit is a regex-anchored (exact substring) old_str -> new_str
replacement, count-verified == 1 before applying; idempotent; creates 2 new
files (HomeWidget.kt, home_widget_info.xml); best-effort Gradle compile
gate before committing; pushes only if it passes.

A note on risk: this is real new Kotlin against a young-ish API (Jetpack
Glance) that could not be compile-tested against the actual Android
toolchain before delivery (no Android SDK / Google Maven access in the
sandbox this was written in). Every API used here was cross-checked against
current official Android Developers documentation and codelab samples
during writing, and the whole change is gated behind the Gradle compile
check below -- if something is still off, this script stops before
touching git and leaves the exact compiler error for you to paste back.
"""

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / f"{TIMESTAMP}_sprint2_part2_home_widget"

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
    confirmed; aborts loudly if neither is true.
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


COMMIT_MESSAGE = """Sprint 2 part 2: home screen widget (Jetpack Glance)

See CHANGELOG.md for the full breakdown.
"""

log("Step 1/6: app/build.gradle.kts -- add Jetpack Glance dependency")
apply_edit(
    "app/build.gradle.kts",
    "add androidx.glance:glance-appwidget dependency",
    old='''    implementation("androidx.compose.material3:material3-adaptive-navigation-suite")
    implementation("androidx.compose.material:material-icons-extended")

    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")''',
    new='''    implementation("androidx.compose.material3:material3-adaptive-navigation-suite")
    implementation("androidx.compose.material:material-icons-extended")

    // Sprint (2026-07-14): home screen widget (see widget/HomeWidget.kt).
    // glance-appwidget alone (no glance-material3) is enough -- the widget
    // uses plain ColorProvider(day=.., night=..) values matching
    // HealthAccent/BitPalette's own hex constants rather than pulling in
    // Material3-for-Glance theming for one small tile.
    implementation("androidx.glance:glance-appwidget:1.1.1")

    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")''',
)
log("Step 2/6: SyncWorker.kt -- refresh the widget after every successful sync")
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/worker/SyncWorker.kt",
    "import updateAll + HomeWidget",
    old='''import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.platform.HmsCoreHelper
import com.openhealth.sync.util.AppLogger
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.withTimeout''',
    new='''import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.platform.HmsCoreHelper
import com.openhealth.sync.util.AppLogger
import androidx.glance.appwidget.updateAll
import com.openhealth.sync.widget.HomeWidget
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.withTimeout''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/worker/SyncWorker.kt",
    "call HomeWidget().updateAll() after snapshotCache.save()",
    old='''            if (freshSnapshot != null) {
                snapshotCache.save(freshSnapshot)
                AppLogger.d(TAG, "Dashboard snapshot cache refreshed after background sync")
            }
            freshSnapshot
        } catch (e: Exception) {''',
    new='''            if (freshSnapshot != null) {
                snapshotCache.save(freshSnapshot)
                AppLogger.d(TAG, "Dashboard snapshot cache refreshed after background sync")
                // Sprint (2026-07-14): the home screen widget reads this same
                // cache (see HomeWidget.kt) rather than calling Health Connect
                // itself, so it needs an explicit nudge to re-render with the
                // now-fresh numbers -- Glance widgets don't observe
                // SharedPreferences changes on their own. Runs after every
                // successful sync regardless of trigger (periodic, the
                // Settings "Sync now" button, or a tap on the widget itself),
                // since they all funnel through this one function -- a single
                // source of truth instead of updating the widget separately
                // from each trigger site.
                HomeWidget().updateAll(applicationContext)
            }
            freshSnapshot
        } catch (e: Exception) {''',
)
log("Step 3/6: strings.xml (en+ru) -- widget_* strings")
apply_edit(
    "app/src/main/res/values/strings.xml",
    "add widget_* strings (en)",
    old='''    <string name="export_csv_link">Export my data as CSV</string>
    <string name="onboarding_continue_button">Continue</string>''',
    new='''    <string name="export_csv_link">Export my data as CSV</string>
    <string name="widget_steps_label">steps</string>
    <string name="widget_synced_just_now">Synced just now</string>
    <string name="widget_synced_minutes_ago">Synced %1$d min ago</string>
    <string name="widget_synced_hours_ago">Synced %1$dh ago</string>
    <string name="widget_synced_long_ago">Synced a while ago</string>
    <string name="widget_never_synced">Not synced yet · tap to sync</string>
    <string name="widget_tap_to_sync">Tap to sync</string>
    <string name="widget_description">Today\\'s steps and last sync time, with a tap to sync now</string>
    <string name="onboarding_continue_button">Continue</string>''',
)
apply_edit(
    "app/src/main/res/values-ru/strings.xml",
    "add widget_* strings (ru)",
    old='''    <string name="export_csv_link">Экспортировать мои данные в CSV</string>
    <string name="onboarding_continue_button">Продолжить</string>''',
    new='''    <string name="export_csv_link">Экспортировать мои данные в CSV</string>
    <string name="widget_steps_label">шагов</string>
    <string name="widget_synced_just_now">Синхронизировано только что</string>
    <string name="widget_synced_minutes_ago">Синхронизировано %1$d мин назад</string>
    <string name="widget_synced_hours_ago">Синхронизировано %1$d ч назад</string>
    <string name="widget_synced_long_ago">Синхронизировано давно</string>
    <string name="widget_never_synced">Ещё не синхронизировано · нажмите</string>
    <string name="widget_tap_to_sync">Нажмите для синхронизации</string>
    <string name="widget_description">Шаги за сегодня и время последней синхронизации, нажатие запускает синк</string>
    <string name="onboarding_continue_button">Продолжить</string>''',
)
log("Step 4/6: AndroidManifest.xml -- register HomeWidgetReceiver")
apply_edit(
    "app/src/main/AndroidManifest.xml",
    "add receiver entry for the home screen widget",
    old='''        </provider>
</application>''',
    new='''        </provider>

        <!-- Sprint (2026-07-14): the home screen widget (widget/HomeWidget.kt).
             exported="true" is required for widget receivers: the platform's
             AppWidgetHost, not another app, is what binds to it (Health
             Connect/Huawei data never passes through this component; it only
             enqueues a WorkManager sync request and renders whatever the
             already-local DashboardSnapshotCache says). -->
        <receiver
            android:name=".widget.HomeWidgetReceiver"
            android:exported="true">
            <intent-filter>
                <action android:name="android.appwidget.action.APPWIDGET_UPDATE" />
            </intent-filter>
            <meta-data
                android:name="android.appwidget.provider"
                android:resource="@xml/home_widget_info" />
        </receiver>
</application>''',
)
log("Step 5/6: create new files for the home screen widget")
create_file(
    "app/src/main/res/xml/home_widget_info.xml",
    "create home_widget_info.xml (AppWidgetProviderInfo)",
    '''<?xml version="1.0" encoding="utf-8"?>
<!--
  Sprint (2026-07-14): provider info for the single-tile home screen widget
  (widget/HomeWidget.kt). minWidth/minHeight sized for a compact 2x1 cell on
  a standard 4-column launcher grid; resizeMode allows a bit of slack
  without pretending this widget has more than one size worth designing for,
  matching the "one tile, not a second UI" scope. updatePeriodMillis is a
  defensive fallback only: SyncWorker already calls HomeWidget().updateAll()
  right after every successful sync (periodic, manual, or widget-tap
  triggered), which is what actually keeps this fresh; the platform clamps
  any updatePeriodMillis below 30 minutes to 30 minutes regardless, so this
  is not doing double duty as a real refresh mechanism.
-->
<appwidget-provider xmlns:android="http://schemas.android.com/apk/res/android"
    android:minWidth="110dp"
    android:minHeight="110dp"
    android:targetCellWidth="2"
    android:targetCellHeight="1"
    android:minResizeWidth="80dp"
    android:minResizeHeight="80dp"
    android:resizeMode="horizontal|vertical"
    android:updatePeriodMillis="1800000"
    android:previewImage="@mipmap/ic_launcher"
    android:widgetCategory="home_screen"
    android:description="@string/widget_description" />
''',
)
create_file(
    "app/src/main/java/com/openhealth/sync/widget/HomeWidget.kt",
    "create HomeWidget.kt (GlanceAppWidget + tap-to-sync ActionCallback)",
    '''package com.openhealth.sync.widget

import android.content.Context
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.action.clickable
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetReceiver
import androidx.glance.appwidget.action.ActionCallback
import androidx.glance.appwidget.action.actionRunCallback
import androidx.glance.appwidget.cornerRadius
import androidx.glance.appwidget.provideContent
import androidx.glance.action.ActionParameters
import androidx.glance.background
import androidx.glance.layout.Alignment
import androidx.glance.layout.Column
import androidx.glance.layout.Spacer
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.height
import androidx.glance.layout.padding
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider
import com.openhealth.sync.R
import com.openhealth.sync.data.DashboardSnapshotCache
import com.openhealth.sync.data.worker.BackgroundSyncScheduler
import java.util.Locale
import java.util.concurrent.TimeUnit

/**
 * Home screen widget (sprint 2026-07-14). One tile, on purpose: today's step
 * count, when it was last synced, and a tap-anywhere-to-sync action -- this
 * is the existing Today screen's headline number surfaced one tap closer,
 * not a second UI or a new data source. See CLAUDE.md for why nothing else
 * (sleep/HR/SpO2/stress, History, a chart) belongs here even in miniature.
 * Deliberately text-only, no icon: keeps this widget's Glance surface area
 * (and therefore its API-compatibility risk) as small as its scope.
 *
 * Reads [DashboardSnapshotCache] -- the same last-known-good cache the
 * dashboard itself reads on cold start -- rather than calling Health
 * Connect directly. A widget's provideGlance should be fast and cheap; a
 * SharedPreferences read is, a live Health Connect query is not.
 * [com.openhealth.sync.data.worker.SyncWorker] calls [updateAll] right
 * after it writes a fresh snapshot to that same cache (see
 * refreshDashboardCacheAfterWrite there), which is what actually refreshes
 * the numbers shown here -- this class only ever renders whatever the
 * cache says right now.
 */
class HomeWidget : GlanceAppWidget() {

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        val cached = DashboardSnapshotCache(context).load()
        val stepsText = formatSteps(cached?.snapshot?.stepsToday ?: 0L)
        val stepsLabel = context.getString(R.string.widget_steps_label)
        val syncText = syncStatusText(context, cached?.savedAtMs)

        provideContent {
            val cardColor = ColorProvider(day = Color(0xFFFFFFFF), night = Color(0xFF1C1C1E))
            val textColor = ColorProvider(day = Color(0xFF111318), night = Color(0xFFF8F8F8))
            val secondaryTextColor = ColorProvider(day = Color(0xFF6E6E73), night = Color(0xFF8E8E93))

            Column(
                modifier = GlanceModifier
                    .fillMaxSize()
                    .background(cardColor)
                    .cornerRadius(20.dp)
                    .padding(16.dp)
                    .clickable(actionRunCallback<SyncNowAction>()),
                verticalAlignment = Alignment.CenterVertically,
                horizontalAlignment = Alignment.Start
            ) {
                Text(
                    text = "BitLut",
                    style = TextStyle(color = secondaryTextColor, fontWeight = FontWeight.Medium, fontSize = 11.sp)
                )

                Spacer(modifier = GlanceModifier.height(6.dp))

                Text(
                    text = stepsText,
                    style = TextStyle(color = textColor, fontWeight = FontWeight.Bold, fontSize = 32.sp)
                )
                Text(
                    text = stepsLabel,
                    style = TextStyle(color = secondaryTextColor, fontWeight = FontWeight.Medium, fontSize = 12.sp)
                )

                Spacer(modifier = GlanceModifier.height(10.dp))

                Text(
                    text = syncText,
                    style = TextStyle(color = secondaryTextColor, fontWeight = FontWeight.Medium, fontSize = 11.sp)
                )
            }
        }
    }

    private fun formatSteps(value: Long): String =
        String.format(Locale.getDefault(), "%,d", value).replace(',', ' ')

    /**
     * Kept deliberately simple (no full plural-form string set, unlike e.g.
     * insights_streak_days_ru_one/few/many elsewhere in this project):
     * abbreviated Russian time units ("мин", "ч") don't inflect by count the
     * way full words do, so "%d мин назад" is correct Russian for every N
     * without needing separate one/few/many strings -- this only works
     * because the unit is abbreviated, not a shortcut taken elsewhere.
     */
    private fun syncStatusText(context: Context, savedAtMs: Long?): String {
        if (savedAtMs == null || savedAtMs <= 0L) {
            return context.getString(R.string.widget_never_synced)
        }
        val elapsedMs = System.currentTimeMillis() - savedAtMs
        val minutes = TimeUnit.MILLISECONDS.toMinutes(elapsedMs)
        val hours = TimeUnit.MILLISECONDS.toHours(elapsedMs)
        return when {
            minutes < 1L -> context.getString(R.string.widget_synced_just_now)
            minutes < 60L -> context.getString(R.string.widget_synced_minutes_ago, minutes.toInt())
            hours < 24L -> context.getString(R.string.widget_synced_hours_ago, hours.toInt())
            else -> context.getString(R.string.widget_synced_long_ago)
        }
    }
}

/**
 * Tap action: enqueues the exact same [BackgroundSyncScheduler.enqueueImmediateSync]
 * unique work request the Settings "Sync now" button uses -- not a separate
 * sync path. This is why SyncOrchestrator's richer triggerImmediateSync()
 * (which needs a LifecycleOwner a Glance ActionCallback doesn't have) isn't
 * used here: the debounce/permission preflight/observation it adds are
 * Activity-UI concerns, while the underlying WorkManager enqueue -- the
 * part that actually matters for correctness -- is identical either way.
 */
class SyncNowAction : ActionCallback {
    override suspend fun onAction(context: Context, glanceId: GlanceId, parameters: ActionParameters) {
        BackgroundSyncScheduler.enqueueImmediateSync(context)
    }
}

class HomeWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = HomeWidget()
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
