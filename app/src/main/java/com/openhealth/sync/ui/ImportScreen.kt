package com.openhealth.sync.ui

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.automirrored.rounded.DirectionsRun
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.FileOpen
import androidx.compose.material.icons.rounded.LocalFireDepartment
import androidx.compose.material.icons.rounded.Place
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.openhealth.sync.R
import com.openhealth.sync.data.import.HuaweiExportSummary

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ImportScreen(
    viewModel: ImportViewModel,
    onBack: () -> Unit
) {
    val state by viewModel.state.collectAsState()

    val filePicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri ->
        if (uri != null) viewModel.parseFile(uri)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.import_screen_title), fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = {
                        viewModel.reset()
                        onBack()
                    }) {
                        Icon(Icons.AutoMirrored.Rounded.ArrowBack, contentDescription = null)
                    }
                }
            )
        }
    ) { padding ->
        AnimatedContent(
            targetState = state,
            transitionSpec = { fadeIn() togetherWith fadeOut() },
            label = "import_state",
            modifier = Modifier.padding(padding).fillMaxSize()
        ) { currentState ->
            when (currentState) {
                is ImportState.Idle    -> IdleContent(onPickFile = { filePicker.launch("*/*") })
                is ImportState.Parsing -> LoadingContent(stringResource(R.string.import_loading_parsing))
                is ImportState.Preview -> PreviewContent(
                    summary   = currentState.summary,
                    onConfirm = { viewModel.confirmImport(currentState.summary) },
                    onCancel  = { viewModel.reset() }
                )
                is ImportState.Writing -> LoadingContent(stringResource(R.string.import_loading_writing))
                is ImportState.Success -> SuccessContent(state = currentState, onDone = { viewModel.reset(); onBack() })
                is ImportState.Error   -> ErrorContent(message = currentState.message, onRetry = { viewModel.reset() })
            }
        }
    }
}

// ── Idle ──────────────────────────────────────────────────────────────────────

@Composable
private fun IdleContent(onPickFile: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(20.dp)
    ) {
        Spacer(Modifier.height(8.dp))

        Card(
            shape = RoundedCornerShape(32.dp),
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
        ) {
            Column(
                modifier = Modifier.padding(28.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text("📦", fontSize = 48.sp, textAlign = TextAlign.Center)
                Spacer(Modifier.height(12.dp))
                Text(
                    text = stringResource(R.string.import_hero_title),
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    text = stringResource(R.string.import_hero_body),
                    style = MaterialTheme.typography.bodyMedium,
                    textAlign = TextAlign.Center,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )
            }
        }

        Text(
            text = stringResource(R.string.import_instructions_title),
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold
        )

        InstructionStep("1", stringResource(R.string.import_step1_title), stringResource(R.string.import_step1_body))
        InstructionStep("2", stringResource(R.string.import_step2_title), stringResource(R.string.import_step2_body))
        InstructionStep("3", stringResource(R.string.import_step3_title), stringResource(R.string.import_step3_body))
        InstructionStep("4", stringResource(R.string.import_step4_title), stringResource(R.string.import_step4_body))
        InstructionStep("5", stringResource(R.string.import_step5_title), stringResource(R.string.import_step5_body))

        Card(
            shape = RoundedCornerShape(24.dp),
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                Text(
                    text = stringResource(R.string.import_what_title),
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSecondaryContainer
                )
                Spacer(Modifier.height(12.dp))
                DataTypeRow("👣", stringResource(R.string.import_type_steps))
                DataTypeRow("📍", stringResource(R.string.import_type_distance))
                DataTypeRow("🔥", stringResource(R.string.import_type_calories))
                DataTypeRow("🏃", stringResource(R.string.import_type_activities))
            }
        }

        Spacer(Modifier.height(8.dp))

        Button(
            onClick = onPickFile,
            modifier = Modifier.fillMaxWidth().height(56.dp),
            shape = RoundedCornerShape(20.dp)
        ) {
            Icon(Icons.Rounded.FileOpen, contentDescription = null)
            Spacer(Modifier.width(10.dp))
            Text(stringResource(R.string.import_pick_file), fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
        }

        Spacer(Modifier.height(16.dp))
    }
}

