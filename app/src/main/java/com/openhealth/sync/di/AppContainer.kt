package com.openhealth.sync.di
import android.content.Context
import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.data.HuaweiAuthManager
class AppContainer(private val context: Context) {
    val googleHealthManager by lazy { GoogleHealthManager(context) }
    val huaweiAuthManager by lazy { HuaweiAuthManager(context) }
}
