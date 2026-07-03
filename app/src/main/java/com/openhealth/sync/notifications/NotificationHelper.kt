package com.openhealth.sync.notifications

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import com.openhealth.sync.MainActivity
import com.openhealth.sync.R
import com.openhealth.sync.util.AppLogger

private const val TAG = "NotificationHelper"

/**
 * Centralized notification channel + posting logic (v1.9.12, sprint 4).
 *
 * BitLut has no notification infrastructure before this sprint. Everything
 * here is activity-only in content (goal progress, streaks, personal
 * records) -- no sleep/heart-rate/stress content, matching the same
 * boundary enforced everywhere else in the app.
 *
 * All posting methods silently no-op if POST_NOTIFICATIONS is not granted
 * (Android 13+/API 33+) rather than crashing -- notifications are a nice-to-
 * have layer on top of a working sync, never something that can break the
 * core data pipeline if permission is denied or not yet requested.
 */
object NotificationHelper {
    const val CHANNEL_ID_ACTIVITY = "bitlut_activity_channel"
    private const val NOTIFICATION_ID_EVENING_REMINDER = 1001
    private const val NOTIFICATION_ID_NEW_RECORD = 1002
    private const val NOTIFICATION_ID_STREAK = 1003

    fun ensureChannel(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return

        val manager = context.getSystemService(NotificationManager::class.java) ?: return
        if (manager.getNotificationChannel(CHANNEL_ID_ACTIVITY) != null) return

        val channel = NotificationChannel(
            CHANNEL_ID_ACTIVITY,
            context.getString(R.string.notification_channel_activity_name),
            NotificationManager.IMPORTANCE_DEFAULT
        ).apply {
            description = context.getString(R.string.notification_channel_activity_description)
        }
        manager.createNotificationChannel(channel)
    }

    private fun hasPermission(context: Context): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return true
        return ActivityCompat.checkSelfPermission(
            context,
            Manifest.permission.POST_NOTIFICATIONS
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun openAppIntent(context: Context): PendingIntent {
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val flags = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        return PendingIntent.getActivity(context, 0, intent, flags)
    }

    fun postEveningReminder(context: Context, title: String, body: String) {
        post(context, NOTIFICATION_ID_EVENING_REMINDER, title, body)
    }

    fun postNewRecord(context: Context, title: String, body: String) {
        post(context, NOTIFICATION_ID_NEW_RECORD, title, body)
    }

    fun postStreakMilestone(context: Context, title: String, body: String) {
        post(context, NOTIFICATION_ID_STREAK, title, body)
    }

    private fun post(context: Context, notificationId: Int, title: String, body: String) {
        if (!hasPermission(context)) {
            AppLogger.d(TAG, "Skipping notification (POST_NOTIFICATIONS not granted): $title")
            return
        }

        try {
            ensureChannel(context)

            val notification = NotificationCompat.Builder(context, CHANNEL_ID_ACTIVITY)
                .setSmallIcon(R.drawable.ic_notification)
                .setContentTitle(title)
                .setContentText(body)
                .setStyle(NotificationCompat.BigTextStyle().bigText(body))
                .setContentIntent(openAppIntent(context))
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .build()

            androidx.core.app.NotificationManagerCompat.from(context).notify(notificationId, notification)
        } catch (e: SecurityException) {
            // Defensive: permission can theoretically be revoked between the
            // hasPermission() check above and this call (e.g. user revokes it
            // from system settings mid-call). Never let a notification failure
            // propagate into worker failure/retry logic.
            AppLogger.e(TAG, "Notification post denied: ${e.message}", e)
        } catch (e: Exception) {
            AppLogger.e(TAG, "Notification post failed: ${e.message}", e)
        }
    }
}
