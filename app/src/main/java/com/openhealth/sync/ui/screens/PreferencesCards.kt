package com.openhealth.sync

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.ui.semantics.Role
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.openhealth.sync.data.ExportDiagnostic
import com.openhealth.sync.ui.theme.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.DateFormat
import java.util.Date

@Composable
internal fun AppearanceSettingsCard(palette: BitPalette) {
    val context = LocalContext.current
    val mode = rememberThemeMode(context)
    SoftCard(palette) {
        Text(stringResource(R.string.appearance_title), style = MaterialTheme.typography.titleMedium, color = palette.text)
        Spacer(Modifier.height(8.dp))
        Column(Modifier.selectableGroup()) {
        ThemeMode.entries.forEach { option ->
            val label = stringResource(when (option) {
                ThemeMode.SYSTEM -> R.string.appearance_system
                ThemeMode.LIGHT -> R.string.appearance_light
                ThemeMode.DARK -> R.string.appearance_dark
            })
            Row(
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
                    .selectable(selected = mode == option, role = Role.RadioButton, onClick = { setThemeMode(context, option) }),
                verticalAlignment = androidx.compose.ui.Alignment.CenterVertically
            ) {
                RadioButton(selected = mode == option, onClick = null)
                Text(label, color = palette.text)
            }
        }
        }
    }
}

@Composable
internal fun HealthConnectDiagnosticCard(palette: BitPalette) {
    val context = LocalContext.current
    val manager = remember(context.applicationContext) { (context.applicationContext as SyncApplication).container.googleHealthManager }
    val scope = rememberCoroutineScope()
    var result by remember { mutableStateOf<ExportDiagnostic?>(null) }
    var running by remember { mutableStateOf(false) }
    var failed by remember { mutableStateOf(false) }
    SoftCard(palette) {
        Text(stringResource(R.string.export_check_title), style = MaterialTheme.typography.titleMedium, color = palette.text)
        Text(stringResource(R.string.export_check_description), color = palette.secondaryText)
        Spacer(Modifier.height(8.dp))
        SecondaryButton(stringResource(R.string.export_check_action), palette, enabled = !running, onClick = {
            scope.launch {
                running = true; failed = false
                try { result = withContext(Dispatchers.IO) { manager.exportDiagnostic() } }
                catch (cancel: kotlinx.coroutines.CancellationException) { throw cancel }
                catch (_: Exception) { failed = true; result = null }
                finally { running = false }
            }
        })
        if (running) LinearProgressIndicator(Modifier.fillMaxWidth().padding(top = 8.dp))
        if (failed) Text(stringResource(R.string.export_check_error), color = MaterialTheme.colorScheme.error)
        result?.let { diagnostic ->
            when {
                !diagnostic.available -> Text(stringResource(R.string.toast_hc_not_installed), color = palette.secondaryText)
                !diagnostic.canRead -> Text(stringResource(R.string.export_check_read_permission), color = palette.secondaryText)
                else -> {
                    Text(stringResource(if (diagnostic.hasMore) R.string.export_check_count_more else R.string.export_check_count, diagnostic.workoutCount), color = palette.text)
                    diagnostic.newestEnd?.let { newest ->
                        Text(stringResource(R.string.export_check_latest, DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(Date(newest))), color = palette.secondaryText)
                    }
                    Text(stringResource(R.string.export_check_reader_note), color = palette.secondaryText, style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}
