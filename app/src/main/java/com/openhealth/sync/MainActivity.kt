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
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
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
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkInfo
import androidx.work.WorkManager
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.data.worker.SyncWorker
import com.openhealth.sync.ui.SyncUiState
import com.openhealth.sync.ui.SyncViewModel
import com.openhealth.sync.util.AppLogger
import java.util.concurrent.TimeUnit
import com.openhealth.sync.platform.HmsCoreHelper
import com.openhealth.sync.ui.theme.BitLutExpressiveTheme

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
    ) {
        viewModel.refreshStatuses()
    }

    private val huaweiAuthorizationLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        val success = viewModel.huaweiHealthManager.handleAuthorizationResult(result.data)
        viewModel.onHuaweiAuthorizationResult(success)
        viewModel.refreshStatuses()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setupPeriodicSync()
        setContent {
            BitLutExpressiveTheme {
                val uiState by viewModel.uiState.collectAsState()
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    MainExpressiveLayout(
                        uiState = uiState,
                        onGoogleClick = { requestGooglePermissionsOrOpenProvider() },
                        onHuaweiClick = { requestHuaweiAuthorization() },
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
        if (HealthConnectClient.getSdkStatus(this) == HealthConnectClient.SDK_AVAILABLE) {
            googlePermissionLauncher.launch(viewModel.googleManager.permissions)
            return
        }

        val uri = Uri.parse("market://details?id=com.google.android.apps.healthdata")
        runCatching { startActivity(Intent(Intent.ACTION_VIEW, uri)) }
            .onFailure {
                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://play.google.com/store/apps/details?id=com.google.android.apps.healthdata")))
            }
    }

    private fun requestHuaweiAuthorization() {
        if (!HuaweiConfig.hasDeveloperAppId()) {
            Toast.makeText(this, "Заполните HUAWEI_APP_ID в .huawei.env и пересоберите приложение", Toast.LENGTH_LONG).show()
        }
        runCatching {
            huaweiAuthorizationLauncher.launch(viewModel.huaweiHealthManager.getAuthorizationIntent())
        }.onFailure { error ->
            AppLogger.e("MainActivity", "Cannot start Huawei authorization", error)
            Toast.makeText(this, "Не удалось открыть Huawei Health authorization", Toast.LENGTH_LONG).show()
        }
    }

    private fun triggerImmediateSync() {
        viewModel.markSyncStarted()
        val req = OneTimeWorkRequestBuilder<SyncWorker>()
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .build()
        val wm = WorkManager.getInstance(applicationContext)
        wm.enqueue(req)
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
            confirmButton = {
                TextButton(onClick = { showLogs = false }) { Text("Закрыть") }
            },
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
                ) { Icon(Icons.Rounded.Info, "Logs") }

                FloatingActionButton(
                    onClick = onSyncClick,
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                ) { Icon(Icons.Rounded.Refresh, "Sync") }
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
                buttonText = if (uiState.hasGooglePermissions) "Обновить" else "Связать",
                onClick = onGoogleClick
            )

            SourceCard(
                title = "Huawei Health",
                status = if (uiState.isHuaweiAuthorized) "Подключено" else "Требуется доступ",
                buttonText = if (uiState.isHuaweiAuthorized) "Обновить" else "Связать",
                onClick = onHuaweiClick
            )

            Button(
                onClick = onSyncClick,
                enabled = !uiState.isSyncing && uiState.hasGooglePermissions && uiState.isHuaweiAuthorized,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(if (uiState.isSyncing) "Синхронизация..." else "Синхронизировать сейчас")
            }
        }
    }
}

@Composable
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
                Text(title, style = MaterialTheme.typography.titleMedium)
                Text(status, style = MaterialTheme.typography.bodyMedium)
            }
            Button(onClick = onClick) { Text(buttonText) }
        }
    }


}

// 1.0.1 UX copy: Install or update HMS Core to authorize Huawei Health.
