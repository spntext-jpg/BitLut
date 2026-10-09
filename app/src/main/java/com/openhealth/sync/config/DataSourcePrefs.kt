package com.openhealth.sync.config

import android.content.Context
import android.content.SharedPreferences
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.util.AppLogger

private const val TAG = "DataSourcePrefs"

/**
 * Exactly one activity source drives BitLut's dashboard at a time.
 *
 * HUAWEI_HEALTH means Huawei data imported by BitLut and therefore stored in
 * Health Connect with BitLut's own package as the data origin. GOOGLE_FIT means
 * records written by the Google Fit package. Keeping this choice exclusive is
 * what prevents raw Health Connect records from two apps being summed twice.
 *
 * GOOGLE_FIT is presented to people as "Google Health": the Fitbit app was
 * renamed Google Health in 2026 and Google Fit is being sunset. The enum name
 * and storage value stay as they are so existing installs need no migration.
 * Daily totals still read the single Google Fit origin; only workout sessions
 * also accept the Google Health app's origin, see
 * [DataSourcePrefs.selectedWorkoutOriginPackages].
 */
enum class HealthDataSource(val storageValue: String) {
    HUAWEI_HEALTH("huawei_health"),
    GOOGLE_FIT("google_fit");

    companion object {
        fun fromStorage(value: String?): HealthDataSource =
            entries.firstOrNull { it.storageValue == value } ?: HUAWEI_HEALTH
    }
}

class DataSourcePrefs(context: Context) {
    private val prefs: SharedPreferences = context.getSharedPreferences(
        HuaweiConfig.PREFS_NAME,
        Context.MODE_PRIVATE
    )

    fun selected(): HealthDataSource =
        HealthDataSource.fromStorage(prefs.getString(KEY_SELECTED_SOURCE, null))

    fun setSelected(source: HealthDataSource) {
        val previous = selected()
        if (previous == source) return

        prefs.edit().putString(KEY_SELECTED_SOURCE, source.storageValue).apply()
        AppLogger.i(TAG, "Health data source changed: $previous -> $source")
    }

    /** Health Connect data-origin package represented by the selected source. */
    fun selectedOriginPackage(bitLutPackageName: String): String = when (selected()) {
        HealthDataSource.HUAWEI_HEALTH -> bitLutPackageName
        HealthDataSource.GOOGLE_FIT -> GOOGLE_FIT_PACKAGE
    }

    /**
     * Health Connect data-origin packages allowed to own workout *sessions* for
     * the selected source. Google workouts can be written by two different apps:
     * Google Fit and the Google Health app (the renamed Fitbit app, a separate
     * package and therefore a separate Health Connect origin). Reading only the
     * Google Fit origin hid every workout recorded in Google Health while steps
     * still appeared. Huawei mode stays on BitLut's own origin.
     */
    fun selectedWorkoutOriginPackages(bitLutPackageName: String): Set<String> = when (selected()) {
        HealthDataSource.HUAWEI_HEALTH -> setOf(bitLutPackageName)
        HealthDataSource.GOOGLE_FIT -> setOf(GOOGLE_FIT_PACKAGE, GOOGLE_HEALTH_PACKAGE)
    }

    companion object {
        const val GOOGLE_FIT_PACKAGE = "com.google.android.apps.fitness"

        /** Google Health app = the renamed Fitbit app (Play package id unchanged). */
        const val GOOGLE_HEALTH_PACKAGE = "com.fitbit.FitbitMobile"
        private const val KEY_SELECTED_SOURCE = "selected_health_data_source"
    }
}
