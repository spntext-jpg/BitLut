package com.openhealth.sync

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.CloudSync
import androidx.compose.material.icons.rounded.Dashboard
import androidx.compose.material.icons.rounded.FileUpload
import androidx.compose.material.icons.rounded.Lock
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.Settings
import androidx.compose.material.icons.rounded.Shield
import androidx.compose.material.icons.rounded.VerifiedUser
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import com.openhealth.sync.config.FeatureFlags
import com.openhealth.sync.ui.DashboardScreen
import com.openhealth.sync.ui.DashboardViewModel
import com.openhealth.sync.ui.ImportScreen
import com.openhealth.sync.ui.ImportViewModel
import com.openhealth.sync.ui.theme.BitLutExpressiveTheme
import com.openhealth.sync.ui.theme.Blue
import com.openhealth.sync.ui.theme.GlassCard
import com.openhealth.sync.ui.theme.GlowBlue
import com.openhealth.sync.ui.theme.GlowOrange
import com.openhealth.sync.ui.theme.GlowPurple
import com.openhealth.sync.ui.theme.MeshBackground
import com.openhealth.sync.ui.theme.Orange
import com.openhealth.sync.ui.theme.Purple
import com.openhealth.sync.ui.theme.TextPrimary
import com.openhealth.sync.ui.theme.TextSecondary
import com.openhealth.sync.util.AppLogger

/**
 * Main product shell for BitLut v1.5.
 *
 * AI-readable architecture contract:
 * - Dashboard is the default visible surface.
 * - Sync contains connection and refresh actions.
 * - Huawei Import remains discoverable but locked until Huawei Health Kit approval.
 * - Settings exposes release state and the staged Huawei feature flag.
 * - No background Huawei sync is scheduled while FeatureFlags.HUAWEI_IMPORT_ENABLED is false.
 */
class MainActivity : ComponentActivity() {

    private val dashboardViewModel: DashboardViewModel by viewModels {
        val app = application as SyncApplication
        DashboardViewModel.provideFactory(app.container.googleHealthManager)
    }

    private val importViewModel: ImportViewModel by viewModels {
        val app = application as SyncApplication
        ImportViewModel.provideFactory(app.container.googleHealthManager, applicationContext)
    }

    private val googlePermissionLauncher = registerForActivityResult(
        PermissionController.createRequestPermissionResultContract()
    ) { granted ->
        AppLogger.i("MainActivity", "Health Connect permissions returned: $granted")
        dashboardViewModel.refresh()
        val app = application as SyncApplication
        if (!granted.containsAll(app.container.googleHealthManager.permissions)) {
            Toast.makeText(this, getString(R.string.toast_hc_no_permissions), Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            BitLutExpressiveTheme {
                BitLutAppShell(
                    dashboardViewModel = dashboardViewModel,
                    importViewModel = importViewModel,
                    onConnectGoogleHealth = { requestGooglePermissionsOrOpenProvider() },
                    onRefreshDashboard = { dashboardViewModel.refresh() }
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        dashboardViewModel.refresh()
    }

    private fun requestGooglePermissionsOrOpenProvider() {
        when (HealthConnectClient.getSdkStatus(this)) {
            HealthConnectClient.SDK_AVAILABLE -> {
                Toast.makeText(this, getString(R.string.toast_hc_opening), Toast.LENGTH_SHORT).show()
                val app = application as SyncApplication
                googlePermissionLauncher.launch(app.container.googleHealthManager.permissions)
            }
            else -> {
                Toast.makeText(this, getString(R.string.toast_hc_required), Toast.LENGTH_LONG).show()
                openUriWithFallback(
                    primary = "market://details?id=com.google.android.apps.healthdata",
                    fallback = "https://play.google.com/store/apps/details?id=com.google.android.apps.healthdata"
                )
            }
        }
    }

    private fun openUriWithFallback(primary: String, fallback: String) {
        runCatching { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(primary))) }
            .onFailure { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(fallback))) }
    }
}

private enum class AppDestination(
    val label: String,
    val subtitle: String,
    val icon: ImageVector
) {
    Dashboard("Dashboard", "Health overview", Icons.Rounded.Dashboard),
    Sync("Sync", "Google Health", Icons.Rounded.CloudSync),
    HuaweiImport("Huawei", "Import locked", Icons.Rounded.FileUpload),
    Settings("Settings", "Release status", Icons.Rounded.Settings)
}

