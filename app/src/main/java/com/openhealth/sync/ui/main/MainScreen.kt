package com.openhealth.sync.ui.main

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.openhealth.sync.util.AppLogger

@Composable
fun LogsOverlay(onDismiss: () -> Unit) {
    // Подписываемся на StateFlow, это единственный корректный способ
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
