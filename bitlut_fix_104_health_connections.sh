#!/usr/bin/env bash
set -euo pipefail

if [ ! -f "settings.gradle.kts" ] || [ ! -d "app/src/main" ]; then
  echo "ERROR: run from BitLut repo root" >&2
  exit 1
fi

python3 - <<'PY'
from pathlib import Path
import re

p = Path("app/build.gradle.kts")
s = p.read_text()
s = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 5', s)
s = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "1.0.4"', s)
p.write_text(s)

manifest = Path("app/src/main/AndroidManifest.xml")
m = manifest.read_text()
perms = [
    '<uses-permission android:name="android.permission.health.WRITE_STEPS" />',
    '<uses-permission android:name="android.permission.health.WRITE_HEART_RATE" />',
    '<uses-permission android:name="android.permission.health.READ_STEPS" />',
    '<uses-permission android:name="android.permission.health.READ_HEART_RATE" />',
]
for perm in perms:
    if perm not in m:
        pos = m.find(">") + 1
        m = m[:pos] + "\n    " + perm + m[pos:]
if "<queries>" not in m:
    q = '''    <queries>
        <package android:name="com.google.android.apps.healthdata" />
        <package android:name="com.huawei.hwid" />
        <package android:name="com.huawei.health" />
        <package android:name="com.huawei.appmarket" />
        <intent>
            <action android:name="android.health.connect.action.MANAGE_HEALTH_PERMISSIONS" />
        </intent>
        <intent>
            <action android:name="androidx.health.ACTION_HEALTH_CONNECT_SETTINGS" />
        </intent>
    </queries>
'''
    pos = m.find("<application")
    if pos != -1:
        m = m[:pos] + q + "\n    " + m[pos:]
manifest.write_text(m)
PY

mkdir -p app/src/main/java/com/openhealth/sync/platform
cat > app/src/main/java/com/openhealth/sync/platform/HmsCoreHelper.kt <<'KOTLIN'
package com.openhealth.sync.platform

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import com.openhealth.sync.util.AppLogger

object HmsCoreHelper {
    private const val HMS_CORE_PACKAGE = "com.huawei.hwid"
    private const val APPGALLERY_PACKAGE = "com.huawei.appmarket"
    private const val HMS_CORE_WEB_URI = "https://consumer.huawei.com/en/mobileservices/hms-core/"

    const val missingMessage: String =
        "HMS Core is required for Huawei Health authorization. Install or update HMS Core and try again."

    fun isHmsCoreInstalled(context: Context): Boolean = try {
        context.packageManager.getPackageInfo(HMS_CORE_PACKAGE, 0)
        true
    } catch (_: PackageManager.NameNotFoundException) {
        false
    }

    fun isInstalled(context: Context): Boolean = isHmsCoreInstalled(context)

    fun openHmsCoreInstall(context: Context) {
        val intents = listOf(
            Intent(Intent.ACTION_VIEW, Uri.parse("appmarket://details?id=$HMS_CORE_PACKAGE")).apply {
                setPackage(APPGALLERY_PACKAGE)
            },
            Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=$HMS_CORE_PACKAGE")),
            Intent(Intent.ACTION_VIEW, Uri.parse(HMS_CORE_WEB_URI))
        )

        for (intent in intents) {
            try {
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
                AppLogger.i("HmsCoreHelper", "Opened HMS Core install/update page")
                return
            } catch (e: ActivityNotFoundException) {
                AppLogger.w("HmsCoreHelper", "HMS Core install intent unavailable: ${e.message}")
            } catch (e: Exception) {
                AppLogger.w("HmsCoreHelper", "Failed to open HMS Core install page: ${e.message}")
            }
        }
    }

    fun openInstallPage(context: Context) = openHmsCoreInstall(context)
}
KOTLIN

cat > app/src/main/java/com/openhealth/sync/MainActivity.kt <<'KOTLIN'
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
import com.openhealth.sync.platform.HmsCoreHelper
import com.openhealth.sync.ui.SyncUiState
import com.openhealth.sync.ui.SyncViewModel
import com.openhealth.sync.ui.theme.BitLutExpressiveTheme
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
            AppLogger.w("MainActivity", "Health Connect permissions were not granted; opening management/settings fallback")
            Toast.makeText(this, "Разрешите доступ BitLut в Health Connect.", Toast.LENGTH_LONG).show()
            openHealthConnectManagement()
        }
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
        if (!HmsCoreHelper.isInstalled(this)) {
            AppLogger.w("MainActivity", "HMS Core is missing; opening official HMS Core page")
            Toast.makeText(this, HmsCoreHelper.missingMessage, Toast.LENGTH_LONG).show()
            HmsCoreHelper.openInstallPage(this)
            return
        }

        if (!HuaweiConfig.hasDeveloperAppId()) {
            Toast.makeText(this, "Huawei App ID is not configured.", Toast.LENGTH_LONG).show()
            return
        }

        runCatching {
            AppLogger.i("MainActivity", "Opening Huawei Health authorization screen")
            huaweiAuthorizationLauncher.launch(viewModel.huaweiHealthManager.getAuthorizationIntent())
        }.onFailure { error ->
            AppLogger.e("MainActivity", "Cannot start Huawei authorization", error)
            Toast.makeText(this, "Не удалось открыть авторизацию Huawei Health", Toast.LENGTH_LONG).show()
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

KOTLIN

rm -f compile_errors.log fixitall.sh fix_runtime_connections_103.sh
echo "Patched BitLut 1.0.4 health connection flows. Run compileReleaseKotlin before commit."