@Composable
private fun BitLutAppShell(
    dashboardViewModel: DashboardViewModel,
    importViewModel: ImportViewModel,
    onConnectGoogleHealth: () -> Unit,
    onRefreshDashboard: () -> Unit
) {
    var destination by remember { mutableStateOf(AppDestination.Dashboard) }

    BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
        MeshBackground()
        val useSidebar = maxWidth >= 720.dp

        if (useSidebar) {
            Row(modifier = Modifier.fillMaxSize().statusBarsPadding()) {
                PremiumSidebar(
                    selected = destination,
                    onSelect = { destination = it },
                    modifier = Modifier.width(280.dp).fillMaxHeight().padding(16.dp)
                )
                Box(modifier = Modifier.weight(1f).fillMaxHeight().padding(top = 16.dp, end = 16.dp, bottom = 16.dp)) {
                    AppContent(
                        destination = destination,
                        dashboardViewModel = dashboardViewModel,
                        importViewModel = importViewModel,
                        onConnectGoogleHealth = onConnectGoogleHealth,
                        onRefreshDashboard = onRefreshDashboard,
                        onBackToDashboard = { destination = AppDestination.Dashboard }
                    )
                }
            }
        } else {
            androidx.compose.foundation.layout.Column(modifier = Modifier.fillMaxSize().statusBarsPadding()) {
                Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
                    AppContent(
                        destination = destination,
                        dashboardViewModel = dashboardViewModel,
                        importViewModel = importViewModel,
                        onConnectGoogleHealth = onConnectGoogleHealth,
                        onRefreshDashboard = onRefreshDashboard,
                        onBackToDashboard = { destination = AppDestination.Dashboard }
                    )
                }
                PremiumBottomNav(
                    selected = destination,
                    onSelect = { destination = it },
                    modifier = Modifier.fillMaxWidth().navigationBarsPadding().padding(horizontal = 12.dp, vertical = 10.dp)
                )
            }
        }
    }
}

@Composable
private fun AppContent(
    destination: AppDestination,
    dashboardViewModel: DashboardViewModel,
    importViewModel: ImportViewModel,
    onConnectGoogleHealth: () -> Unit,
    onRefreshDashboard: () -> Unit,
    onBackToDashboard: () -> Unit
) {
    AnimatedContent(
        targetState = destination,
        transitionSpec = { fadeIn() togetherWith fadeOut() },
        label = "appDestination"
    ) { current ->
        when (current) {
            AppDestination.Dashboard -> {
                DashboardScreen(
                            viewModel = dashboardViewModel,
                            onSyncClick = onConnectGoogleHealth
                        )
            }
            AppDestination.Sync -> SyncScreen(
                dashboardViewModel = dashboardViewModel,
                onConnectGoogleHealth = onConnectGoogleHealth,
                onRefreshDashboard = onRefreshDashboard
            )
            AppDestination.HuaweiImport -> {
                if (FeatureFlags.HUAWEI_IMPORT_ENABLED) {
                    ImportScreen(viewModel = importViewModel, onBack = onBackToDashboard)
                } else {
                    LockedHuaweiImportScreen()
                }
            }
            AppDestination.Settings -> SettingsScreen()
        }
    }
}

@Composable
private fun PremiumSidebar(selected: AppDestination, onSelect: (AppDestination) -> Unit, modifier: Modifier = Modifier) {
    GlassCard(modifier = modifier, shape = RoundedCornerShape(32.dp), glowColor = GlowBlue.copy(alpha = 0.35f)) {
        androidx.compose.foundation.layout.Column(modifier = Modifier.fillMaxSize().padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            BrandHeader()
            Spacer(Modifier.height(10.dp))
            AppDestination.values().forEach { item ->
                NavigationItem(item = item, selected = item == selected, onClick = { onSelect(item) })
            }
            Spacer(modifier = Modifier.weight(1f))
            ReleaseBadge()
        }
    }
}

