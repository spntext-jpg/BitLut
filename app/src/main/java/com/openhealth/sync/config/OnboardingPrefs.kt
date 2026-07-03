package com.openhealth.sync.config

import android.content.Context
import android.content.SharedPreferences
import com.openhealth.sync.data.remote.HuaweiConfig

/**
 * Tracks whether the person has already seen the permissions-rationale
 * onboarding screen (v1.9.12, sprint 7). Shown once, the first time
 * "Connect Google Health" is tapped, explaining in plain language what
 * BitLut does with the requested Health Connect permissions before the
 * system's own (much terser) permission dialog appears.
 */
class OnboardingPrefs(context: Context) {

    private val prefs: SharedPreferences = context.getSharedPreferences(
        HuaweiConfig.PREFS_NAME,
        Context.MODE_PRIVATE
    )

    fun hasSeenPermissionsRationale(): Boolean = prefs.getBoolean(KEY_SEEN_PERMISSIONS_RATIONALE, false)

    fun markPermissionsRationaleSeen() {
        prefs.edit().putBoolean(KEY_SEEN_PERMISSIONS_RATIONALE, true).apply()
    }

    companion object {
        private const val KEY_SEEN_PERMISSIONS_RATIONALE = "onboarding_seen_permissions_rationale"
    }
}
