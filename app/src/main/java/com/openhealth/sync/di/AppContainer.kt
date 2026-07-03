package com.openhealth.sync.di

import android.content.Context
import com.openhealth.sync.config.GoalPrefs
import com.openhealth.sync.data.AchievementsStore
import com.openhealth.sync.data.DashboardSnapshotCache
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

    /**
     * Shared dashboard snapshot cache (v1.9.12). Both [com.openhealth.sync.data.worker.SyncWorker]
     * (writes after every successful background sync) and
     * [com.openhealth.sync.data.worker.EveningReminderWorker] (reads, to check
     * goal progress without a second live Health Connect call) use the same
     * instance -- there's no correctness requirement for a single shared
     * object the way there was for the lease, but centralizing it here avoids
     * three call sites each re-deriving "which SharedPreferences file does
     * this live in".
     */
    val dashboardSnapshotCache: DashboardSnapshotCache by lazy { DashboardSnapshotCache(context) }

    /** Shared activity-only personal records + streak store (v1.9.12). */
    val achievementsStore: AchievementsStore by lazy { AchievementsStore(context) }

    /** Shared user-configurable activity goals (v1.9.12). */
    val goalPrefs: GoalPrefs by lazy { GoalPrefs(context) }
}
