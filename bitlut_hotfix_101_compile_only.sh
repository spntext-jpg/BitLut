#!/usr/bin/env bash
set -euo pipefail

log() { printf "\n==> %s\n" "$*"; }

if [ ! -f "settings.gradle.kts" ] || [ ! -d "app/src/main" ]; then
  echo "ERROR: run this script from BitLut repository root." >&2
  exit 1
fi

log "Bumping version to 1.0.1 / versionCode 2"
python3 - <<'PY'
from pathlib import Path
p = Path("app/build.gradle.kts")
s = p.read_text()
import re
s = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 2', s)
s = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "1.0.1"', s)
p.write_text(s)
PY

log "Replacing HMS Core helper with compatibility aliases"
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

    const val missingMessage: String =
        "HMS Core is required for Huawei Health sync. Install or update HMS Core and try again."

    fun isHmsCoreInstalled(context: Context): Boolean = try {
        context.packageManager.getPackageInfo(HMS_CORE_PACKAGE, 0)
        true
    } catch (_: PackageManager.NameNotFoundException) {
        false
    }

    // Compatibility alias for call sites introduced by previous patch.
    fun isInstalled(context: Context): Boolean = isHmsCoreInstalled(context)

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

    // Compatibility alias for call sites introduced by previous patch.
    fun openInstallPage(context: Context) = openHmsCoreInstall(context)
}
KOTLIN

log "Removing broken local ensureHmsCoreOrOpenInstall function from MainActivity"
python3 - <<'PY'
from pathlib import Path
p = Path("app/src/main/java/com/openhealth/sync/MainActivity.kt")
s = p.read_text()

if "com.openhealth.sync.platform.HmsCoreHelper" not in s:
    lines = s.splitlines()
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("import "):
            insert_at = i + 1
    lines.insert(insert_at, "import com.openhealth.sync.platform.HmsCoreHelper")
    s = "\n".join(lines) + "\n"

# Remove any previous inserted function block, even if it was inserted inside a composable/local scope.
marker = "private fun ensureHmsCoreOrOpenInstall()"
while marker in s:
    start = s.find(marker)
    brace = s.find("{", start)
    if brace == -1:
        break
    depth = 0
    end = brace
    for i in range(brace, len(s)):
        ch = s[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    s = s[:start] + s[end:]

# Also remove non-private broken variants if any.
marker2 = "fun ensureHmsCoreOrOpenInstall()"
while marker2 in s:
    start = s.find(marker2)
    brace = s.find("{", start)
    if brace == -1:
        break
    depth = 0
    end = brace
    for i in range(brace, len(s)):
        ch = s[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    s = s[:start] + s[end:]

# Replace guarded calls with direct helper call that doesn't require a local function.
replacements = {
    "if (ensureHmsCoreOrOpenInstall()) viewModel.authorizeHuawei()":
        "if (HmsCoreHelper.isInstalled(this)) viewModel.authorizeHuawei() else HmsCoreHelper.openInstallPage(this)",
    "if (ensureHmsCoreOrOpenInstall()) viewModel.requestHuaweiAuthorization()":
        "if (HmsCoreHelper.isInstalled(this)) viewModel.requestHuaweiAuthorization() else HmsCoreHelper.openInstallPage(this)",
    "if (ensureHmsCoreOrOpenInstall()) viewModel.connectHuawei()":
        "if (HmsCoreHelper.isInstalled(this)) viewModel.connectHuawei() else HmsCoreHelper.openInstallPage(this)",
}
for old, new in replacements.items():
    s = s.replace(old, new)

# If previous patch left helper calls with this in non-Activity context, keep aliases available but remove local broken declaration.
p.write_text(s)
PY

log "Ensuring SyncWorker has HMS import only once"
python3 - <<'PY'
from pathlib import Path
p = Path("app/src/main/java/com/openhealth/sync/data/worker/SyncWorker.kt")
s = p.read_text()
lines = s.splitlines()
# De-duplicate imports
seen = set()
out = []
for line in lines:
    if line.startswith("import "):
        if line in seen:
            continue
        seen.add(line)
    out.append(line)
s = "\n".join(out) + "\n"
if "com.openhealth.sync.platform.HmsCoreHelper" not in s:
    parts = s.splitlines()
    insert_at = 0
    for i, line in enumerate(parts):
        if line.startswith("import "):
            insert_at = i + 1
    parts.insert(insert_at, "import com.openhealth.sync.platform.HmsCoreHelper")
    s = "\n".join(parts) + "\n"
p.write_text(s)
PY

log "Ensuring HuaweiHealthManager has HMS import only once"
python3 - <<'PY'
from pathlib import Path
p = Path("app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt")
if not p.exists():
    raise SystemExit(0)
s = p.read_text()
if "com.openhealth.sync.platform.HmsCoreHelper" not in s:
    parts = s.splitlines()
    insert_at = 0
    for i, line in enumerate(parts):
        if line.startswith("import "):
            insert_at = i + 1
    parts.insert(insert_at, "import com.openhealth.sync.platform.HmsCoreHelper")
    s = "\n".join(parts) + "\n"
p.write_text(s)
PY

log "Adding GitHub Actions failure summary if missing"
python3 - <<'PY'
from pathlib import Path
p = Path(".github/workflows/build.yml")
if not p.exists():
    raise SystemExit(0)
s = p.read_text()
if "Build failure summary" not in s:
    s += """

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
"""
    p.write_text(s)
PY

log "Done. No local build was run."
echo "Next commands:"
echo "git diff -- app/build.gradle.kts app/src/main/java/com/openhealth/sync/platform/HmsCoreHelper.kt app/src/main/java/com/openhealth/sync/MainActivity.kt app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt app/src/main/java/com/openhealth/sync/data/worker/SyncWorker.kt .github/workflows/build.yml"
echo "git add -A && git commit -m 'fix: prepare BitLut 1.0.1 HMS Core handling' && git push origin main"
echo "gh workflow run build.yml -f version_name=1.0.1 -f version_code=2"
