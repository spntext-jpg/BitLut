package com.openhealth.sync

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Dashboard
import androidx.compose.material.icons.rounded.FileOpen
import androidx.compose.material.icons.rounded.Sync
import androidx.compose.material.icons.rounded.Info
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.FloatingActionButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkInfo
import androidx.work.WorkManager
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.data.worker.SyncWorker
import com.openhealth.sync.platform.HmsCoreHelper
import com.openhealth.sync.ui.DashboardScreen
import com.openhealth.sync.ui.DashboardViewModel
import com.openhealth.sync.ui.ImportScreen
import com.openhealth.sync.ui.ImportViewModel
import com.openhealth.sync.ui.SyncUiState
import com.openhealth.sync.ui.SyncViewModel
import com.openhealth.sync.ui.onboarding.OnboardingScreen
import com.openhealth.sync.ui.theme.BitLutExpressiveTheme
import com.openhealth.sync.ui.theme.ElectricIndigo
import com.openhealth.sync.ui.theme.ElectricIndigoLt
import com.openhealth.sync.ui.theme.GlassCard
import com.openhealth.sync.ui.theme.GlowIndigo
import com.openhealth.sync.ui.theme.GlowMint
import com.openhealth.sync.ui.theme.MeshBackground
import com.openhealth.sync.ui.theme.NeonMint
import com.openhealth.sync.ui.theme.NeonRose
import com.openhealth.sync.ui.theme.PulsingGlowBorder
import com.openhealth.sync.ui.theme.TextPrimary
import com.openhealth.sync.ui.theme.TextSecondary
import com.openhealth.sync.ui.theme.TextTertiary
import com.openhealth.sync.ui.theme.Void
import com.openhealth.sync.ui.theme.VoidBorder
import com.openhealth.sync.ui.theme.VoidSurface
import com.openhealth.sync.util.AppLogger
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.delay

class MainActivity : ComponentActivity() {

    private val viewModel: SyncViewModel by viewModels {
        val app = application as SyncApplication
        SyncViewModel.provideFactory(app.container.googleHealthManager, app.container.huaweiHealthManager, this)
    }

    private val dashboardViewModel: DashboardViewModel by viewModels {
        val app = application as SyncApplication
        DashboardViewModel.provideFactory(app.container.googleHealthManager)
    }

    private val importViewModel: ImportViewModel by viewModels {
        val app = application as SyncApplication
        ImportViewModel.provideFactory(app.container.googleHealthManager, this)
    }

    private val googlePermissionLauncher = registerForActivityResult(
        PermissionController.createRequestPermissionResultContract()
    ) { granted ->
        AppLogger.i("MainActivity", "HC permissions returned: $granted")
        viewModel.refreshStatuses()
        if (!granted.containsAll(viewModel.googleManager.permissions)) {
            Toast.makeText(this, getString(R.string.toast_hc_no_permissions), Toast.LENGTH_LONG).show()
        }
    }

