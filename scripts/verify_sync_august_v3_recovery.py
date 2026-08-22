#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def text(rel): return (ROOT / rel).read_text(encoding='utf-8')
def require(cond, msg):
    if not cond:
        raise SystemExit('VERIFY FAILED: ' + msg)

ghm = text('app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt')
dvm = text('app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt')
svm = text('app/src/main/java/com/openhealth/sync/ui/SyncViewModel.kt')
main = text('app/src/main/java/com/openhealth/sync/MainActivity.kt')
theme = text('app/src/main/java/com/openhealth/sync/ui/theme/BitLutExpressiveTheme.kt')
shell = text('app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt')
cards = text('app/src/main/java/com/openhealth/sync/GlassCards.kt')

require('readAllRecords(' not in ghm, 'unbounded Health Connect pagination remains in dashboard hot path')
require('readBoundedRecentRecords(' in ghm, 'bounded newest-first Health Connect reader missing')
require('PERMISSION_CACHE_TTL_MS = 30_000L' in ghm, 'permission snapshot cache TTL not hardened')
require('preserving last-known permissions' in ghm, 'transient rate limit can still become false permission denial')
require('fun refreshFromCache()' in dvm, 'cache-only dashboard refresh missing')
require('MIN_LIVE_REFRESH_INTERVAL_MS = 5_000L' in dvm, 'dashboard live-read coalescing missing')
require(main.count('onDashboardRefresh = { dashboardViewModel.refreshFromCache() }') == 2, 'sync completion still performs live dashboard reads')
require('dashboardViewModel.refresh()\n    }' not in main, 'onResume helper still performs duplicate dashboard read')
require('STATUS_REFRESH_MIN_INTERVAL_MS = 10_000L' in svm, 'sync status refresh throttling missing')
require('refreshStatuses()\n    }\n\n    companion object' not in svm, 'markSyncCompleted still re-queries permissions')
require('darkColorScheme' not in theme and 'isSystemInDarkTheme' not in theme, 'OS dark mode still overrides August v3 surface architecture')
require('window.navigationBarColor = AugustColor.Navy.toArgb()' in theme, 'system navigation chrome is not Navy')
require('val palette = remember { BitPalette.light() }' in shell, 'main shell can still switch all cards to dark palette')
require('val activity = AugustColor.InkSoft' in shell, 'legacy decorative metric accents are still Purple')
require('targetValue = if (hero) AugustColor.NavyRaised else palette.card' in cards, 'top hero is not a true NavyRaised surface')
print('Sync quota recovery + August v3 verifier passed.')
