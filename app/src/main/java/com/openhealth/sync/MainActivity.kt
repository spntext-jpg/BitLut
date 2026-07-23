package com.openhealth.sync

import android.app.Activity
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.health.connect.client.PermissionController
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.lifecycleScope
import com.openhealth.sync.config.HealthDataSource
import com.openhealth.sync.config.WidgetVisibilityPrefs
import com.openhealth.sync.domain.SyncOrchestrator
import com.openhealth.sync.platform.HmsCoreHelper
import com.openhealth.sync.ui.DashboardViewModel
import com.openhealth.sync.ui.ImportViewModel
import com.openhealth.sync.ui.SyncViewModel
import com.openhealth.sync.ui.theme.BitLutExpressiveTheme
import com.openhealth.sync.util.AppLogger
import kotlinx.coroutines.launch
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue

class MainActivity : ComponentActivity() {

    private val onboardingPrefs by lazy { com.openhealth.sync.config.OnboardingPrefs(applicationContext) }

    private val syncViewModel: SyncViewModel by viewModels {
        val app = application as SyncApplication
        SyncViewModel.provideFactory(
            app.container.googleHealthManager,
            app.container.huaweiHealthManager,
            this,
            app.container.dataSourcePrefs
        )
    }

    private val dashboardViewModel: DashboardViewModel by viewModels {
        val app = application as SyncApplication
        DashboardViewModel.provideFactory(
            app.container.googleHealthManager,
            WidgetVisibilityPrefs(applicationContext),
            app.container.dashboardSnapshotCache,
            app.container.goalPrefs,
            app.container.achievementsStore
        )
    }

    private val importViewModel: ImportViewModel by lazy {
        ViewModelProvider(
            this,
            ImportViewModel.provideFactory(
                (application as SyncApplication).container.googleHealthManager,
                this
            )
        )[ImportViewModel::class.java]
    }

    private val syncOrchestrator: SyncOrchestrator by lazy {
        SyncOrchestrator(this, syncViewModel.googleManager)
    }