    private val huaweiAuthorizationLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        val success = viewModel.huaweiHealthManager.handleAuthorizationResult(
            resultCode = result.resultCode, data = result.data
        )
        viewModel.onHuaweiAuthorizationResult(success)
        viewModel.refreshStatuses()
        Toast.makeText(
            this,
            getString(if (success) R.string.toast_huawei_connected else R.string.toast_huawei_auth_returned),
            Toast.LENGTH_LONG
        ).show()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setupPeriodicSync()
        setContent {
            var showOnboarding by rememberSaveable { mutableStateOf(true) }
            BitLutExpressiveTheme {
                if (showOnboarding) {
                    OnboardingScreen(onContinue = { showOnboarding = false })
                    return@BitLutExpressiveTheme
                }
                val uiState by viewModel.uiState.collectAsState()
                Box(modifier = Modifier.fillMaxSize()) {
                    if (uiState.showImportScreen) {
                        ImportScreen(viewModel = importViewModel, onBack = { viewModel.hideImportScreen() })
                    } else {
                        BitLutNavHost(
                            uiState = uiState,
                            dashboardViewModel = dashboardViewModel,
                            onGoogleClick = { requestGooglePermissionsOrOpenProvider() },
                            onHuaweiClick = { requestHuaweiAuthorizationOrInstallHms() },
                            onSyncClick = { triggerImmediateSync() },
                            onImportClick = { viewModel.showImportScreen() }
                        )
                    }
                }
            }
        }
    }

    override fun onResume() { super.onResume(); viewModel.refreshStatuses() }

    private fun requestGooglePermissionsOrOpenProvider() {
        val status = HealthConnectClient.getSdkStatus(this)
        if (status == HealthConnectClient.SDK_AVAILABLE) {
            Toast.makeText(this, getString(R.string.toast_hc_opening), Toast.LENGTH_SHORT).show()
            googlePermissionLauncher.launch(viewModel.googleManager.permissions)
        } else {
            Toast.makeText(this, getString(R.string.toast_hc_required), Toast.LENGTH_LONG).show()
            openUriWithFallback(
                "market://details?id=com.google.android.apps.healthdata",
                "https://play.google.com/store/apps/details?id=com.google.android.apps.healthdata"
            )
        }
    }

    private fun requestHuaweiAuthorizationOrInstallHms() {
        if (!HuaweiConfig.hasDeveloperAppId()) {
            Toast.makeText(this, getString(R.string.toast_huawei_app_id_missing), Toast.LENGTH_LONG).show()
            return
        }
        if (!HmsCoreHelper.isInstalled(this)) {
            Toast.makeText(this, getString(R.string.toast_huawei_hms_missing), Toast.LENGTH_LONG).show()
            HmsCoreHelper.openInstallPage(this); return
        }
        if (!HmsCoreHelper.isHuaweiHealthInstalled(this)) {
            Toast.makeText(this, getString(R.string.toast_huawei_health_missing), Toast.LENGTH_LONG).show()
            HmsCoreHelper.openHuaweiHealth(this); return
        }
        runCatching {
            Toast.makeText(this, getString(R.string.toast_huawei_opening_auth), Toast.LENGTH_SHORT).show()
            huaweiAuthorizationLauncher.launch(viewModel.huaweiHealthManager.getAuthorizationIntent())
        }.onFailure {
            Toast.makeText(this, getString(R.string.toast_huawei_auth_failed), Toast.LENGTH_LONG).show()
            HmsCoreHelper.openHuaweiHealth(this)
        }
    }

    private fun triggerImmediateSync() {
        viewModel.markSyncStarted()
        val req = OneTimeWorkRequestBuilder<SyncWorker>()
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .build()
        val wm = WorkManager.getInstance(applicationContext)
        wm.enqueueUniqueWork("BitLutManualSync", ExistingWorkPolicy.KEEP, req)
        wm.getWorkInfoByIdLiveData(req.id).observe(this) { info ->
            if (info?.state?.isFinished == true)
                viewModel.markSyncCompleted(info.state == WorkInfo.State.SUCCEEDED)
        }
    }

    private fun setupPeriodicSync() {
        WorkManager.getInstance(applicationContext).enqueueUniquePeriodicWork(
            HuaweiConfig.SYNC_WORKER_TAG, ExistingPeriodicWorkPolicy.KEEP,
            PeriodicWorkRequestBuilder<SyncWorker>(1, TimeUnit.HOURS)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .build()
        )
    }

    private fun openUriWithFallback(primary: String, fallback: String) {
        runCatching { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(primary))) }
            .onFailure { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(fallback))) }
    }
}

// ── Status resolvers ──────────────────────────────────────────────────────────

@Composable
private fun resolveSyncStatus(key: String): String = when (key) {
    "sync_status_idle"    -> stringResource(R.string.sync_status_idle)
    "sync_status_syncing" -> stringResource(R.string.sync_status_syncing)
    "sync_status_success" -> stringResource(R.string.sync_status_success)
    "sync_status_error"   -> stringResource(R.string.sync_status_error)
    else -> key
}

@Composable
private fun resolveLastSync(key: String): String =
    if (key == "sync_no_data") stringResource(R.string.sync_no_data) else key

