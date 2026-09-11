package com.openhealth.sync
import android.app.Application
import com.openhealth.sync.data.worker.BackgroundSyncScheduler
import com.openhealth.sync.di.AppContainer
class SyncApplication : Application() {
    lateinit var container: AppContainer
    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)

        // 2026-09: previously only scheduled from MainActivity.onCreate(),
        // which meant the periodic sync and evening reminder were only
        // re-registered when a person actually opened the app. WorkManager
        // itself already recovers from a device reboot (its own internal
        // RescheduleReceiver) and from the app being force-stopped (its
        // own ForceStopRunnable, which re-applies pending work the next
        // time this process starts for any reason) -- so this call is not
        // what makes background sync survive those two cases, WorkManager's
        // own library code already does that. What this closes is a
        // narrower gap: Application.onCreate() runs on every process start,
        // including ones triggered by WorkManager's own background executor
        // waking the process to run a job, not just ones triggered by a
        // person tapping the launcher icon. Both calls are idempotent
        // (ExistingPeriodicWorkPolicy.KEEP plus a one-time SharedPreferences
        // migration flag), so calling them here in addition to their
        // existing MainActivity call has no duplicate-scheduling risk.
        BackgroundSyncScheduler.schedulePeriodic(this)
        BackgroundSyncScheduler.scheduleEveningReminder(this)
    }
}
