package com.openhealth.sync.config
import com.openhealth.sync.data.HealthConnectManager

import android.content.Context
import android.widget.Toast
import androidx.activity.result.ActivityResultLauncher
import com.openhealth.sync.R
import com.openhealth.sync.data.HealthConnectStatus
import com.openhealth.sync.util.AppLogger

private const val TAG = "GoogleHealthPermissionRequester"

/**
 * Self-healing entry point for "Connect Google Health" / "Подключить Google Health".
 *
 * Always re-opens the permission request, even if permissions were already granted
 * before -- this is the one place the person can re-trigger the request, so it must
 * never silently no-op just because the dashboard already reports hasPermissions=true.
 *
 * Checks Health Connect availability first and wraps the actual launch() call in
 * try/catch: if no app on the device can handle the permission-request intent (no
 * Health Connect provider installed, or a provider that doesn't support the
 * contract), ActivityResultLauncher.launch() can throw synchronously. Previously this
 * call had no guard at all in MainActivity, which is the most likely direct cause of
 * the AppGallery review crash report ("click connect google health - app crashes").
 *
 * Returns true only when launcher.launch() was actually invoked without throwing --
 * i.e. only when a system permission screen is genuinely about to appear and its
 * result callback will eventually fire. MainActivity uses this to know when the
 * next onResume() is just that screen returning, not a real "back to the app" event.
 */
fun requestGoogleHealthPermissions(
    context: Context,
    googleManager: HealthConnectManager,
    launcher: ActivityResultLauncher<Set<String>>
): Boolean {
    when (googleManager.getStatus()) {
        HealthConnectStatus.NOT_INSTALLED -> {
            Toast.makeText(context, context.getString(R.string.toast_hc_not_installed), Toast.LENGTH_LONG).show()
            return false
        }
        HealthConnectStatus.NEEDS_UPDATE -> {
            Toast.makeText(context, context.getString(R.string.toast_hc_needs_update), Toast.LENGTH_LONG).show()
            return false
        }
        HealthConnectStatus.NOT_SUPPORTED -> {
            Toast.makeText(context, context.getString(R.string.toast_hc_not_supported), Toast.LENGTH_LONG).show()
            return false
        }
        HealthConnectStatus.AVAILABLE -> {
            // fall through to the actual launch below
        }
    }
    return try {
        launcher.launch(googleManager.permissions)
        true
    } catch (e: Exception) {
        AppLogger.e(TAG, "Failed to launch Health Connect permission request: ${e.message}", e)
        Toast.makeText(context, context.getString(R.string.toast_hc_launch_failed), Toast.LENGTH_LONG).show()
        false
    }
}
