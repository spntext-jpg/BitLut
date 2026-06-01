package com.openhealth.sync.platform

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import com.openhealth.sync.util.AppLogger

object HmsCoreHelper {
    private const val TAG = "HmsCoreHelper"

    private const val HMS_CORE_PACKAGE = "com.huawei.hwid"
    private const val HUAWEI_HEALTH_PACKAGE = "com.huawei.health"
    private const val APPGALLERY_PACKAGE = "com.huawei.appmarket"

    private const val HMS_CORE_WEB_URI = "https://consumer.huawei.com/en/mobileservices/hms-core/"
    private const val HUAWEI_HEALTH_WEB_URI = "https://consumer.huawei.com/en/health/"
    private const val APPGALLERY_WEB_URI = "https://consumer.huawei.com/en/mobileservices/appgallery/"

    const val missingMessage: String =
        "HMS Core is required for Huawei Health authorization. Install or update HMS Core and try again."

    fun isInstalled(context: Context): Boolean = isHmsCoreInstalled(context)

    fun isHmsCoreInstalled(context: Context): Boolean =
        isPackageInstalled(context, HMS_CORE_PACKAGE)

    fun isHuaweiHealthInstalled(context: Context): Boolean =
        isPackageInstalled(context, HUAWEI_HEALTH_PACKAGE)

    fun isAppGalleryInstalled(context: Context): Boolean =
        isPackageInstalled(context, APPGALLERY_PACKAGE)

    fun prerequisiteStatus(context: Context): String =
        "hmsCore=${isHmsCoreInstalled(context)} huaweiHealth=${isHuaweiHealthInstalled(context)} appGallery=${isAppGalleryInstalled(context)}"

    fun canResolveIntent(context: Context, intent: Intent): Boolean =
        intent.resolveActivity(context.packageManager) != null

    fun openInstallPage(context: Context) = openHmsCoreInstall(context)

    fun openHmsCoreInstall(context: Context) {
        openFirstAvailable(
            context = context,
            label = "HMS Core install/update page",
            intents = listOf(
                Intent(Intent.ACTION_VIEW, Uri.parse("appmarket://details?id=$HMS_CORE_PACKAGE")).apply {
                    setPackage(APPGALLERY_PACKAGE)
                },
                Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=$HMS_CORE_PACKAGE")),
                Intent(Intent.ACTION_VIEW, Uri.parse(HMS_CORE_WEB_URI))
            )
        )
    }

    fun openHuaweiHealth(context: Context) {
        context.packageManager.getLaunchIntentForPackage(HUAWEI_HEALTH_PACKAGE)?.let { intent ->
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
            AppLogger.i(TAG, "Opened Huawei Health app")
            return
        }

        openFirstAvailable(
            context = context,
            label = "Huawei Health install/open page",
            intents = listOf(
                Intent(Intent.ACTION_VIEW, Uri.parse("appmarket://details?id=$HUAWEI_HEALTH_PACKAGE")).apply {
                    setPackage(APPGALLERY_PACKAGE)
                },
                Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=$HUAWEI_HEALTH_PACKAGE")),
                Intent(Intent.ACTION_VIEW, Uri.parse(HUAWEI_HEALTH_WEB_URI))
            )
        )
    }

    fun openAppGallery(context: Context) {
        context.packageManager.getLaunchIntentForPackage(APPGALLERY_PACKAGE)?.let { intent ->
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
            AppLogger.i(TAG, "Opened AppGallery")
            return
        }

        openFirstAvailable(
            context = context,
            label = "AppGallery install/open page",
            intents = listOf(
                Intent(Intent.ACTION_VIEW, Uri.parse(APPGALLERY_WEB_URI)),
                Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=$APPGALLERY_PACKAGE"))
            )
        )
    }

    private fun isPackageInstalled(context: Context, packageName: String): Boolean =
        try {
            context.packageManager.getPackageInfo(packageName, 0)
            true
        } catch (_: PackageManager.NameNotFoundException) {
            false
        }

    private fun openFirstAvailable(context: Context, label: String, intents: List<Intent>) {
        for (intent in intents) {
            try {
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
                AppLogger.i(TAG, "Opened $label")
                return
            } catch (e: ActivityNotFoundException) {
                AppLogger.w(TAG, "$label intent unavailable: ${e.message}")
            } catch (e: Exception) {
                AppLogger.w(TAG, "Failed to open $label: ${e.message}")
            }
        }

        AppLogger.e(TAG, "No available intent for $label")
    }
}
