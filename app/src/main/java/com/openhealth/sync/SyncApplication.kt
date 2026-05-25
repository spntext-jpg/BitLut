package com.openhealth.sync
import android.app.Application
import com.openhealth.sync.di.AppContainer
class SyncApplication : Application() {
    lateinit var container: AppContainer
    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
    }
}
