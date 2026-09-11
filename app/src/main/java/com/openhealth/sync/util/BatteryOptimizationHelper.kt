package com.openhealth.sync.util

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.PowerManager
import android.provider.Settings

/**
 * Android 12+ (API 31) advisory for OEM battery/autostart restrictions.
 *
 * BitLut's background sync (BackgroundSyncScheduler's 30-minute
 * PeriodicWorkRequest) already relies on WorkManager's own guarantees, which
 * are sufficient on stock Android. On OEM skins with their own aggressive
 * battery managers (EMUI/Magic UI "Protected Apps", MIUI/HyperOS
 * autostart/battery saver, and similar on other manufacturers), the OS can
 * still force-stop the app process well before WorkManager would otherwise
 * run it again -- WorkManager recovers automatically the next time the
 * process starts for any reason, but if the OEM restriction keeps
 * preventing that, syncs can silently stop appearing for hours. This can't
 * be fixed from inside the app; the person has to grant the exemption
 * themselves. This helper only detects the condition and opens the
 * relevant system settings screen -- it never requests the exemption
 * directly (see below for why).
 *
 * Scoped to API 31+ only: this is when BitLut's diagnostic evidence for
 * this failure mode exists, and Android's own battery-settings UI varies
 * enough release to release that supporting every version back to minSdk
 * 26 was judged not worth the added surface for a single advisory card.
 */
object BatteryOptimizationHelper {

    /**
     * True when the OS reports BitLut is currently *not* exempt from
     * battery optimizations and the advisory is relevant on this API
     * level. False on API < 31 (the hint isn't shown there) so callers can
     * gate the whole card on this one check.
     */
    fun shouldShowHint(context: Context): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return false
        val powerManager = context.getSystemService(Context.POWER_SERVICE) as? PowerManager
            ?: return false
        return !powerManager.isIgnoringBatteryOptimizations(context.packageName)
    }

    /**
     * Opens the general "Ignore battery optimizations" list (Settings >
     * Apps > Special app access > Battery optimization on stock Android;
     * the OEM equivalent on EMUI/MIUI/etc.) rather than
     * ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS' direct one-tap grant
     * dialog. The direct dialog needs the REQUEST_IGNORE_BATTERY_OPTIMIZATIONS
     * permission and is meant for apps whose core function requires it
     * (e.g. VPNs, alarm clocks); BitLut's periodic sync is exactly the kind
     * of best-effort background work Android's own developer guidance
     * says should NOT use that permission. Landing on the list keeps this
     * a plain, review-safe settings deep link with no extra permission
     * declaration, at the cost of the person needing to find BitLut in the
     * list themselves instead of a single tap.
     */
    fun settingsIntent(): Intent =
        Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)
}
