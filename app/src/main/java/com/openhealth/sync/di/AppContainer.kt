package com.openhealth.sync.di

import android.content.Context
import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.data.HealthConnectManager
import com.openhealth.sync.data.HuaweiHealthManager
import com.openhealth.sync.data.HuaweiHealthReader
import com.openhealth.sync.data.worker.SyncRunLease

class AppContainer(private val context: Context) {
    val googleHealthManager: HealthConnectManager by lazy { GoogleHealthManager(context) }
    val huaweiHealthManager: HuaweiHealthReader by lazy { HuaweiHealthManager(context) }

    /**
     * A single process-wide [SyncRunLease] instance, shared by every
     * [com.openhealth.sync.data.worker.SyncWorker] execution (manual "Sync now"
     * and the periodic 30-minute background sync alike).
     *
     * This used to be created fresh inside each [com.openhealth.sync.data.worker.SyncWorker]
     * via `by lazy { SyncRunLease(applicationContext) }`. Because manual and
     * periodic sync use different WorkManager unique-work names, WorkManager
     * does not serialize them against each other, so two concurrently-running
     * `SyncWorker` instances could each construct their own `SyncRunLease`
     * object -- and the lease's internal lock only protects callers that share
     * the *same* object, so the two workers had no real mutual exclusion.
     * Hosting one shared instance here closes that gap.
     */
    val syncRunLease: SyncRunLease by lazy { SyncRunLease(context) }
}
