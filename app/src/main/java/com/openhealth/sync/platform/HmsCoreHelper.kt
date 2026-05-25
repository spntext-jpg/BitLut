package com.openhealth.sync.platform

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import com.openhealth.sync.util.AppLogger

object HmsCoreHelper {
    private const val HMS_CORE_PACKAGE = "com.huawei.hwid"
    private const val APPGALLERY_PACKAGE = "com.huawei.appmarket"
    private const val HMS_CORE_WEB_URI = "https://consumer.huawei.com/en/mobileservices/hms-core/"

    const val missingMessage: String =
        "HMS Core is required for Huawei Health authorization. Install or update HMS Core and try again."

    fun isHmsCoreInstalled(context: Context): Boolean = try {
        context.packageManager.getPackageInfo(HMS_CORE_PACKAGE, 0)
        true
    } catch (_: PackageManager.NameNotFoundException) {
        false
    }

    fun isInstalled(context: Context): Boolean = isHmsCoreInstalled(context)

    fun openHmsCoreInstall(context: Context) {
        val intents = listOf(
            Intent(Intent.ACTION_VIEW, Uri.parse("appmarket://details?id=$HMS_CORE_PACKAGE")).apply {
                setPackage(APPGALLERY_PACKAGE)
            },
            Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=$HMS_CORE_PACKAGE")),
            Intent(Intent.ACTION_VIEW, Uri.parse(HMS_CORE_WEB_URI))
        )

        for (intent in intents) {
            try {
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
                AppLogger.i("HmsCoreHelper", "Opened HMS Core install/update page")
                return
            } catch (e: ActivityNotFoundException) {
                AppLogger.w("HmsCoreHelper", "HMS Core install intent unavailable: ${e.message}")
            } catch (e: Exception) {
                AppLogger.w("HmsCoreHelper", "Failed to open HMS Core install page: ${e.message}")
            }
        }
    }

    fun openInstallPage(context: Context) = openHmsCoreInstall(context)
}