// ── Main layout ───────────────────────────────────────────────────────────────

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainExpressiveLayout(
    uiState: SyncUiState,
    onGoogleClick: () -> Unit,
    onHuaweiClick: () -> Unit,
    onSyncClick: () -> Unit,
    onImportClick: () -> Unit
) {
    var showLogs by remember { mutableStateOf(false) }
    var contentVisible by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { delay(80); contentVisible = true }
    val contentAlpha by animateFloatAsState(
        targetValue = if (contentVisible) 1f else 0f,
        animationSpec = tween(600, easing = FastOutSlowInEasing),
        label = "contentAlpha"
    )

    if (showLogs) { LogsDialog(onDismiss = { showLogs = false }) }

    Box(modifier = Modifier.fillMaxSize()) {
        MeshBackground()
        Scaffold(
            containerColor = Color.Transparent,
            topBar = {
                TopAppBar(
                    title = {
                        Text(
                            text = stringResource(R.string.app_bar_title),
                            fontWeight = FontWeight.Black,
                            fontSize = 20.sp,
                            color = TextPrimary,
                            letterSpacing = (-0.5).sp
                        )
                    },
                    actions = {
                        IconButton(onClick = { showLogs = true }) {
                            Icon(Icons.Rounded.Info, contentDescription = null, tint = TextSecondary)
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent)
                )
            },
            floatingActionButton = {
                FloatingActionButton(
                    onClick = onSyncClick,
                    containerColor = Color.Transparent,
                    contentColor = Color.White,
                    elevation = FloatingActionButtonDefaults.elevation(0.dp, 0.dp),
                    modifier = Modifier
                        .clip(RoundedCornerShape(20.dp))
                        .background(Brush.linearGradient(listOf(ElectricIndigo, ElectricIndigoLt)))
                ) {
                    Icon(Icons.Rounded.Refresh, contentDescription = null)
                }
            }
        ) { padding ->
            Column(
                modifier = Modifier
                    .padding(padding)
                    .fillMaxSize()
                    .alpha(contentAlpha)
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 20.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                Spacer(Modifier.height(4.dp))

                // Status hero
                GlassCard(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(28.dp),
                    glowColor = if (uiState.syncStatus == "sync_status_success") GlowMint else GlowIndigo
                ) {
                    Column(modifier = Modifier.padding(24.dp)) {
                        Text(
                            text = stringResource(R.string.sync_section_title),
                            fontSize = 12.sp, fontWeight = FontWeight.SemiBold,
                            color = ElectricIndigoLt, letterSpacing = 1.sp
                        )
                        Spacer(Modifier.height(6.dp))
                        Text(
                            text = resolveSyncStatus(uiState.syncStatus),
                            fontSize = 28.sp, fontWeight = FontWeight.Black,
                            color = TextPrimary, letterSpacing = (-1).sp
                        )
                        Spacer(Modifier.height(4.dp))
                        Text(
                            text = stringResource(R.string.sync_last_success, resolveLastSync(uiState.lastSyncTime)),
                            fontSize = 13.sp, color = TextTertiary
                        )
                    }
                }

                Text(
                    text = stringResource(R.string.sync_sources_title),
                    fontSize = 13.sp, fontWeight = FontWeight.SemiBold,
                    color = TextSecondary, letterSpacing = 0.8.sp,
                    modifier = Modifier.padding(horizontal = 4.dp, vertical = 4.dp)
                )

                // Google Health card
                if (uiState.hasGooglePermissions) {
                    PulsingGlowBorder(
                        color = NeonMint,
                        shape = RoundedCornerShape(24.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        SourceCardContent(
                            emoji = "🟢",
                            title = stringResource(R.string.google_card_title),
                            status = stringResource(R.string.google_status_connected),
                            statusColor = NeonMint,
                            buttonText = stringResource(R.string.google_button_connected),
                            onClick = {}
                        )
                    }
                } else {
                    GlassCard(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(24.dp)) {
                        SourceCardContent(
                            emoji = "⚪",
                            title = stringResource(R.string.google_card_title),
                            status = if (!uiState.isGoogleAvailable)
                                stringResource(R.string.google_status_not_ready)
                            else
                                stringResource(R.string.google_status_needs_access),
                            statusColor = TextSecondary,
                            buttonText = stringResource(R.string.google_button_connect),
                            onClick = onGoogleClick
                        )
                    }
                }

                // Huawei Health card
                GlassCard(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(24.dp)) {
                    SourceCardContent(
                        emoji = if (uiState.isHuaweiAuthorized) "🟣" else "🔴",
                        title = stringResource(R.string.huawei_card_title),
                        status = if (uiState.isHuaweiAuthorized)
                            stringResource(R.string.huawei_status_connected)
                        else
                            stringResource(R.string.huawei_status_pending),
                        statusColor = if (uiState.isHuaweiAuthorized) ElectricIndigoLt else NeonRose,
                        buttonText = if (uiState.isHuaweiAuthorized)
                            stringResource(R.string.huawei_button_refresh)
                        else
                            stringResource(R.string.huawei_button_check),
                        onClick = onHuaweiClick
                    )
                }

                // Huawei pending info
                if (!uiState.isHuaweiAuthorized) {
                    GlassCard(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(20.dp),
                        glowColor = Color(0x22F43F5E)
                    ) {
                        Column(modifier = Modifier.padding(20.dp)) {
                            Text(
                                text = stringResource(R.string.huawei_approval_title),
                                fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary
                            )
                            Spacer(Modifier.height(8.dp))
                            Text(
                                text = stringResource(R.string.huawei_approval_body),
                                fontSize = 13.sp, color = TextSecondary, lineHeight = 19.sp
                            )
                            Spacer(Modifier.height(8.dp))
                            Text(
                                text = stringResource(R.string.huawei_approval_action),
                                fontSize = 13.sp, color = TextSecondary, lineHeight = 19.sp
                            )
                        }
                    }
                }

                // Import button
                GlassCard(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(20.dp)) {
                    Row(
                        modifier = Modifier
                            .clickable(
                                interactionSource = remember { MutableInteractionSource() },
                                indication = null,
                                onClick = onImportClick
                            )
                            .padding(horizontal = 20.dp, vertical = 16.dp)
                            .fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "📦  " + stringResource(R.string.sync_import_button),
                            fontSize = 14.sp, fontWeight = FontWeight.Medium, color = TextPrimary,
                            modifier = Modifier.weight(1f)
                        )
                        Spacer(Modifier.width(12.dp))
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(12.dp))
                                .background(
                                    Brush.linearGradient(
                                        listOf(ElectricIndigo.copy(alpha = 0.3f), ElectricIndigoLt.copy(alpha = 0.2f))
                                    )
                                )
                                .border(1.dp, ElectricIndigo.copy(alpha = 0.4f), RoundedCornerShape(12.dp))
                                .padding(10.dp)
                        ) {
                            Icon(Icons.Rounded.FileOpen, contentDescription = null, tint = ElectricIndigoLt)
                        }
                    }
                }

                Spacer(Modifier.height(88.dp))
            }
        }
    }
}

