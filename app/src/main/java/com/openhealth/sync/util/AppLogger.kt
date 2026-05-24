package com.openhealth.sync.util

import android.util.Log
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.CopyOnWriteArrayList

object AppLogger {
    private const val MAX = 500
    private val fmt = SimpleDateFormat("HH:mm:ss.SSS", Locale.getDefault())
    private val buffer = CopyOnWriteArrayList<String>()

    private fun add(level: String, tag: String, msg: String) {
        val line = "${fmt.format(Date())} $level/$tag: $msg"
        buffer.add(line)
        if (buffer.size > MAX) buffer.removeAt(0)
    }

    fun d(tag: String, msg: String) { add("D", tag, msg); Log.d(tag, msg) }
    fun i(tag: String, msg: String) { add("I", tag, msg); Log.i(tag, msg) }
    fun w(tag: String, msg: String) { add("W", tag, msg); Log.w(tag, msg) }
    fun e(tag: String, msg: String) { add("E", tag, msg); Log.e(tag, msg) }

    fun getLogs(): List<String> = buffer.toList()
    fun clear() = buffer.clear()
}
