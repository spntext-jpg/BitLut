package com.openhealth.sync

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Info
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SmallFloatingActionButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
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
import com.openhealth.sync.ui.SyncUiState
import com.openhealth.sync.ui.SyncViewModel
import com.openhealth.sync.ui.theme.BitLutExpressiveTheme
import com.openhealth.sync.ui.onboarding.OnboardingScreen
import com.openhealth.sync.util.AppLogger
import java.util.concurrent.TimeUnit

class MainActivity : ComponentActivity() {

    private val viewModel: SyncViewModel by viewModels {
        val app = application as SyncApplication
        SyncViewModel.provideFactory(
            app.container.googleHealthManager,
            app.container.huaweiHealthManager,
            this
        )
    }

    private val googlePermissionLauncher = registerForActivityResult(
        PermissionController.createRequestPermissionResultContract()
    ) { granted ->
        AppLogger.i("MainActivity", "Returned from Health Connect permission request: $granted")
        viewModel.refreshStatuses()

        val required = viewModel.googleManager.permissions
        if (!granted.containsAll(required)) {
            AppLogger.w("MainActivity", "Health Connect permissions were not granted")
            Toast.makeText(
                this,
                "Health Connect не выдал разрешения. Нажмите Google Health ещё раз и разрешите доступ BitLut.",
                Toast.LENGTH_LONG
            ).show()
        }
    }

    private val huaweiAuthorizationLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        AppLogger.i(
            "MainActivity",
            "Huawei authorization returned resultCode=${result.resultCode} hasData=${result.data != null}"
        )

        val success = viewModel.huaweiHealthManager.handleAuthorizationResult(
            resultCode = result.resultCode,
            data = result.data
        )

        viewModel.onHuaweiAuthorizationResult(success)
        viewModel.refreshStatuses()