@Composable
private fun PremiumBottomNav(selected: AppDestination, onSelect: (AppDestination) -> Unit, modifier: Modifier = Modifier) {
    GlassCard(modifier = modifier, shape = RoundedCornerShape(28.dp), glowColor = GlowPurple.copy(alpha = 0.35f)) {
        Row(modifier = Modifier.fillMaxWidth().padding(8.dp), horizontalArrangement = Arrangement.SpaceBetween) {
            AppDestination.values().forEach { item ->
                val isSelected = item == selected
                androidx.compose.foundation.layout.Column(
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(20.dp))
                        .background(if (isSelected) Color(0x2619AEF9) else Color.Transparent)
                        .clickable { onSelect(item) }
                        .padding(vertical = 10.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Icon(item.icon, contentDescription = item.label, tint = if (isSelected) Blue else TextSecondary, modifier = Modifier.size(22.dp))
                    Spacer(Modifier.height(4.dp))
                    Text(item.label, color = if (isSelected) TextPrimary else TextSecondary, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
private fun BrandHeader() {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Box(
            modifier = Modifier
                .size(48.dp)
                .clip(RoundedCornerShape(16.dp))
                .background(Brush.linearGradient(listOf(Blue, Purple), start = Offset.Zero, end = Offset(120f, 120f))),
            contentAlignment = Alignment.Center
        ) {
            Icon(Icons.Rounded.AutoAwesome, contentDescription = null, tint = Color.White, modifier = Modifier.size(26.dp))
        }
        Column {
            Text("BitLut", color = TextPrimary, fontSize = 22.sp, fontWeight = FontWeight.Black, letterSpacing = (-0.6).sp)
            Text("Health Sync OS", color = TextSecondary, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun NavigationItem(item: AppDestination, selected: Boolean, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(if (selected) Color(0x2619AEF9) else Color.Transparent)
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 13.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Box(
            modifier = Modifier
                .size(34.dp)
                .clip(CircleShape)
                .background(if (selected) Color(0x3319AEF9) else Color(0x0FFFFFFF)),
            contentAlignment = Alignment.Center
        ) {
            Icon(item.icon, contentDescription = null, tint = if (selected) Blue else TextSecondary, modifier = Modifier.size(20.dp))
        }
        Column {
            Text(item.label, color = if (selected) TextPrimary else TextSecondary, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            Text(item.subtitle, color = TextSecondary.copy(alpha = 0.72f), fontSize = 11.sp, fontWeight = FontWeight.Medium)
        }
    }
}

@Composable
private fun ReleaseBadge() {
    GlassCard(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp), glowColor = GlowOrange.copy(alpha = 0.25f)) {
        Row(modifier = Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Icon(Icons.Rounded.VerifiedUser, contentDescription = null, tint = Orange, modifier = Modifier.size(22.dp))
            Column {
                Text("v1.5", color = TextPrimary, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                Text("Dashboard-first release", color = TextSecondary, fontSize = 11.sp, fontWeight = FontWeight.Medium)
            }
        }
    }
}

@Composable
private fun SyncScreen(
    dashboardViewModel: DashboardViewModel,
    onConnectGoogleHealth: () -> Unit,
    onRefreshDashboard: () -> Unit
) {
    val state by dashboardViewModel.state.collectAsState()
    ScreenColumn {
        ScreenHeader(
            icon = Icons.Rounded.CloudSync,
            title = "Sync",
            subtitle = "Connect Google Health now. Huawei Health Kit stays prepared for the next approval stage."
        )
        ActionCard(
            icon = Icons.Rounded.Shield,
            title = "Google Health Connect",
            body = if (state.hasPermissions) "Connected. BitLut can read steps and workouts for the dashboard." else "Required for steps, weekly activity and imported workouts.",
            accent = Blue,
            primaryAction = if (state.hasPermissions) "Refresh dashboard" else "Connect Google Health",
            onPrimaryAction = if (state.hasPermissions) onRefreshDashboard else onConnectGoogleHealth
        )
        ActionCard(
            icon = Icons.Rounded.FileUpload,
            title = "Huawei Health import",
            body = "Code is preserved, but the importer is locked until Huawei Health Kit approval. This keeps AppGallery review clean and avoids premature permissions.",
            accent = Orange,
            primaryAction = "Pending Health Kit approval",
            onPrimaryAction = {}
        )
    }
}

@Composable
private fun LockedHuaweiImportScreen() {
    ScreenColumn {
        ScreenHeader(
            icon = Icons.Rounded.Lock,
            title = "Huawei Import",
            subtitle = "Prepared, hidden from runtime sync, and ready to unlock after Health Kit approval."
        )
        ActionCard(
            icon = Icons.Rounded.FileUpload,
            title = "Importer preserved",
            body = "The parser, import view model and Google Health writer remain in the project. The visible import flow is intentionally locked in v1.5.",
            accent = Orange,
            primaryAction = "Locked for AppGallery review",
            onPrimaryAction = {}
        )
        InfoGrid()
    }
}

@Composable
private fun SettingsScreen() {
    ScreenColumn {
        ScreenHeader(
            icon = Icons.Rounded.Settings,
            title = "Settings",
            subtitle = "Release state, privacy posture and staged feature flags."
        )
        ActionCard(
            icon = Icons.Rounded.VerifiedUser,
            title = "Release track",
            body = FeatureFlags.RELEASE_TRACK,
            accent = Purple,
            primaryAction = "Stable",
            onPrimaryAction = {}
        )
        ActionCard(
            icon = Icons.Rounded.Lock,
            title = "Huawei feature flag",
            body = "HUAWEI_IMPORT_ENABLED = ${FeatureFlags.HUAWEI_IMPORT_ENABLED}. Turn this on only after Huawei Health Kit approval and a dedicated import QA pass.",
            accent = Orange,
            primaryAction = "Protected",
            onPrimaryAction = {}
        )
    }
}

@Composable
private fun ScreenColumn(content: @Composable androidx.compose.foundation.layout.ColumnScope.() -> Unit) {
    androidx.compose.foundation.layout.Column(
        modifier = Modifier.fillMaxSize().padding(horizontal = 20.dp, vertical = 24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        content = content
    )
}

@Composable
private fun ScreenHeader(icon: ImageVector, title: String, subtitle: String) {
    GlassCard(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(32.dp), glowColor = GlowBlue.copy(alpha = 0.35f)) {
        Row(modifier = Modifier.padding(24.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Box(
                modifier = Modifier.size(52.dp).clip(RoundedCornerShape(18.dp)).background(Brush.linearGradient(listOf(Blue, Purple))),
                contentAlignment = Alignment.Center
            ) { Icon(icon, contentDescription = null, tint = Color.White, modifier = Modifier.size(28.dp)) }
            androidx.compose.foundation.layout.Column(modifier = Modifier.weight(1f)) {
                Text(title, color = TextPrimary, fontSize = 30.sp, fontWeight = FontWeight.Black, letterSpacing = (-1.0).sp)
                Spacer(Modifier.height(4.dp))
                Text(subtitle, color = TextSecondary, fontSize = 14.sp, fontWeight = FontWeight.Medium, lineHeight = 20.sp)
            }
        }
    }
}

@Composable
private fun ActionCard(
    icon: ImageVector,
    title: String,
    body: String,
    accent: Color,
    primaryAction: String,
    onPrimaryAction: () -> Unit
) {
    GlassCard(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(28.dp), glowColor = accent.copy(alpha = 0.22f)) {
        androidx.compose.foundation.layout.Column(modifier = Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                Box(modifier = Modifier.size(44.dp).clip(RoundedCornerShape(16.dp)).background(accent.copy(alpha = 0.18f)), contentAlignment = Alignment.Center) {
                    Icon(icon, contentDescription = null, tint = accent, modifier = Modifier.size(24.dp))
                }
                androidx.compose.foundation.layout.Column(modifier = Modifier.weight(1f)) {
                    Text(title, color = TextPrimary, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                    Text(body, color = TextSecondary, fontSize = 13.sp, fontWeight = FontWeight.Medium, lineHeight = 19.sp)
                }
            }
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(18.dp))
                    .background(Brush.linearGradient(listOf(accent, Purple)))
                    .clickable(onClick = onPrimaryAction)
                    .padding(horizontal = 18.dp, vertical = 13.dp),
                contentAlignment = Alignment.Center
            ) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Icon(Icons.Rounded.Refresh, contentDescription = null, tint = Color.White, modifier = Modifier.size(18.dp))
                    Text(primaryAction, color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
private fun InfoGrid() {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        MiniInfoCard("Status", "Prepared", Blue, Modifier.weight(1f))
        MiniInfoCard("Runtime", "Locked", Orange, Modifier.weight(1f))
    }
}

@Composable
private fun MiniInfoCard(label: String, value: String, accent: Color, modifier: Modifier = Modifier) {
    GlassCard(modifier = modifier.height(120.dp), shape = RoundedCornerShape(24.dp), glowColor = accent.copy(alpha = 0.18f)) {
        androidx.compose.foundation.layout.Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.Center) {
            Text(label.uppercase(), color = TextSecondary, fontSize = 11.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.2.sp)
            Spacer(Modifier.height(8.dp))
            Text(value, color = TextPrimary, fontSize = 22.sp, fontWeight = FontWeight.Black)
        }
    }
}
