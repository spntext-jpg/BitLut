package com.openhealth.sync.util
import android.content.Context
import android.os.Build
import android.util.Log
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object AppLogger {
    private const val MAX_LOG_ENTRIES = 120
    private val _logs = MutableStateFlow<List<String>>(emptyList())
    val logs = _logs.asStateFlow()

    private fun shouldShowInUi(level: String, tag: String, message: String): Boolean {
        if (level == "D") return false
        val noisy = listOf(
            "Granted permissions",
            "HC: AVAILABLE",
            "getSdkStatus()",
            "Found HC package",
            "HealthConnectClient created OK",
        )
        if (noisy.any { message.contains(it, ignoreCase = true) }) return false
        return true
    }

    private fun addLog(level: String, tag: String, message: String) {
        if (!shouldShowInUi(level, tag, message)) return
        val time = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        _logs.value = (listOf("[$time] $level/$tag: $message") + _logs.value).take(MAX_LOG_ENTRIES)
    }

    fun d(tag: String, msg: String) {
    fun d(tag: String, msg: String) {
        Log.d(tag, msg)
        addLog("D", tag, msg)
    }

    fun i(tag: String, msg: String) {
        Log.i(tag, msg)
        addLog("I", tag, msg)
    }

    fun w(tag: String, msg: String) {
        Log.w(tag, msg)
        addLog("W", tag, msg)
    }

    fun e(tag: String, msg: String, t: Throwable? = null) {
        Log.e(tag, msg, t)
        addLog("E", tag, msg + (t?.message?.let { " - $it" } ?: ""))
    }

    /**
     * Full-text export for the hidden log viewer's Copy button.
     *
     * Includes device/app metadata up front so a pasted-in log is
     * self-contained. Reads the actual installed versionName/versionCode via
     * [context.packageManager] rather than hardcoding a version string, so
     * this never goes stale as releases ship.
     *
     * Entries in [logs] are stored newest-first (see [addLog]); this export
     * reverses them to oldest-first, which reads more naturally as a
     * top-to-bottom timeline when pasted somewhere for diagnosis.
     */
    fun exportFullDump(context: Context): String {
        val versionInfo = try {
            val pInfo = context.packageManager.getPackageInfo(context.packageName, 0)
            val versionCode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                pInfo.longVersionCode
            } else {
                @Suppress("DEPRECATION")
                pInfo.versionCode.toLong()
            }
            "${pInfo.versionName} ($versionCode)"
        } catch (e: Exception) {
            "unknown"
        }

        val header = buildString {
            appendLine("BitLut diagnostic log")
            appendLine("Generated: ${SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date())}")
            appendLine("App version: $versionInfo")
            appendLine("Device: ${Build.MANUFACTURER} ${Build.MODEL}")
            appendLine("Android: ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})")
            appendLine("Entries: ${_logs.value.size}")
            appendLine("----------------------------------------")
        }

        val body = _logs.value.reversed().joinToString(separator = "\n")

        return header + body
    }
}
