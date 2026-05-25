package com.openhealth.sync.platform

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import com.openhealth.sync.util.AppLogger

object HmsCoreHelper {
    private const val HMS_CORE_PACKAGE = "com.huawei.hwid"
    private const val HUAWEI_HEALTH_PACKAGE = "com.huawei.health"
    private const val APPGALLERY_PACKAGE = "com.huawei.appmarket"
    private const val HMS_CORE_WEB_URI = "https://consumer.huawei.com/ru/mobileservices/hms-core/"

    const val missingMessage: String =
        "HMS Core is required for Huawei Health authorization. Install or update HMS Core and try again."

    fun isHmsCoreInstalled(context: Context): Boolean = try {
        context.packageManager.getPackageInfo(HMS_CORE_PACKAGE, 0)
        true
    } catch (_: PackageManager.NameNotFoundException) {
        false
    }

    fun isInstalled(context: Context): Boolean = isHmsCoreInstalled(context)

    fun isHuaweiHealthInstalled(context: Context): Boolean = try {
        context.packageManager.getPackageInfo(HUAWEI_HEALTH_PACKAGE, 0)
        true
    } catch (_: PackageManager.NameNotFoundException) {
        false
    }


    fun openHmsCoreInstall(context: Context) {
        val intents = listOf(
            Intent(Intent.ACTION_VIEW, Uri.parse(HMS_CORE_WEB_URI)),
            Intent(Intent.ACTION_VIEW, Uri.parse("appmarket://details?id=$HMS_CORE_PACKAGE")).apply {
                setPackage(APPGALLERY_PACKAGE)
            },
            Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=$HMS_CORE_PACKAGE"))
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

    fun openHuaweiHealth(context: Context) {
        val launchIntent = context.packageManager.getLaunchIntentForPackage(HUAWEI_HEALTH_PACKAGE)
        if (launchIntent != null) {
            launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(launchIntent)
            AppLogger.i("HmsCoreHelper", "Opened Huawei Health app")
            return
        }

        val intents = listOf(
            Intent(Intent.ACTION_VIEW, Uri.parse("appmarket://details?id=$HUAWEI_HEALTH_PACKAGE")).apply {
                setPackage(APPGALLERY_PACKAGE)
            },
            Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=$HUAWEI_HEALTH_PACKAGE")),
            Intent(Intent.ACTION_VIEW, Uri.parse("https://consumer.huawei.com/en/health/"))
        )

        for (intent in intents) {
            try {
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
                AppLogger.i("HmsCoreHelper", "Opened Huawei Health install/open page")
                return
            } catch (e: Exception) {
                AppLogger.w("HmsCoreHelper", "Huawei Health fallback failed: ${e.message}")
            }
        }
    }
}
