#!/usr/bin/env bash
set -euo pipefail

log() { printf "\n==> %s\n" "$*"; }

if [ ! -f "settings.gradle.kts" ] || [ ! -d "app/src/main" ]; then
  echo "ERROR: run this script from BitLut repository root." >&2
  exit 1
fi

log "Using Java 17"
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export PATH="$JAVA_HOME/bin:$PATH"
java -version

log "Bumping app version to 1.0.1 / versionCode 2"
python3 - <<'PY'
from pathlib import Path
p = Path('app/build.gradle.kts')
s = p.read_text()
s = s.replace('versionCode = 1', 'versionCode = 2')
s = s.replace('versionName = "1.0.0"', 'versionName = "1.0.1"')
p.write_text(s)
PY

log "Adding HMS Core helper"
mkdir -p app/src/main/java/com/openhealth/sync/platform
cat > app/src/main/java/com/openhealth/sync/platform/HmsCoreHelper.kt <<'KOTLIN'
package com.openhealth.sync.platform

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import com.openhealth.sync.util.AppLogger

object HmsCoreHelper {
    private const val HMS_CORE_PACKAGE = "com.huawei.hwid"
    private const val APPGALLERY_PACKAGE = "com.huawei.appmarket"

    fun isHmsCoreInstalled(context: Context): Boolean = try {
        context.packageManager.getPackageInfo(HMS_CORE_PACKAGE, 0)
        true
    } catch (_: PackageManager.NameNotFoundException) {
        false
    }

    fun openHmsCoreInstall(context: Context) {
        val intents = listOf(
            Intent(Intent.ACTION_VIEW, Uri.parse("appmarket://details?id=$HMS_CORE_PACKAGE")).apply {
                setPackage(APPGALLERY_PACKAGE)
            },
            Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=$HMS_CORE_PACKAGE")),
            Intent(Intent.ACTION_VIEW, Uri.parse("https://appgallery.huawei.com/app/C10132067"))
        )

        for (intent in intents) {
            try {
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
                AppLogger.i("HmsCoreHelper", "Opened HMS Core install/update page")
                return
            } catch (e: ActivityNotFoundException) {
                AppLogger.w("HmsCoreHelper", "HMS Core install intent unavailable: ${e.message}")
            } catch (e: Exception) {
                AppLogger.w("HmsCoreHelper", "Failed to open HMS Core install page: ${e.message}")
            }
        }
    }
}
KOTLIN

log "Patching SyncWorker: do not start Huawei sync without HMS Core"
python3 - <<'PY'
from pathlib import Path
p = Path('app/src/main/java/com/openhealth/sync/data/worker/SyncWorker.kt')
s = p.read_text()
if 'com.openhealth.sync.platform.HmsCoreHelper' not in s:
    parts = s.splitlines()
    insert_at = 0
    for i, line in enumerate(parts):
        if line.startswith('import '):
            insert_at = i + 1
    parts.insert(insert_at, 'import com.openhealth.sync.platform.HmsCoreHelper')
    s = '\n'.join(parts) + '\n'
needle = 'AppLogger.i("SyncWorker", "Starting Huawei -> Health Connect sync")'
guard = '''if (!HmsCoreHelper.isHmsCoreInstalled(applicationContext)) {
            AppLogger.e("SyncWorker", "HMS Core is missing; Huawei Health sync cannot start")
            return Result.failure()
        }

        '''
if needle in s and 'HMS Core is missing; Huawei Health sync cannot start' not in s:
    s = s.replace(needle, guard + needle)
p.write_text(s)
PY

log "Patching MainActivity with HMS Core install helper"
python3 - <<'PY'
from pathlib import Path
p = Path('app/src/main/java/com/openhealth/sync/MainActivity.kt')
s = p.read_text()
if 'com.openhealth.sync.platform.HmsCoreHelper' not in s:
    parts = s.splitlines()
    insert_at = 0
    for i, line in enumerate(parts):
        if line.startswith('import '):
            insert_at = i + 1
    parts.insert(insert_at, 'import com.openhealth.sync.platform.HmsCoreHelper')
    s = '\n'.join(parts) + '\n'
if 'private fun ensureHmsCoreOrOpenInstall()' not in s:
    idx = s.find('class MainActivity')
    brace = s.find('{', idx) if idx != -1 else -1
    if brace != -1:
        helper = '''
    private fun ensureHmsCoreOrOpenInstall(): Boolean {
        if (HmsCoreHelper.isHmsCoreInstalled(this)) return true
        android.widget.Toast.makeText(
            this,
            "HMS Core is required for Huawei Health sync. Opening install page.",
            android.widget.Toast.LENGTH_LONG
        ).show()
        HmsCoreHelper.openHmsCoreInstall(this)
        return false
    }

'''
        s = s[:brace + 1] + helper + s[brace + 1:]
for call in ['viewModel.authorizeHuawei()', 'viewModel.requestHuaweiAuthorization()', 'viewModel.connectHuawei()']:
    guarded = f'if (ensureHmsCoreOrOpenInstall()) {call}'
    if call in s and guarded not in s:
        s = s.replace(call, guarded)
p.write_text(s)
PY

log "Adding GitHub Actions failure summary if missing"
python3 - <<'PY'
from pathlib import Path
p = Path('.github/workflows/build.yml')
s = p.read_text()
if 'Build failure summary' not in s:
    s += '''

      - name: Build failure summary
        if: failure()
        run: |
          {
            echo "## Build failed"
            echo ""
            echo "### Environment"
            echo '```'
            java -version 2>&1 || true
            ./gradlew --version 2>&1 || true
            echo '```'
            echo ""
            echo "### APK/output tree"
            echo '```'
            find app/build/outputs -maxdepth 6 -type f -print 2>/dev/null || true
            echo '```'
            echo ""
            echo "### Common BitLut checks"
            echo "- Use JDK 17."
            echo "- Verify BITLUT_KEYSTORE_BASE64 matches the current PKCS12 release keystore."
            echo "- Verify BITLUT_KEYSTORE_PASSWORD, BITLUT_KEY_PASSWORD, and BITLUT_KEY_ALIAS=bitlut."
            echo "- Verify HUAWEI_APP_ID is set."
            echo "- For Huawei runtime tests, install HMS Core and Huawei Health."
          } >> "$GITHUB_STEP_SUMMARY"
'''
    p.write_text(s)
PY

log "Building local release 1.0.1"
if [ ! -f ".signing/bitlut-release.jks" ]; then
  echo "ERROR: .signing/bitlut-release.jks is missing." >&2
  exit 1
fi

export BITLUT_KEYSTORE_PATH=.signing/bitlut-release.jks
export BITLUT_KEYSTORE_PASSWORD=bitlut_release_password
export BITLUT_KEY_ALIAS=bitlut
export BITLUT_KEY_PASSWORD=bitlut_release_password
export HUAWEI_APP_ID=117824685

./gradlew --no-daemon :app:clean :app:assembleRelease --stacktrace

log "Commit and push"
git add -A
git commit -m "fix: prepare BitLut 1.0.1 HMS Core handling" || true
git push origin main

log "Done. Run workflow with:"
echo "gh workflow run build.yml -f version_name=1.0.1 -f version_code=2"
