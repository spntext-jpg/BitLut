package com.openhealth.sync.ui.theme

import android.content.Context
import android.content.SharedPreferences
import androidx.compose.runtime.*

enum class ThemeMode { SYSTEM, LIGHT, DARK }
private const val KEY_MODE = "mode"
private fun themePrefs(context: Context): SharedPreferences =
    context.applicationContext.getSharedPreferences("bitlut_appearance", Context.MODE_PRIVATE)
private fun readTheme(prefs: SharedPreferences): ThemeMode =
    ThemeMode.entries.firstOrNull { it.name == prefs.getString(KEY_MODE, null) } ?: ThemeMode.SYSTEM

fun setThemeMode(context: Context, mode: ThemeMode) {
    themePrefs(context).edit().putString(KEY_MODE, mode.name).apply()
}

@Composable
fun rememberThemeMode(context: Context): ThemeMode {
    val prefs = remember(context.applicationContext) { themePrefs(context) }
    var mode by remember(prefs) { mutableStateOf(readTheme(prefs)) }
    DisposableEffect(prefs) {
        val listener = SharedPreferences.OnSharedPreferenceChangeListener { _, key ->
            if (key == KEY_MODE) mode = readTheme(prefs)
        }
        prefs.registerOnSharedPreferenceChangeListener(listener)
        mode = readTheme(prefs)
        onDispose { prefs.unregisterOnSharedPreferenceChangeListener(listener) }
    }
    return mode
}
