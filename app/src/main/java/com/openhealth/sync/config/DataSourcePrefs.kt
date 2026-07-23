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

    companion object {
        const val GOOGLE_FIT_PACKAGE = "com.google.android.apps.fitness"
        private const val KEY_SELECTED_SOURCE = "selected_health_data_source"
    }
}
