package com.openhealth.sync.util

import android.util.Log
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object AppLogger {
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
        _logs.value = (listOf("[$time] $level/$tag: $message") + _logs.value).take(160)
    }

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
}

