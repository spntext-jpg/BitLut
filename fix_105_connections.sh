#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path
import re

# Version bump
p = Path("app/build.gradle.kts")
s = p.read_text()
s = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 6', s)
s = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "1.0.5"', s)
p.write_text(s)

# HMS Core helper: open stable official web page first
p = Path("app/src/main/java/com/openhealth/sync/platform/HmsCoreHelper.kt")
s = p.read_text()
s = re.sub(
    r'private const val HMS_CORE_WEB_URI = ".*?"',
    'private const val HMS_CORE_WEB_URI = "https://consumer.huawei.com/ru/mobileservices/hms-core/"',
    s
)
old = '''val intents = listOf(
            Intent(Intent.ACTION_VIEW, Uri.parse("appmarket://details?id=$HMS_CORE_PACKAGE")).apply {
                setPackage(APPGALLERY_PACKAGE)
            },
            Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=$HMS_CORE_PACKAGE")),
            Intent(Intent.ACTION_VIEW, Uri.parse(HMS_CORE_WEB_URI))
        )'''
new = '''val intents = listOf(
            Intent(Intent.ACTION_VIEW, Uri.parse(HMS_CORE_WEB_URI)),
            Intent(Intent.ACTION_VIEW, Uri.parse("appmarket://details?id=$HMS_CORE_PACKAGE")).apply {
                setPackage(APPGALLERY_PACKAGE)
            },
            Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=$HMS_CORE_PACKAGE"))
        )'''
s = s.replace(old, new)
p.write_text(s)

# MainActivity: do not redirect to settings after empty Health Connect permission result
p = Path("app/src/main/java/com/openhealth/sync/MainActivity.kt")
s = p.read_text()

s = re.sub(
    r'''(?s)        val required = viewModel\.googleManager\.permissions\s*
        if \(!granted\.containsAll\(required\)\) \{
            AppLogger\.w\("MainActivity", "Health Connect permissions were not granted; opening management/settings fallback"\)
            Toast\.makeText\(this, "Разрешите доступ BitLut в Health Connect\.", Toast\.LENGTH_LONG\)\.show\(\)
            openHealthConnectManagement\(\)
        \}''',
    '''        val required = viewModel.googleManager.permissions
        if (!granted.containsAll(required)) {
            AppLogger.w("MainActivity", "Health Connect permissions were not granted")
            Toast.makeText(
                this,
                "Health Connect не выдал разрешения. Нажмите Google Health ещё раз и разрешите доступ BitLut.",
                Toast.LENGTH_LONG
            ).show()
        }''',
    s
)

s = s.replace(
    'AppLogger.i("MainActivity", "Opening Health Connect permission screen for: $permissions")\n            googlePermissionLauncher.launch(permissions)',
    'AppLogger.i("MainActivity", "Opening Health Connect permission screen for: $permissions")\n            Toast.makeText(this, "Открываю запрос разрешений Health Connect", Toast.LENGTH_SHORT).show()\n            googlePermissionLauncher.launch(permissions)'
)

p.write_text(s)

# Manifest: add Health Connect rationale action alias if missing
p = Path("app/src/main/AndroidManifest.xml")
s = p.read_text()

if "androidx.health.ACTION_SHOW_PERMISSIONS_RATIONALE" not in s:
    alias = '''
        <activity-alias
            android:name=".HealthConnectRationaleActivity"
            android:exported="true"
            android:targetActivity=".MainActivity">
            <intent-filter>
                <action android:name="androidx.health.ACTION_SHOW_PERMISSIONS_RATIONALE" />
            </intent-filter>
        </activity-alias>
'''
    s = s.replace("</application>", alias + "\n    </application>")

p.write_text(s)
PY

rm -f compile_errors.log fixitall.sh fix_runtime_connections_103.sh