@Composable
private fun InstructionStep(number: String, title: String, body: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(16.dp),
        verticalAlignment = Alignment.Top
    ) {
        Box(
            modifier = Modifier.size(36.dp).clip(CircleShape).background(MaterialTheme.colorScheme.primary),
            contentAlignment = Alignment.Center
        ) {
            Text(number, color = MaterialTheme.colorScheme.onPrimary, fontWeight = FontWeight.Bold, fontSize = 14.sp)
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(title, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.bodyLarge)
            Spacer(Modifier.height(2.dp))
            Text(body, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun DataTypeRow(emoji: String, label: String) {
    Row(
        modifier = Modifier.padding(vertical = 3.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(emoji, fontSize = 18.sp)
        Text(label, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSecondaryContainer)
    }
}

// ── Loading ───────────────────────────────────────────────────────────────────

@Composable
private fun LoadingContent(message: String) {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(20.dp)) {
            CircularProgressIndicator(modifier = Modifier.size(52.dp), strokeWidth = 4.dp)
            Text(message, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

// ── Preview ───────────────────────────────────────────────────────────────────

@Composable
private fun PreviewContent(
    summary: HuaweiExportSummary,
    onConfirm: () -> Unit,
    onCancel: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Spacer(Modifier.height(8.dp))

        Text(stringResource(R.string.import_preview_title), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text(stringResource(R.string.import_preview_subtitle), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)

        if (summary.stepCount > 0)
            DataSummaryCard({ Icon(Icons.AutoMirrored.Rounded.DirectionsRun, null, tint = MaterialTheme.colorScheme.primary) }, stringResource(R.string.import_preview_steps), summary.stepCount)
        if (summary.distanceCount > 0)
            DataSummaryCard({ Icon(Icons.Rounded.Place, null, tint = MaterialTheme.colorScheme.secondary) }, stringResource(R.string.import_preview_distance), summary.distanceCount)
        if (summary.calorieCount > 0)
            DataSummaryCard({ Icon(Icons.Rounded.LocalFireDepartment, null, tint = MaterialTheme.colorScheme.error) }, stringResource(R.string.import_preview_calories), summary.calorieCount)
        if (summary.activityCount > 0)
            DataSummaryCard({ Icon(Icons.AutoMirrored.Rounded.DirectionsRun, null, tint = MaterialTheme.colorScheme.tertiary) }, stringResource(R.string.import_preview_activities), summary.activityCount)

        if (summary.filesFound.isNotEmpty()) {
            Card(shape = RoundedCornerShape(16.dp), modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(stringResource(R.string.import_files_found), style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.SemiBold)
                    Spacer(Modifier.height(8.dp))
                    summary.filesFound.forEach { file ->
                        Text("✓ ${file.substringAfterLast("/")}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }

        Spacer(Modifier.height(8.dp))

        Button(onClick = onConfirm, modifier = Modifier.fillMaxWidth().height(56.dp), shape = RoundedCornerShape(20.dp)) {
            Icon(Icons.Rounded.CheckCircle, contentDescription = null)
            Spacer(Modifier.width(10.dp))
            Text(stringResource(R.string.import_confirm_button), fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
        }

        OutlinedButton(onClick = onCancel, modifier = Modifier.fillMaxWidth().height(52.dp), shape = RoundedCornerShape(20.dp)) {
            Text(stringResource(R.string.import_pick_another))
        }

        Spacer(Modifier.height(16.dp))
    }
}

@Composable
private fun DataSummaryCard(icon: @Composable () -> Unit, label: String, count: Int) {
    Card(shape = RoundedCornerShape(20.dp), modifier = Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
        Row(modifier = Modifier.padding(20.dp).fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                icon()
                Text(label, style = MaterialTheme.typography.bodyLarge)
            }
            Text(count.toString(), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
        }
    }
}

// ── Success ───────────────────────────────────────────────────────────────────

@Composable
private fun SuccessContent(state: ImportState.Success, onDone: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            modifier = Modifier.size(88.dp).clip(CircleShape).background(MaterialTheme.colorScheme.primaryContainer),
            contentAlignment = Alignment.Center
        ) {
            Icon(Icons.Rounded.CheckCircle, null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(52.dp))
        }
        Spacer(Modifier.height(24.dp))
        Text(stringResource(R.string.import_success_title), style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center)
        Spacer(Modifier.height(8.dp))
        Text(stringResource(R.string.import_success_body), style = MaterialTheme.typography.bodyLarge, textAlign = TextAlign.Center, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(32.dp))
        Card(shape = RoundedCornerShape(24.dp), modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                if (state.stepsWritten > 0)     ResultRow("👣", stringResource(R.string.import_preview_steps), state.stepsWritten)
                if (state.distancesWritten > 0) ResultRow("📍", stringResource(R.string.import_preview_distance), state.distancesWritten)
                if (state.caloriesWritten > 0)  ResultRow("🔥", stringResource(R.string.import_preview_calories), state.caloriesWritten)
                if (state.activitiesWritten > 0) ResultRow("🏃", stringResource(R.string.import_preview_activities), state.activitiesWritten)
            }
        }
        Spacer(Modifier.height(32.dp))
        Button(onClick = onDone, modifier = Modifier.fillMaxWidth().height(56.dp), shape = RoundedCornerShape(20.dp)) {
            Text(stringResource(R.string.import_done), fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun ResultRow(emoji: String, label: String, count: Int) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(emoji, fontSize = 20.sp)
            Text(label, style = MaterialTheme.typography.bodyLarge)
        }
        Text(count.toString(), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
    }
}

// ── Error ─────────────────────────────────────────────────────────────────────

@Composable
private fun resolveErrorMessage(raw: String): String {
    val parts = raw.split("|", limit = 2)
    val key = parts[0]
    val detail = parts.getOrNull(1)?.trim() ?: ""
    return when (key) {
        "import_error_no_data"     -> stringResource(R.string.import_error_no_data) + if (detail.isNotBlank()) "\n\n$detail" else ""
        "import_error_read_failed" -> stringResource(R.string.import_error_read_failed) + if (detail.isNotBlank()) "\n\n$detail" else ""
        "import_error_write_failed"-> stringResource(R.string.import_error_write_failed) + if (detail.isNotBlank()) "\n\n$detail" else ""
        else -> raw
    }
}

@Composable
private fun ErrorContent(message: String, onRetry: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            modifier = Modifier.size(88.dp).clip(CircleShape).background(MaterialTheme.colorScheme.errorContainer),
            contentAlignment = Alignment.Center
        ) {
            Icon(Icons.Rounded.Warning, null, tint = MaterialTheme.colorScheme.error, modifier = Modifier.size(48.dp))
        }
        Spacer(Modifier.height(24.dp))
        Text(stringResource(R.string.import_error_title), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center)
        Spacer(Modifier.height(12.dp))
        Card(shape = RoundedCornerShape(20.dp), modifier = Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
            Text(resolveErrorMessage(message), modifier = Modifier.padding(20.dp), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onErrorContainer)
        }
        Spacer(Modifier.height(32.dp))
        FilledTonalButton(onClick = onRetry, modifier = Modifier.fillMaxWidth().height(56.dp), shape = RoundedCornerShape(20.dp)) {
            Icon(Icons.Rounded.Refresh, null)
            Spacer(Modifier.width(10.dp))
            Text(stringResource(R.string.import_retry), fontSize = 16.sp)
        }
    }
}