        if (success) {
            Toast.makeText(this, "Huawei Health подключен. Можно запускать синхронизацию.", Toast.LENGTH_LONG).show()
        } else {
            Toast.makeText(
                this,
                "Huawei authorization returned. Sync will verify real API access.",
                Toast.LENGTH_LONG
            ).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setupPeriodicSync()

        setContent {

            var showOnboarding by rememberSaveable {
                mutableStateOf(true)
            }


            BitLutExpressiveTheme {

                if (showOnboarding) {
                    OnboardingScreen(
                        onContinue = {
                            showOnboarding = false
                        }
                    )
                    return@BitLutExpressiveTheme
                }

                val uiState by viewModel.uiState.collectAsState()
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    MainExpressiveLayout(
                        uiState = uiState,
                        onGoogleClick = { requestGooglePermissionsOrOpenProvider() },
                        onHuaweiClick = { requestHuaweiAuthorizationOrInstallHms() },
                        onSyncClick = { triggerImmediateSync() }
                    )
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        viewModel.refreshStatuses()
    }

    private fun requestGooglePermissionsOrOpenProvider() {
        val status = HealthConnectClient.getSdkStatus(this)
        AppLogger.i("MainActivity", "Health Connect SDK status before permission request: $status")

        if (status == HealthConnectClient.SDK_AVAILABLE) {
            val permissions = viewModel.googleManager.permissions
            AppLogger.i("MainActivity", "Opening Health Connect permission screen for: $permissions")
            Toast.makeText(this, "Открываю запрос разрешений Health Connect", Toast.LENGTH_SHORT).show()
            googlePermissionLauncher.launch(permissions)
            return
        }

        AppLogger.w("MainActivity", "Health Connect is not available; opening provider page")
        Toast.makeText(this, "Health Connect is required. Opening install page.", Toast.LENGTH_LONG).show()
        openHealthConnectInstallPage()
    }

    private fun openHealthConnectManagement() {
        val intents = listOf(
            Intent("android.health.connect.action.MANAGE_HEALTH_PERMISSIONS").apply {
                putExtra(Intent.EXTRA_PACKAGE_NAME, packageName)
            },
            Intent("androidx.health.ACTION_HEALTH_CONNECT_SETTINGS"),
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                data = Uri.parse("package:com.google.android.apps.healthdata")
            }
        )

        for (intent in intents) {
            try {
                startActivity(intent)
                AppLogger.i("MainActivity", "Opened Health Connect management/settings")
                return
            } catch (e: Exception) {
                AppLogger.w("MainActivity", "Health Connect management fallback failed: ${e.message}")
            }
        }

        openHealthConnectInstallPage()
    }

    private fun openHealthConnectInstallPage() {
        openUriWithFallback(
            primary = "market://details?id=com.google.android.apps.healthdata",
            fallback = "https://play.google.com/store/apps/details?id=com.google.android.apps.healthdata"
        )
    }

    private fun requestHuaweiAuthorizationOrInstallHms() {
        if (!HuaweiConfig.hasDeveloperAppId()) {
            AppLogger.e("MainActivity", "Huawei App ID is not configured")
            Toast.makeText(this, "Huawei App ID is not configured.", Toast.LENGTH_LONG).show()
            return
        }

        AppLogger.i(
            "MainActivity",
            "Huawei authorization preflight: ${HmsCoreHelper.prerequisiteStatus(this)}"
        )

        if (!HmsCoreHelper.isInstalled(this)) {
            AppLogger.e("MainActivity", "Cannot start Huawei authorization: HMS Core is missing")
            Toast.makeText(
                this,
                "Install or update HMS Core first, then return to BitLut.",
                Toast.LENGTH_LONG
            ).show()
            HmsCoreHelper.openHmsCoreInstall(this)
            return
        }

        if (!HmsCoreHelper.isHuaweiHealthInstalled(this)) {
            AppLogger.e("MainActivity", "Cannot start Huawei authorization: Huawei Health is missing")
            Toast.makeText(
                this,
                "Install Huawei Health first, sign in, then return to BitLut.",
                Toast.LENGTH_LONG
            ).show()
            HmsCoreHelper.openHuaweiHealth(this)
            return
        }

        runCatching {
            val intent = viewModel.huaweiHealthManager.getAuthorizationIntent()

            if (!HmsCoreHelper.canResolveIntent(this, intent)) {
                AppLogger.e(
                    "MainActivity",
                    "Huawei authorization intent cannot be resolved. ${HmsCoreHelper.prerequisiteStatus(this)}"
                )
                Toast.makeText(
                    this,
                    "Huawei authorization screen is unavailable. Update HMS Core, Huawei Health and AppGallery.",
                    Toast.LENGTH_LONG
                ).show()

                if (!HmsCoreHelper.isAppGalleryInstalled(this)) {
                    HmsCoreHelper.openAppGallery(this)
                } else {
                    HmsCoreHelper.openHuaweiHealth(this)
                }
                return
            }

            AppLogger.i(
                "MainActivity",
                "Launching Huawei authorization for ${viewModel.huaweiHealthManager.requestedScopeNames()}"
            )
            Toast.makeText(this, "Opening Huawei Health authorization", Toast.LENGTH_SHORT).show()
            huaweiAuthorizationLauncher.launch(intent)
        }.onFailure { error ->
            AppLogger.e("MainActivity", "Cannot start Huawei Health authorization", error)
            Toast.makeText(
                this,
                "Huawei Health authorization could not be opened. Update HMS Core and Huawei Health, then try again.",
                Toast.LENGTH_LONG
            ).show()

            if (HmsCoreHelper.isHuaweiHealthInstalled(this)) {
                HmsCoreHelper.openHuaweiHealth(this)
            } else {
                HmsCoreHelper.openInstallPage(this)
            }
        }
    }

    private fun triggerImmediateSync() {
        viewModel.markSyncStarted()

        val req = OneTimeWorkRequestBuilder<SyncWorker>()
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .build()

        val wm = WorkManager.getInstance(applicationContext)
        wm.enqueueUniqueWork(
            "BitLutManualSync",
            ExistingWorkPolicy.KEEP,
            req
        )
        wm.getWorkInfoByIdLiveData(req.id).observe(this) { info ->
            if (info?.state?.isFinished == true) {
                viewModel.markSyncCompleted(info.state == WorkInfo.State.SUCCEEDED)
            }
        }
    }

    private fun setupPeriodicSync() {
        WorkManager.getInstance(applicationContext).enqueueUniquePeriodicWork(
            HuaweiConfig.SYNC_WORKER_TAG,
            ExistingPeriodicWorkPolicy.KEEP,
            PeriodicWorkRequestBuilder<SyncWorker>(1, TimeUnit.HOURS)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .build()
        )
    }

    private fun openUriWithFallback(primary: String, fallback: String) {
        runCatching {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(primary)))
        }.onFailure {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(fallback)))
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainExpressiveLayout(
    uiState: SyncUiState,
    onGoogleClick: () -> Unit,
    onHuaweiClick: () -> Unit,
    onSyncClick: () -> Unit
) {
    var showLogs by remember { mutableStateOf(false) }
    val context = LocalContext.current

    if (showLogs) {
        val logs by AppLogger.logs.collectAsState()
        AlertDialog(
            onDismissRequest = { showLogs = false },
            title = { Text("Системные логи") },
            text = {
                LazyColumn(modifier = Modifier.fillMaxWidth().height(340.dp)) {
                    items(logs) { log ->
                        Text(log, fontSize = 12.sp, modifier = Modifier.padding(vertical = 4.dp))
                        HorizontalDivider()
                    }
                }
            },
            confirmButton = { TextButton(onClick = { showLogs = false }) { Text("Закрыть") } },
            dismissButton = {
                TextButton(onClick = {
                    val text = logs.joinToString(separator = "\n")
                    val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                    clipboard.setPrimaryClip(ClipData.newPlainText("BitLut logs", text))
                    Toast.makeText(context, "Логи скопированы", Toast.LENGTH_SHORT).show()
                }) { Text("Копировать") }
            }
        )
    }

    Scaffold(
        topBar = { TopAppBar(title = { Text("BitLut Health", fontWeight = FontWeight.Black) }) },
        floatingActionButton = {
            Column(horizontalAlignment = Alignment.End) {
                SmallFloatingActionButton(
                    onClick = { showLogs = true },
                    containerColor = MaterialTheme.colorScheme.secondaryContainer,
                    modifier = Modifier.padding(bottom = 12.dp)
                ) { Icon(Icons.Rounded.Info, contentDescription = "Logs") }

                FloatingActionButton(
                    onClick = onSyncClick,
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                ) { Icon(Icons.Rounded.Refresh, contentDescription = "Sync") }
            }
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Spacer(Modifier.height(8.dp))

            Card(shape = RoundedCornerShape(28.dp), modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(24.dp)) {
                    Text("Синхронизация", style = MaterialTheme.typography.labelLarge)
                    Text(uiState.syncStatus, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                    Text("Последняя успешная: ${uiState.lastSyncTime}", style = MaterialTheme.typography.bodySmall)
                }
            }

            Text("Источники данных", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(top = 16.dp))

            SourceCard(
                title = "Google Health Connect",
                status = when {
                    !uiState.isGoogleAvailable -> "Health Connect не готов"
                    uiState.hasGooglePermissions -> "Подключено"
                    else -> "Требуется доступ"
                },
                buttonText = if (uiState.hasGooglePermissions) "Подключено" else "Связать",
                onClick = {
                    if (!uiState.hasGooglePermissions) {
                        onGoogleClick()
                    }
                }
            )

            SourceCard(
                title = "Huawei Health",
                status = if (uiState.isHuaweiAuthorized) "Подключено" else "Ожидает разрешения Huawei",
                buttonText = if (uiState.isHuaweiAuthorized) "Обновить" else "Проверить доступ",
                onClick = onHuaweiClick
            )

            if (!uiState.isHuaweiAuthorized) {
                HuaweiApprovalInfoCard()
            }

            Button(
                onClick = onSyncClick,
                enabled = !uiState.isSyncing && uiState.hasGooglePermissions,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(if (uiState.isSyncing) "Синхронизация..." else "Синхронизировать сейчас")
            }
        }
    }
}


@Composable
private fun HuaweiApprovalInfoCard() {
    Card(
        shape = RoundedCornerShape(24.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(
                "Huawei Health: доступ на проверке",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            Text(
                "BitLut уже настроен для Huawei Health Kit, но Huawei отдельно проверяет доступ к данным здоровья. Пока заявка на Health Service Kit находится на ручной проверке, авторизация может возвращать ошибки 50005 или 50011.",
                style = MaterialTheme.typography.bodyMedium
            )
            Text(
                "Что можно сделать сейчас: откройте Huawei Health, войдите в тот же Huawei ID, примите настройки конфиденциальности Health Kit и повторите попытку позже.",
                style = MaterialTheme.typography.bodyMedium
            )
        }
    }
}

@Composable
private fun SourceCard(
    title: String,
    status: String,
    buttonText: String,
    onClick: () -> Unit
) {
    Card(shape = RoundedCornerShape(20.dp), modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.padding(20.dp).fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text(status, style = MaterialTheme.typography.bodyMedium)
            }
            Button(onClick = onClick) { Text(buttonText) }
        }
    }
}

