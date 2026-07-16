package com.openhealth.sync.util

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
                    val safeTitle = w.title.replace(",", ";").replace("\n", " ")
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