    private val archiveImportLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode == Activity.RESULT_OK) {
                val uri = result.data?.data
                if (uri != null) {
                    Toast.makeText(this, getString(R.string.import_archive_selected), Toast.LENGTH_LONG).show()
                    AppLogger.i("MainActivity", "Huawei archive selected: $uri")
                } else {
                    Toast.makeText(this, getString(R.string.status_error), Toast.LENGTH_LONG).show()
                }
            }
        }

    private val notificationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            AppLogger.i("MainActivity", "POST_NOTIFICATIONS permission result: $granted")
            // No toast either way: this permission is optional polish (goal
            // reminders, streak/record celebrations), not something the core
            // sync flow depends on, so a denial should not interrupt the
            // person with an error-style message.
        }

    private val googlePermissionLauncher = registerForActivityResult(
        PermissionController.createRequestPermissionResultContract()
    ) { granted ->
        AppLogger.i("MainActivity", "Health Connect permissions returned: $granted")
        syncViewModel.refreshStatuses()
        dashboardViewModel.refresh()

        if (!granted.containsAll(syncViewModel.googleManager.permissions)) {
            Toast.makeText(this, getString(R.string.toast_hc_permissions), Toast.LENGTH_LONG).show()
        }
    }

    private val huaweiAuthorizationLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            val success = syncViewModel.huaweiHealthManager.handleAuthorizationResult(
                result.resultCode,
                result.data
            )
            syncViewModel.onHuaweiAuthorizationResult(success)
            syncViewModel.refreshStatuses()

            // Sprint (2026-07-18): previously this always showed the same
            // generic toast_huawei_pending text for every possible failure
            // (scope pending, privacy not accepted, cert mismatch, invalid
            // config) -- which is exactly the message an AppGallery reviewer
            // quoted in a real rejection report, with no way for anyone
            // reading it to tell which of those 4 very different causes was
            // actually in play. The specific reason (and full explanation)
            // now lives in the Settings screen's Huawei card instead of a
            // fleeting Toast, since a Toast can't hold enough text to be
            // useful here -- this toast just points there.
            Toast.makeText(
                this,
                if (success) getString(R.string.toast_huawei_connected) else getString(R.string.toast_huawei_failed),
                Toast.LENGTH_LONG
            ).show()
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Sprint (2026-07-14): targetSdk 35 already forces edge-to-edge on
        // real Android 15+ devices with or without this call (that's the
        // whole point of the platform enforcement) -- what enableEdgeToEdge()
        // actually buys us is (a) the same look on Android 8-14 devices,
        // which would otherwise render with old-style opaque system bars,
        // and (b) correct light/dark status- and navigation-bar icon
        // contrast that auto-follows system dark mode, matching how
        // isDark is computed in FinalBitLutShell (isSystemInDarkTheme()) --
        // no manual SystemBarStyle wiring needed since both use the same
        // system signal. The root Scaffold in FinalBitLutShell already
        // applies M3's default contentWindowInsets, and the bottom nav bar
        // already calls navigationBarsPadding() itself, so no other insets
        // work was needed for this.
        enableEdgeToEdge()

        setupPeriodicSync()

        setContent {
            BitLutExpressiveTheme {
                var hasSeenOnboarding by androidx.compose.runtime.remember {
                    androidx.compose.runtime.mutableStateOf(onboardingPrefs.hasSeenPermissionsRationale())
                }
                FinalBitLutShell(
                    dashboardStateProvider = {
                        dashboardViewModel.state.collectAsStateWithLifecycle().value
                    },
                    syncStateProvider = {
                        syncViewModel.uiState.collectAsStateWithLifecycle().value
                    },
                    onRefresh = {
                        syncViewModel.refreshStatuses()
                        dashboardViewModel.refresh()
                    },
                    onRequestGoogle = { requestGoogleHealthPermissions() },
                    onRequestHuawei = { startHuaweiAuthorization() },
                    onSyncNow = { triggerImmediateSync() },
                    onImportArchive = { openHuaweiArchiveImport() },
                    onExportCsv = { exportCsv() },
                    onWidgetVisibilityChanged = { widget, visible ->
                        dashboardViewModel.setWidgetVisible(widget, visible)
                    },
                    onStepsGoalChanged = { value -> dashboardViewModel.setStepsGoal(value) },
                    onDistanceGoalChanged = { value -> dashboardViewModel.setDistanceGoalMeters(value) },
                    onActiveMinutesGoalChanged = { value -> dashboardViewModel.setActiveMinutesGoal(value) },
                    onCaloriesGoalChanged = { value -> dashboardViewModel.setCaloriesGoalKcal(value) },
                    onDataSourceSelected = { source -> selectDataSource(source) },
                    hasSeenPermissionsOnboarding = hasSeenOnboarding,
                    onPermissionsOnboardingSeen = {
                        onboardingPrefs.markPermissionsRationaleSeen()
                        hasSeenOnboarding = true
                    },
                    importViewModel = importViewModel
                )
            }
        }
    }

    /**
     * Sprint (2026-07-09): the 2026-07-07 cold-launch fix only ran once, in
     * onCreate() -- which fires exactly once per Activity instance. Every
     * later return to the app (after being backgrounded, after a permission
     * dialog, after switching apps) used to rely on stale state until the
     * next 30-minute periodic tick. That is exactly why data only ever
     * looked fresh after a background/foreground cycle: by the time the
     * person returned, the *original* cold-launch sync had usually already
     * finished, but nothing re-read Health Connect until some other,
     * unrelated event happened to trigger a refresh. Moving the trigger to
     * onResume() -- which also fires once right after onCreate on a genuine
     * cold launch, so nothing needs to stay duplicated in onCreate too --
     * makes every single return to the app kick off a fresh sync + refresh
     * immediately, not just the very first one.
     */
    override fun onResume() {
        super.onResume()
        refreshUiStatusOnLaunch()
        triggerAutomaticSyncOnLaunch()
    }

    private fun refreshUiStatusOnLaunch() {
        syncViewModel.refreshStatuses()
        dashboardViewModel.refresh()
    }

    private fun requestGoogleHealthPermissions() {
        com.openhealth.sync.config.requestGoogleHealthPermissions(
            context = this,
            googleManager = syncViewModel.googleManager,
            launcher = googlePermissionLauncher
        )
    }

    private fun startHuaweiAuthorization() {
        try {
            if (!HmsCoreHelper.isInstalled(this)) {
                Toast.makeText(this, HmsCoreHelper.missingMessage, Toast.LENGTH_LONG).show()
                return
            }

            if (!HmsCoreHelper.isHuaweiHealthInstalled(this)) {
                Toast.makeText(this, getString(R.string.toast_huawei_health_missing), Toast.LENGTH_LONG).show()
                return
            }

            huaweiAuthorizationLauncher.launch(syncViewModel.huaweiHealthManager.getAuthorizationIntent())
        } catch (e: Exception) {
            AppLogger.e("MainActivity", "Huawei authorization start failed: ${e.message}", e)
            Toast.makeText(this, getString(R.string.toast_huawei_start_failed), Toast.LENGTH_LONG).show()
        }
    }

    private fun openHuaweiArchiveImport() {
        try {
            val intent = android.content.Intent(android.content.Intent.ACTION_OPEN_DOCUMENT).apply {
                addCategory(android.content.Intent.CATEGORY_OPENABLE)
                type = "*/*"
                putExtra(
                    android.content.Intent.EXTRA_MIME_TYPES,
                    arrayOf(
                        "application/zip",
                        "application/json",
                        "text/*",
                        "application/octet-stream"
                    )
                )
            }
            archiveImportLauncher.launch(intent)
        } catch (t: Throwable) {
            AppLogger.e("MainActivity", "Archive picker failed: ${t.message}", t)
            Toast.makeText(this, getString(R.string.status_error), Toast.LENGTH_LONG).show()
        }
    }

    /**
     * Sprint (2026-07-14): exports exactly what BitLut already reads for its
     * own dashboard (daily steps/distance/calories + recent workouts) as a
     * CSV via the system share sheet. Read work happens off the main thread
     * in lifecycleScope, same as every other Health Connect read in this
     * class; CsvExporter.writeAndShare does its own file I/O synchronously
     * but is only ever called here, already off the main thread.
     */
    private fun exportCsv() {
        lifecycleScope.launch {
            val app = application as SyncApplication
            // readDailyTotals()/readRecentWorkouts() are plain GoogleHealthManager
            // functions, not part of the HealthConnectManager interface that
            // AppContainer.googleHealthManager is declared as (same reason
            // SyncWorker only ever calls the interface's readDashboardSnapshot()).
            // AppContainer always constructs a real GoogleHealthManager, so this
            // cast is safe in practice; the null-check is defensive only.
            val googleManager = app.container.googleHealthManager as? com.openhealth.sync.data.GoogleHealthManager
            if (googleManager == null) {
                Toast.makeText(this@MainActivity, getString(R.string.status_error), Toast.LENGTH_LONG).show()
                return@launch
            }
            val dailyTotals = googleManager.readDailyTotals(30)
            val workouts = googleManager.readRecentWorkouts(100)
            com.openhealth.sync.util.CsvExporter.writeAndShare(this@MainActivity, dailyTotals, workouts)
        }
    }

    private fun selectDataSource(source: HealthDataSource) {
        if (syncViewModel.uiState.value.selectedDataSource == source) return

        syncViewModel.setDataSource(source)
        dashboardViewModel.onDataSourceChanged()
        AppLogger.i("MainActivity", "Selected dashboard/import source: $source")

        // Refresh immediately in either mode. Huawei mode imports into Health
        // Connect; Google Fit mode skips Huawei and refreshes the selected
        // source cache/widget only.
        triggerImmediateSync()
    }

    private fun setupPeriodicSync() {
        syncOrchestrator.schedulePeriodic()
        com.openhealth.sync.data.worker.BackgroundSyncScheduler.scheduleEveningReminder(this)
        requestNotificationPermissionIfNeeded()
    }

    /**
     * POST_NOTIFICATIONS is a runtime permission on API 33+ (Android 13).
     * Requested once, right after the sync schedule is set up, so the
     * evening reminder (sprint 4) and any future notification content has a
     * chance to actually be delivered. If denied, NotificationHelper simply
     * no-ops on every post attempt -- there is no degraded/broken state, the
     * app just stays silent, matching the same "notifications are optional
     * polish" philosophy used throughout this feature.
     */
    private fun requestNotificationPermissionIfNeeded() {
        if (android.os.Build.VERSION.SDK_INT < android.os.Build.VERSION_CODES.TIRAMISU) return

        val granted = androidx.core.content.ContextCompat.checkSelfPermission(
            this,
            android.Manifest.permission.POST_NOTIFICATIONS
        ) == android.content.pm.PackageManager.PERMISSION_GRANTED

        if (!granted) {
            notificationPermissionLauncher.launch(android.Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    /**
     * Sprint (2026-07-07): expedite a Huawei -> Health Connect sync
     * automatically on every cold launch, using the exact same orchestration
     * path as the manual "Sync now" button, so the dashboard no longer
     * depends on the next periodic tick (or the person manually opening
     * Google Fit / Health Connect) to show fresh data. Silent no-op if
     * Health Connect permissions aren't granted yet -- onboarding/the lock
     * screen is the right place to ask for that, not an unsolicited prompt
     * on every app open.
     */
    private fun triggerAutomaticSyncOnLaunch() {
        lifecycleScope.launch {
            syncOrchestrator.triggerImmediateSync(
                lifecycleOwner = this@MainActivity,
                onStarted = { syncViewModel.markSyncStarted() },
                onMissingPermissions = {
                    AppLogger.i("MainActivity", "Skipping automatic launch sync: Health Connect permissions not granted yet")
                },
                onCompleted = { success -> syncViewModel.markSyncCompleted(success) },
                onDashboardRefresh = { dashboardViewModel.refresh() }
            )
        }
    }

    private fun triggerImmediateSync() {
        lifecycleScope.launch {
            syncOrchestrator.triggerImmediateSync(
                lifecycleOwner = this@MainActivity,
                onStarted = { syncViewModel.markSyncStarted() },
                onMissingPermissions = {
                    Toast.makeText(
                        this@MainActivity,
                        getString(R.string.toast_hc_permissions),
                        Toast.LENGTH_LONG
                    ).show()
                    requestGoogleHealthPermissions()
                },
                onCompleted = { success -> syncViewModel.markSyncCompleted(success) },
                onDashboardRefresh = { dashboardViewModel.refresh() }
            )
        }
    }
}
