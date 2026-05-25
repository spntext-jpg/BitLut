package com.openhealth.sync.di
import android.content.Context
import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.data.HuaweiAuthManager
class AppContainer(private val context: Context) {
    val googleHealthManager: GoogleHealthManager by lazy { GoogleHealthManager(context) }
    val huaweiAuthManager: HuaweiAuthManager by lazy { HuaweiAuthManager(context) }
}
