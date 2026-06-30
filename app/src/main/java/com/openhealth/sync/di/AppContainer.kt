package com.openhealth.sync.di

import android.content.Context
import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.data.HealthConnectManager
import com.openhealth.sync.data.HuaweiHealthManager
import com.openhealth.sync.data.HuaweiHealthReader

class AppContainer(private val context: Context) {
    val googleHealthManager: HealthConnectManager by lazy { GoogleHealthManager(context) }
    val huaweiHealthManager: HuaweiHealthReader by lazy { HuaweiHealthManager(context) }
}