// ── Source card content ───────────────────────────────────────────────────────

@Composable
private fun SourceCardContent(
    emoji: String,
    title: String,
    status: String,
    statusColor: Color,
    buttonText: String,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier.padding(20.dp).fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.weight(1f)
        ) {
            Text(emoji, fontSize = 20.sp)
            Column {
                Text(title, fontSize = 15.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
                Text(status, fontSize = 12.sp, color = statusColor)
            }
        }
        Box(
            modifier = Modifier
                .clip(RoundedCornerShape(12.dp))
                .background(
                    Brush.linearGradient(
                        listOf(ElectricIndigo.copy(alpha = 0.25f), ElectricIndigoLt.copy(alpha = 0.15f))
                    )
                )
                .border(1.dp, ElectricIndigo.copy(alpha = 0.35f), RoundedCornerShape(12.dp))
                .clickable(
                    interactionSource = remember { MutableInteractionSource() },
                    indication = null,
                    onClick = onClick
                )
                .padding(horizontal = 14.dp, vertical = 8.dp)
        ) {
            Text(buttonText, fontSize = 13.sp, fontWeight = FontWeight.Medium, color = ElectricIndigoLt)
        }
    }
}

// ── Logs dialog ───────────────────────────────────────────────────────────────

@Composable
private fun LogsDialog(onDismiss: () -> Unit) {
    val context = LocalContext.current
    val logs by AppLogger.logs.collectAsState()
    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = VoidSurface,
        titleContentColor = TextPrimary,
        textContentColor = TextSecondary,
        title = { Text(stringResource(R.string.logs_title), fontWeight = FontWeight.Bold) },
        text = {
            LazyColumn(modifier = Modifier.fillMaxWidth().height(340.dp)) {
                items(logs) { log ->
                    Text(log, fontSize = 11.sp, modifier = Modifier.padding(vertical = 3.dp), color = TextSecondary)
                    HorizontalDivider(color = VoidBorder)
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text(stringResource(R.string.logs_close), color = ElectricIndigoLt)
            }
        },
        dismissButton = {
            TextButton(onClick = {
                val text = logs.joinToString("\n")
                val cb = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                cb.setPrimaryClip(ClipData.newPlainText("BitLut logs", text))
                Toast.makeText(context, context.getString(R.string.logs_copied), Toast.LENGTH_SHORT).show()
            }) {
                Text(stringResource(R.string.logs_copy), color = TextSecondary)
            }
        }
    )
}

