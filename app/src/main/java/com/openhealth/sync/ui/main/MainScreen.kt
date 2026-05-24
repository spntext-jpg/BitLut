package com.openhealth.sync.ui.main

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
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

    // Scaffold gives us a proper floatingActionButton slot — no clipping issues
    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = onToggleLogs,
                containerColor = MaterialTheme.colorScheme.surfaceVariant,
                contentColor = MaterialTheme.colorScheme.onSurfaceVariant
            ) {
                Text("📋", fontSize = 16.sp)
                Spacer(Modifier.width(6.dp))
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
            verticalArrangement = Arrangement.spacedBy(24.dp)
        ) {
            // ── Status header ─────────────────────────────────────────────────
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
                    Spacer(Modifier.height(4.dp))
                    Text(
                        "Последняя синхронизация: ${uiState.lastSyncTime}",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.secondary
                    )
                }
            }

            // ── Service cards ─────────────────────────────────────────────────
            ServiceCard(
                name = "Google Health",
                statusText = when {
                    uiState.isGoogleConnected -> "Подключено"
                    uiState.healthConnectStatus == HealthConnectStatus.NOT_INSTALLED ->
                        "Нажмите — установить приложение"
                    uiState.healthConnectStatus == HealthConnectStatus.NEEDS_UPDATE ->
                        "Нажмите — открыть Play Store"
                    else -> "Нажмите для подключения"
                },
                isConnected = uiState.isGoogleConnected,
                onClick = onConnectGoogle
            )

            ServiceCard(
                name = "Huawei Health",
                statusText = when {
                    uiState.isHuaweiConnected    -> "Подключено"
                    !uiState.isHuaweiConfigured  -> "Ожидает CLIENT_ID разработчика"
                    else                         -> "Нажмите для входа"
                },
                isConnected = uiState.isHuaweiConnected,
                onClick = onConnectHuawei
            )

            Spacer(Modifier.weight(1f))

            // ── Sync button ───────────────────────────────────────────────────
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

    // ── Log bottom sheet — rendered outside Scaffold so it overlays everything
    if (uiState.showLogs) {
        LogBottomSheet(onDismiss = onToggleLogs, context = context)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LogBottomSheet(onDismiss: () -> Unit, context: Context) {
    val logs = AppLogger.getLogs()
    val logsText = logs.joinToString("\n").ifEmpty { "Логов пока нет." }

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
                Text(
                    "Логи (${logs.size})",
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 16.sp
                )
                Row {
                    TextButton(onClick = {
                        val cb = context.getSystemService(Context.CLIPBOARD_SERVICE)
                                as ClipboardManager
                        cb.setPrimaryClip(ClipData.newPlainText("BitLut Logs", logsText))
                        Toast.makeText(context, "Скопировано в буфер", Toast.LENGTH_SHORT).show()
                    }) { Text("Копировать") }
                    TextButton(onClick = {
                        AppLogger.clear()
                        Toast.makeText(context, "Логи очищены", Toast.LENGTH_SHORT).show()
                        onDismiss()
                    }) { Text("Очистить") }
                }
            }
            Spacer(Modifier.height(8.dp))
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 120.dp, max = 500.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant)
                    .padding(12.dp)
            ) {
                Text(
                    text = logsText,
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    lineHeight = 15.sp,
                    modifier = Modifier.verticalScroll(rememberScrollState())
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
            Text(
                text = name,
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface
            )
            Text(
                text = statusText,
                fontSize = 12.sp,
                color = if (isConnected) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.secondary
            )
        }
        Spacer(Modifier.width(8.dp))
        TextButton(onClick = onClick) {
            Text(if (isConnected) "Сменить" else "Войти", fontWeight = FontWeight.Medium)
        }
    }
}
