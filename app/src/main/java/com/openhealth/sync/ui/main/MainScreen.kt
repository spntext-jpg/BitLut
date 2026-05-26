package com.openhealth.sync.ui.main

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.openhealth.sync.util.AppLogger

@Composable
fun MainScreen(
    onGoogleConnectClick: () -> Unit,
    onHuaweiConnectClick: () -> Unit,
    hasGooglePermissions: Boolean,
    hasHuaweiPermissions: Boolean,
    googleStatus: String,
    huaweiStatus: String,
    onExportClick: () -> Unit,
    isExporting: Boolean,
    exportStatus: String,
    onShowLogsClick: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            text = "BitLut Sync",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(bottom = 8.dp)
        )

        SourceCard(
            title = "Google Health Connect",
            status = googleStatus,
            buttonText = if (hasGooglePermissions) "Подключено" else "Подключить",
            onClick = onGoogleConnectClick
        )

        SourceCard(
            title = "Huawei Health Kit",
            status = huaweiStatus,
            buttonText = if (hasHuaweiPermissions) "Подключено" else "Подключить",
            onClick = onHuaweiConnectClick
        )

        Card(
            shape = RoundedCornerShape(20.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                Text(
                    text = "Синхронизация данных",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(text = exportStatus, style = MaterialTheme.typography.bodyMedium)
                Spacer(modifier = Modifier.height(16.dp))
                Button(
                    onClick = onExportClick,
                    enabled = !isExporting && hasGooglePermissions && hasHuaweiPermissions,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    if (isExporting) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(24.dp),
                            color = MaterialTheme.colorScheme.onPrimary
                        )
                    } else {
                        Text("Синхронизировать сейчас")
                    }
                }
            }
        }

        Card(
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.errorContainer
            ),
            shape = RoundedCornerShape(20.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                Text(
                    "Заявка на проверке",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    "BitLut уже настроен для Huawei Health Kit, но Huawei отдельно проверяет доступ к данным здоровья. Пока заявка на Health Service Kit находится на ручной проверке, авторизация может возвращать ошибки 50005 или 50011.",
                    style = MaterialTheme.typography.bodyMedium
                )
            }
        }

        Button(
            onClick = onShowLogsClick,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary)
        ) {
            Text("Показать системные логи")
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

@Composable
fun LogsOverlay(onDismiss: () -> Unit) {
    val logs by AppLogger.logs.collectAsState()

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Системные логи") },
        text = {
            LazyColumn(modifier = Modifier.fillMaxWidth().height(300.dp)) {
                items(logs) { log ->
                    Text(text = log, style = MaterialTheme.typography.bodySmall)
                    HorizontalDivider(modifier = Modifier.padding(vertical = 4.dp))
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text("Закрыть") }
        }
    )
}
