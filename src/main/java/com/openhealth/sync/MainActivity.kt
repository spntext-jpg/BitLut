package com.openhealth.sync

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.work.*
import com.openhealth.sync.data.config.HuaweiConfig
import com.openhealth.sync.data.worker.SyncWorker
import com.openhealth.sync.ui.SyncUiState
import com.openhealth.sync.ui.SyncViewModel
import com.openhealth.sync.ui.ThemeScreen
import java.util.concurrent.TimeUnit

class MainActivity : ComponentActivity() {
    private val viewModel: SyncViewModel by viewModels {
        val app = application as SyncApplication
        SyncViewModel.provideFactory(
            app.container.googleHealthManager,
            app.container.huaweiAuthManager,
            this
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setupPeriodicSync()

        setContent {
            ThemeScreen {
                val uiState by viewModel.uiState.collectAsState()
                
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    MainExpressiveLayout(
                        uiState = uiState,
                        onGoogleClick = { requestGooglePermissions() },
                        onHuaweiClick = { startHuaweiAuth() },
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

    private fun requestGooglePermissions() {
        Toast.makeText(this, "Переход в Health Connect...", Toast.LENGTH_SHORT).show()
    }

    private fun startHuaweiAuth() {
        val authUrl = "${HuaweiConfig.OAUTH_URL}?response_type=code&client_id=${HuaweiConfig.CLIENT_ID}&redirect_uri=${HuaweiConfig.REDIRECT_URI}&scope=${HuaweiConfig.SCOPE}"
        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(authUrl)))
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
            HuaweiConfig.SYNC_WORKER_TAG, ExistingPeriodicWorkPolicy.KEEP,
            PeriodicWorkRequestBuilder<SyncWorker>(1, TimeUnit.HOURS).build()
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
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("BitLut", fontWeight = FontWeight.Black) },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)
            )
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

            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHighest),
                shape = RoundedCornerShape(28.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .animateContentSize(spring(stiffness = Spring.StiffnessMediumLow))
                ) {
                Column(Modifier.padding(24.dp)) {
                    Text("Синхронизация", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Spacer(Modifier.height(4.dp))
                    Text(uiState.syncStatus, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                    Spacer(Modifier.height(8.dp))
                    Text("Последняя успешная: ${uiState.lastSyncTime}", style = MaterialTheme.typography.bodySmall)
                }
            }

            Text("Источники данных", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(top = 16.dp))

            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
                shape = RoundedCornerShape(20.dp)
            ) {
                Row(
                    modifier = Modifier.padding(20.dp).fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text("Google Health", style = MaterialTheme.typography.titleMedium)
                        Text(if (uiState.hasGooglePermissions) "Подключено" else "Требуется доступ", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    FilledTonalButton(onClick = onGoogleClick) {
                        Text(if (uiState.hasGooglePermissions) "Обновить" else "Связать")
                    }
                }
            }

            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
                shape = RoundedCornerShape(20.dp)
            ) {
                Row(
                    modifier = Modifier.padding(20.dp).fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text("Huawei Health", style = MaterialTheme.typography.titleMedium)
                        Text(if (uiState.isHuaweiAuthorized) "Авторизован" else "Не авторизован", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    FilledTonalButton(onClick = onHuaweiClick) {
                        Text(if (uiState.isHuaweiAuthorized) "Аккаунт" else "Войти")
                    }
                }
            }

            Spacer(Modifier.weight(1f))

            FloatingActionButton(
                onClick = onSyncClick,
                containerColor = MaterialTheme.colorScheme.primaryContainer,
                modifier = Modifier.align(Alignment.End).padding(bottom = 24.dp)
            ) {
                Icon(Icons.Rounded.Refresh, contentDescription = "Sync Now")
            }
        }
    }
}
