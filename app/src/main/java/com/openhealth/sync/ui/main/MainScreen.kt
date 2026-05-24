package com.openhealth.sync.ui.main

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.openhealth.sync.data.HealthConnectStatus
import com.openhealth.sync.util.AppLogger

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    uiState: MainUiState,
    onConnectHuawei: () -> Unit,
    onConnectGoogle: () -> Unit,
    onSyncNow: () -> Unit,
    onToggleLogs: () -> Unit
) {
    val context = LocalContext.current

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = onToggleLogs,
                containerColor = MaterialTheme.colorScheme.surfaceVariant,
                contentColor = MaterialTheme.colorScheme.onSurfaceVariant
            ) {
                Text("📋", fontSize = 16.sp)
                Spacer(modifier = Modifier.width(6.dp))
                Text("Логи", fontSize = 14.sp)
            }
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 24.dp, vertical = 32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.padding(top = 16.dp)
            ) {
                Text(
                    text = uiState.syncStatus,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Medium,
                    color = MaterialTheme.colorScheme.onBackground,
                    textAlign = TextAlign.Center
                )
                if (uiState.lastSyncTime != "—") {
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Последняя синхронизация: ${uiState.lastSyncTime}",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.secondary
                    )
                }
            }

            ServiceCard(
                name = "Google Health",
                statusText = when {
                    uiState.isGoogleConnected -> "Подключено"
                    uiState.healthConnectStatus == HealthConnectStatus.NOT_INSTALLED ->
                        "Нажмите — установить"
                    uiState.healthConnectStatus == HealthConnectStatus.NEEDS_UPDATE ->
                        "Нажмите — обновить"
                    else -> "Нажмите для подключения"
                },
                isConnected = uiState.isGoogleConnected,
                onClick = onConnectGoogle
            )

            ServiceCard(
                name = "Huawei Health",
                statusText = when {
                    uiState.isHuaweiConnected   -> "Подключено"
                    !uiState.isHuaweiConfigured -> "Ожидает CLIENT_ID"
                    else                        -> "Нажмите для входа"
                },
                isConnected = uiState.isHuaweiConnected,
                onClick = onConnectHuawei
            )

            Spacer(modifier = Modifier.weight(1f))

            Button(
                onClick = onSyncNow,
                enabled = !uiState.isSyncing
                        && uiState.isGoogleConnected
                        && uiState.isHuaweiConnected,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                shape = RoundedCornerShape(26.dp)
            ) {
                if (uiState.isSyncing) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(22.dp),
                        strokeWidth = 2.dp,
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                } else {
                    Text("Синхронизировать", fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }

    if (uiState.showLogs) {
        LogBottomSheet(onDismiss = onToggleLogs, context = context)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LogBottomSheet(onDismiss: () -> Unit, context: Context) {
    val logs = AppLogger.getLogs()
    val text = logs.joinToString("\n").ifEmpty { "Логов пока нет." }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = MaterialTheme.colorScheme.surface
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp)
                .padding(bottom = 32.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Логи (${logs.size})", fontWeight = FontWeight.SemiBold, fontSize = 16.sp)
                Row {
                    TextButton(onClick = {
                        val cb = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                        cb.setPrimaryClip(ClipData.newPlainText("BitLut Logs", text))
                        Toast.makeText(context, "Скопировано", Toast.LENGTH_SHORT).show()
                    }) { Text("Копировать") }
                    TextButton(onClick = {
                        AppLogger.clear()
                        onDismiss()
                    }) { Text("Очистить") }
                }
            }
            Spacer(modifier = Modifier.height(8.dp))
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 120.dp, max = 500.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant)
                    .padding(12.dp)
                    .verticalScroll(rememberScrollState())
            ) {
                Text(
                    text = text,
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    lineHeight = 15.sp
                )
            }
        }
    }
}

@Composable
fun ServiceCard(
    name: String,
    statusText: String,
    isConnected: Boolean,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(18.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .padding(horizontal = 20.dp, vertical = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(name, fontSize = 16.sp, fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface)
            Text(statusText, fontSize = 12.sp,
                color = if (isConnected) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.secondary)
        }
        Spacer(modifier = Modifier.width(8.dp))
        TextButton(onClick = onClick) {
            Text(if (isConnected) "Сменить" else "Войти", fontWeight = FontWeight.Medium)
        }
    }
}
