package com.openhealth.sync.widget

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