// ── Bottom nav host ───────────────────────────────────────────────────────────

@Composable
private fun BitLutNavHost(
    uiState: SyncUiState,
    dashboardViewModel: DashboardViewModel,
    onGoogleClick: () -> Unit,
    onHuaweiClick: () -> Unit,
    onSyncClick: () -> Unit,
    onImportClick: () -> Unit
) {
    var selectedTab by remember { mutableStateOf(0) }

    Box(modifier = Modifier.fillMaxSize()) {
        MeshBackground()

        androidx.compose.material3.Scaffold(
            containerColor = Color.Transparent,
            bottomBar = {
                BitLutBottomNav(
                    selected = selectedTab,
                    onSelect = { selectedTab = it }
                )
            }
        ) { padding ->
            Box(modifier = Modifier.padding(padding).fillMaxSize()) {
                when (selectedTab) {
                    0 -> DashboardScreen(viewModel = dashboardViewModel)
                    1 -> MainExpressiveLayout(
                        uiState = uiState,
                        onGoogleClick = onGoogleClick,
                        onHuaweiClick = onHuaweiClick,
                        onSyncClick = onSyncClick,
                        onImportClick = onImportClick
                    )
                }
            }
        }
    }
}

@Composable
private fun BitLutBottomNav(selected: Int, onSelect: (Int) -> Unit) {
    NavigationBar(
        containerColor = Color(0xCC0C0C1E),
        contentColor = com.openhealth.sync.ui.theme.TextSecondary,
        tonalElevation = 0.dp,
        modifier = Modifier
            .selectableGroup()
    ) {
        NavigationBarItem(
            selected = selected == 0,
            onClick = { onSelect(0) },
            icon = { Icon(Icons.Rounded.Dashboard, contentDescription = null) },
            label = { Text("Dashboard", fontSize = 11.sp) },
            colors = androidx.compose.material3.NavigationBarItemDefaults.colors(
                selectedIconColor = com.openhealth.sync.ui.theme.NeonMint,
                selectedTextColor = com.openhealth.sync.ui.theme.NeonMint,
                unselectedIconColor = com.openhealth.sync.ui.theme.TextTertiary,
                unselectedTextColor = com.openhealth.sync.ui.theme.TextTertiary,
                indicatorColor = com.openhealth.sync.ui.theme.ElectricIndigo.copy(alpha = 0.15f)
            )
        )
        NavigationBarItem(
            selected = selected == 1,
            onClick = { onSelect(1) },
            icon = { Icon(Icons.Rounded.Sync, contentDescription = null) },
            label = { Text("Sync", fontSize = 11.sp) },
            colors = androidx.compose.material3.NavigationBarItemDefaults.colors(
                selectedIconColor = com.openhealth.sync.ui.theme.NeonMint,
                selectedTextColor = com.openhealth.sync.ui.theme.NeonMint,
                unselectedIconColor = com.openhealth.sync.ui.theme.TextTertiary,
                unselectedTextColor = com.openhealth.sync.ui.theme.TextTertiary,
                indicatorColor = com.openhealth.sync.ui.theme.ElectricIndigo.copy(alpha = 0.15f)
            )
        )
    }
}
