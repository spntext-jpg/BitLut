package com.openhealth.sync.ui.main

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
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
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
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
import kotlinx.coroutines.delay

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
        // M3 Expressive: background color, no elevation shadow on scaffold
        containerColor = MaterialTheme.colorScheme.background,
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = onToggleLogs,
                // Tonal surface — no shadow, color-based elevation
                containerColor = MaterialTheme.colorScheme.surfaceContainerHigh,
                contentColor = MaterialTheme.colorScheme.onSurfaceVariant
            ) {
                Text("📋", fontSize = 16.sp)
                Spacer(Modifier.width(6.dp))
                Text("Логи", fontSize = 14.sp)
            }
        }
    ) { innerPadding ->
        // Adaptive centering — content max width 600dp (looks good on tablets too)
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 24.dp, vertical = 32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier
                    .widthIn(max = 600.dp)
                    .padding(top = 24.dp)
                    // Spring animation on status text size change
                    .animateContentSize(
                        animationSpec = spring(
                            dampingRatio = Spring.DampingRatioMediumBouncy,
                            stiffness = Spring.StiffnessLow
                        )
                    )
            ) {
                Text(
                    text = uiState.syncStatus,
                    fontSize = if (uiState.isSyncing) 22.sp else 20.sp,
                    fontWeight = if (uiState.isSyncing) FontWeight.Bold else FontWeight.Medium,
                    color = MaterialTheme.colorScheme.onBackground,
                    textAlign = TextAlign.Center
                )
                if (uiState.lastSyncTime != "—") {
                    Spacer(Modifier.height(4.dp))
                    Text(
                        "Последняя синхронизация: ${uiState.lastSyncTime}",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            Spacer(Modifier.height(8.dp))

            // Service cards — shape morphing: first card more rounded on top,
            // second more rounded on bottom (visual container effect)
            Column(
                modifier = Modifier.widthIn(max = 600.dp).fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(4.dp)  // tight grouping = one container
            ) {
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
                    onClick = onConnectGoogle,
                    // Top card: large top radius, small bottom radius
                    shape = RoundedCornerShape(
                        topStart = 28.dp, topEnd = 28.dp,
                        bottomStart = 8.dp, bottomEnd = 8.dp
                    )
                )
                ServiceCard(
                    name = "Huawei Health",
                    statusText = when {
                        uiState.isHuaweiConnected   -> "Подключено"
                        !uiState.isHuaweiConfigured -> "Ожидает CLIENT_ID"
                        else                        -> "Нажмите для входа"
                    },
                    isConnected = uiState.isHuaweiConnected,
                    onClick = onConnectHuawei,
                    // Bottom card: small top radius, large bottom radius
                    shape = RoundedCornerShape(
                        topStart = 8.dp, topEnd = 8.dp,
                        bottomStart = 28.dp, bottomEnd = 28.dp
                    )
                )
            }

            Spacer(Modifier.weight(1f))

            // Sync button — spring animation on enabled state change
            Button(
                onClick = onSyncNow,
                enabled = !uiState.isSyncing
                        && uiState.isGoogleConnected
                        && uiState.isHuaweiConnected,
                modifier = Modifier
                    .widthIn(max = 600.dp)
                    .fillMaxWidth()
                    .height(56.dp)
                    .animateContentSize(spring(Spring.DampingRatioMediumBouncy)),
                shape = RoundedCornerShape(28.dp),
                // Tonal surface for disabled state — no ugly gray
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    disabledContainerColor = MaterialTheme.colorScheme.surfaceContainerHigh,
                    disabledContentColor = MaterialTheme.colorScheme.onSurfaceVariant
                )
            ) {
                if (uiState.isSyncing) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(22.dp),
                        strokeWidth = 2.dp,
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                } else {
                    Text(
                        "Синхронизировать",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }
        }
    }

    if (uiState.showLogs) {
        LogBottomSheet(onDismiss = onToggleLogs, context = context)
    }
}

@Composable
fun ServiceCard(
    name: String,
    statusText: String,
    isConnected: Boolean,
    onClick: () -> Unit,
    shape: RoundedCornerShape
) {
    // M3 Expressive: tonal surface, no shadow (elevation = 0)
    Surface(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        shape = shape,
        // Color hierarchy via tonal containers, not shadows
        color = if (isConnected)
            MaterialTheme.colorScheme.surfaceContainerHigh
        else
            MaterialTheme.colorScheme.surfaceContainer,
        tonalElevation = 0.dp,
        shadowElevation = 0.dp
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 20.dp, vertical = 18.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    name,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Text(
                    statusText,
                    fontSize = 12.sp,
                    color = if (isConnected) MaterialTheme.colorScheme.primary
                            else MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Spacer(Modifier.width(8.dp))
            TextButton(onClick = onClick) {
                Text(
                    if (isConnected) "Сменить" else "Войти",
                    fontWeight = FontWeight.Medium,
                    color = MaterialTheme.colorScheme.primary
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LogBottomSheet(onDismiss: () -> Unit, context: Context) {
    val logs = AppLogger.getLogs()
    val text = logs.joinToString("\n").ifEmpty { "Логов пока нет." }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        // Tonal surface for sheet background
        containerColor = MaterialTheme.colorScheme.surfaceContainerHigh
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
                    fontSize = 16.sp,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Row {
                    TextButton(onClick = {
                        val cb = context.getSystemService(Context.CLIPBOARD_SERVICE)
                                as ClipboardManager
                        cb.setPrimaryClip(ClipData.newPlainText("BitLut Logs", text))
                        Toast.makeText(context, "Скопировано", Toast.LENGTH_SHORT).show()
                    }) { Text("Копировать") }
                    TextButton(onClick = {
                        AppLogger.clear()
                        onDismiss()
                    }) { Text("Очистить") }
                }
            }

            Spacer(Modifier.height(8.dp))

            // Staggered log entries — cascade animation on open
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 120.dp, max = 500.dp)
                    .clip(RoundedCornerShape(16.dp))
                    .background(MaterialTheme.colorScheme.surfaceContainer)
                    .padding(12.dp)
                    .verticalScroll(rememberScrollState())
            ) {
                logs.takeLast(200).forEachIndexed { index, line ->
                    var visible by remember { mutableStateOf(false) }
                    LaunchedEffect(line) {
                        // Stagger: each line appears 20ms after the previous
                        delay(index.coerceAtMost(30) * 20L)
                        visible = true
                    }
                    AnimatedVisibility(
                        visible = visible,
                        enter = fadeIn() + slideInVertically(
                            initialOffsetY = { it / 2 },
                            animationSpec = spring(
                                dampingRatio = Spring.DampingRatioNoBouncy,
                                stiffness = Spring.StiffnessMedium
                            )
                        )
                    ) {
                        val color = when {
                            line.contains(" E/") -> MaterialTheme.colorScheme.error
                            line.contains(" W/") -> MaterialTheme.colorScheme.primary
                            else -> MaterialTheme.colorScheme.onSurfaceVariant
                        }
                        Text(
                            text = line,
                            fontSize = 11.sp,
                            fontFamily = FontFamily.Monospace,
                            color = color,
                            lineHeight = 15.sp,
                            modifier = Modifier.padding(vertical = 1.dp)
                        )
                    }
                }
            }
        }
    }
}
