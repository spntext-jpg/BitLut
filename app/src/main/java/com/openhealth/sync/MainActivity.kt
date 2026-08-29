package com.openhealth.sync

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

    /**
     * onResume() is meant to catch a genuine "person switched back to the
     * app" event and kick off a fresh sync. A system permission dialog
     * (POST_NOTIFICATIONS) or a full-screen flow the app itself launched
     * (Health Connect permissions, Huawei authorization) also triggers
     * onResume() when it returns -- but that is not the person "coming
     * back", it's this same screen resuming right where it left off. A
     * real device log showed several redundant sync triggers firing back
     * to back right after a cold launch (five separate SyncWorker
     * executions inside 30 seconds, several of them manual-sync triggers
     * competing for the sync lease with the periodic one) -- consistent
     * with onResume() unconditionally re-triggering a sync every time one
     * of these system screens closes. Set to true right before launching
     * any of those three flows, reset to false as soon as its result
     * callback fires (or immediately, if the launch itself failed to
     * start and no result will ever arrive).
     */
    private var awaitingSystemResult = false

    private val notificationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            awaitingSystemResult = false
            AppLogger.i("MainActivity", "POST_NOTIFICATIONS permission result: $granted")
            // No toast either way: this permission is optional polish (goal
            // reminders, streak/record celebrations), not something the core
            // sync flow depends on, so a denial should not interrupt the
            // person with an error-style message.
        }

    private val googlePermissionLauncher = registerForActivityResult(
        PermissionController.createRequestPermissionResultContract()
    ) { granted ->
        awaitingSystemResult = false
        AppLogger.i("MainActivity", "Health Connect permissions returned: $granted")
        // Permission screens are explicit state transitions, so bypass
        // normal status throttling and perform one authoritative dashboard read.
        syncViewModel.googleManager.invalidateClientCache()
        syncViewModel.refreshStatuses(force = true)
        dashboardViewModel.refresh(force = true)

        if (!granted.containsAll(syncViewModel.googleManager.permissions)) {
            Toast.makeText(this, getString(R.string.toast_hc_permissions), Toast.LENGTH_LONG).show()
        }
    }

    private val huaweiAuthorizationLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            awaitingSystemResult = false
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
        // isSystemInDarkTheme() is read in BitLutExpressiveTheme (status/nav
        // bar icon contrast) and in FinalBitLutShell (card palette, since
        // 2026-08-22's dark theme) -- no manual SystemBarStyle wiring needed
        // since all three read the same system signal. The root Scaffold in
        // FinalBitLutShell already applies M3's default contentWindowInsets,
        // and the bottom nav bar already calls navigationBarsPadding()
        // itself, so no other insets work was needed for this.
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
                        syncViewModel.refreshStatuses(force = true)
                        dashboardViewModel.refreshFromCache()
                    },
                    onRequestGoogle = { requestGoogleHealthPermissions() },
                    onRequestHuawei = { startHuaweiAuthorization() },
                    onSyncNow = { triggerImmediateSync() },
                    onOpenHealthConnectSettings = { openHealthConnectSettings() },
                    onDataSourceSelected = { source -> selectDataSource(source) },
                    onStepsGoalChanged = { value -> dashboardViewModel.setStepsGoal(value) },
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
        if (awaitingSystemResult) {
            AppLogger.i("MainActivity", "Skipping onResume auto-sync: a system permission/authorization screen is still in progress")
        } else {
            triggerAutomaticSyncOnLaunch()
        }
    }

    private fun refreshUiStatusOnLaunch() {
        // DashboardViewModel already starts from the last successful cache.
        // Automatic sync below owns the fresh provider read and will refresh
        // this UI from that cache when WorkManager completes.
        syncViewModel.refreshStatuses()
    }

    private fun requestGoogleHealthPermissions() {
        awaitingSystemResult = com.openhealth.sync.config.requestGoogleHealthPermissions(
            context = this,
            googleManager = syncViewModel.googleManager,
            launcher = googlePermissionLauncher
        )
    }

    /**
     * Sprint 2026-08-27: opens Health Connect's own settings screen so the
     * user can check "Manage data > Data sources and priority" -- see the
     * doc comment on GoogleHealthManager.healthConnectSettingsIntent() for
     * why this is a distinct step from BitLut's own runtime permission
     * grant. syncViewModel.googleManager is declared as the
     * HealthConnectManager interface, which does not expose this
     * GoogleHealthManager-specific function. AppContainer always constructs a
     * real GoogleHealthManager, so this cast is safe in practice; the
     * null-check is defensive only. No ActivityResultLauncher/onResult
     * handling is needed here (unlike Huawei's authorization intent):
     * Health Connect's own settings screen returns no result BitLut acts
     * on, so a plain startActivity is enough, wrapped in the same
     * try/catch pattern as startHuaweiAuthorization above in case Health
     * Connect itself is missing or the intent otherwise fails to resolve.
     */
    private fun openHealthConnectSettings() {
        try {
            val googleManager = syncViewModel.googleManager as? com.openhealth.sync.data.GoogleHealthManager
            if (googleManager == null) {
                Toast.makeText(this, getString(R.string.toast_hc_launch_failed), Toast.LENGTH_LONG).show()
                return
            }
            startActivity(googleManager.healthConnectSettingsIntent())
        } catch (e: Exception) {
            AppLogger.e("MainActivity", "Opening Health Connect settings failed: ${e.message}", e)
            Toast.makeText(this, getString(R.string.toast_hc_launch_failed), Toast.LENGTH_LONG).show()
        }
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

            awaitingSystemResult = true
            huaweiAuthorizationLauncher.launch(syncViewModel.huaweiHealthManager.getAuthorizationIntent())
        } catch (e: Exception) {
            awaitingSystemResult = false
            AppLogger.e("MainActivity", "Huawei authorization start failed: ${e.message}", e)
            Toast.makeText(this, getString(R.string.toast_huawei_start_failed), Toast.LENGTH_LONG).show()
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
            awaitingSystemResult = true
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
                onDashboardRefresh = { dashboardViewModel.refreshFromCache() }
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
                onDashboardRefresh = { dashboardViewModel.refreshFromCache() }
            )
        }
    }
}