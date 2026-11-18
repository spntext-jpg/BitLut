package com.openhealth.sync.data;

import android.content.Context;
import androidx.health.connect.client.HealthConnectClient;
import androidx.health.connect.client.HealthConnectFeatures;

/**
 * Maps the SDK's Java IntDef constants to a type shared by the Kotlin call sites.
 */
enum HealthConnectSdkAvailability {
    AVAILABLE,
    UPDATE_REQUIRED,
    UNAVAILABLE;

    static boolean supportsBackgroundRead(HealthConnectClient client) {
        return client.getFeatures().getFeatureStatus(
                HealthConnectFeatures.FEATURE_READ_HEALTH_DATA_IN_BACKGROUND)
                == HealthConnectFeatures.FEATURE_STATUS_AVAILABLE;
    }

    static HealthConnectSdkAvailability read(Context context) {
        switch (HealthConnectClient.getSdkStatus(context)) {
            case HealthConnectClient.SDK_AVAILABLE:
                return AVAILABLE;
            case HealthConnectClient.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED:
                return UPDATE_REQUIRED;
            default:
                return UNAVAILABLE;
        }
    }
}
