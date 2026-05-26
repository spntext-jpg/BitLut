package com.openhealth.sync.data

import android.content.Context
import android.content.SharedPreferences

class PreferencesManager(context: Context) {
    private val prefs: SharedPreferences = context.getSharedPreferences("bitlut_prefs", Context.MODE_PRIVATE)

    companion object {
        const val KEY_GOOGLE_CONNECTED = "google_connected"
        const val KEY_HUAWEI_CONNECTED = "huawei_connected"
        const val KEY_HUAWEI_PENDING_APPROVAL = "huawei_pending_approval"
    }

    var isGoogleConnected: Boolean
        get() = prefs.getBoolean(KEY_GOOGLE_CONNECTED, false)
        set(value) = prefs.edit().putBoolean(KEY_GOOGLE_CONNECTED, value).apply()

    var isHuaweiConnected: Boolean
        get() = prefs.getBoolean(KEY_HUAWEI_CONNECTED, false)
        set(value) = prefs.edit().putBoolean(KEY_HUAWEI_CONNECTED, value).apply()

    var isHuaweiPendingApproval: Boolean
        get() = prefs.getBoolean(KEY_HUAWEI_PENDING_APPROVAL, false)
        set(value) = prefs.edit().putBoolean(KEY_HUAWEI_PENDING_APPROVAL, value).apply()
}
