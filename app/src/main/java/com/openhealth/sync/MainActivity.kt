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
import com.openhealth.sync.data.worker.SyncWorker
import com.openhealth.sync.ui.SyncUiState
import com.openhealth.sync.ui.SyncViewModel
import java.util.concurrent.TimeUnit

// Local fallback for missing HuaweiConfig
object LocalConfig {
    const val OAUTH_URL = "https://oauth-login.cloud.huawei.com/oauth2/v3/authorize"
    const val CLIENT_ID = "DEFAULT_CLIENT_ID"
    const val REDIRECT_URI = "DEFAULT_REDIRECT_URI"
    const val SCOPE = "https://www.huawei.com/health/healthkit.read"
    const val SYNC_WORKER_TAG = "sync_worker"
}

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
            MaterialTheme { // Replaced missing ThemeScreen with standard MaterialTheme
                val uiState by viewModel.uiState.collectAsState()
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
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
        val authUrl = "${LocalConfig.OAUTH_URL}?response_type=code&client_id=${LocalConfig.CLIENT_ID}&redirect_uri=${LocalConfig.REDIRECT_URI}&scope=${LocalConfig.SCOPE}"
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
            LocalConfig.SYNC_WORKER_TAG, ExistingPeriodicWorkPolicy.KEEP,
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
        topBar = { TopAppBar(title = { Text("BitLut", fontWeight = FontWeight.Black) }) }
    ) { padding ->
        Column(
            modifier = Modifier.padding(padding).fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 24.dp),
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
            Card(shape = RoundedCornerShape(20.dp)) {
                Row(modifier = Modifier.padding(20.dp).fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Column {
                        Text("Google Health", style = MaterialTheme.typography.titleMedium)
                        Text(if (uiState.hasGooglePermissions) "Подключено" else "Требуется доступ", style = MaterialTheme.typography.bodyMedium)
                    }
                    Button(onClick = onGoogleClick) { Text(if (uiState.hasGooglePermissions) "Обновить" else "Связать") }
                }
            }
            Card(shape = RoundedCornerShape(20.dp)) {
                Row(modifier = Modifier.padding(20.dp).fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Column {
                        Text("Huawei Health", style = MaterialTheme.typography.titleMedium)
                        Text(if (uiState.isHuaweiAuthorized) "Авторизован" else "Не авторизован", style = MaterialTheme.typography.bodyMedium)
                    }
                    Button(onClick = onHuaweiClick) { Text(if (uiState.isHuaweiAuthorized) "Аккаунт" else "Войти") }
                }
            }
            Spacer(Modifier.weight(1f))
            FloatingActionButton(onClick = onSyncClick, modifier = Modifier.align(Alignment.End).padding(bottom = 24.dp)) {
                Icon(Icons.Rounded.Refresh, contentDescription = "Sync")
            }
        }
    }
}
