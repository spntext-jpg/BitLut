#!/usr/bin/env bash
set -euo pipefail

APP_ID="${1:-117824685}"
VERSION_NAME="${2:-1.0.7}"
VERSION_CODE="${3:-8}"

if [ ! -f "settings.gradle.kts" ] || [ ! -d "app/src/main" ]; then
  echo "ERROR: run from BitLut repository root" >&2
  exit 1
fi

echo "==> Patching Huawei HMS identity config"
echo "APP_ID=$APP_ID VERSION_NAME=$VERSION_NAME VERSION_CODE=$VERSION_CODE"

python3 - "$APP_ID" "$VERSION_NAME" "$VERSION_CODE" <<'PY'
from pathlib import Path
import re
import sys

app_id, version_name, version_code = sys.argv[1], sys.argv[2], sys.argv[3]

gradle = Path("app/build.gradle.kts")
s = gradle.read_text()
s = re.sub(r'versionCode\s*=\s*\d+', f'versionCode = {version_code}', s)
s = re.sub(r'versionName\s*=\s*"[^"]+"', f'versionName = "{version_name}"', s)
s = re.sub(
    r'val huaweiAppId\s*=\s*secretProp\("HUAWEI_APP_ID",\s*"[^"]*"\)',
    f'val huaweiAppId = secretProp("HUAWEI_APP_ID", "{app_id}")',
    s
)
if 'manifestPlaceholders["huaweiAppId"]' not in s:
    s = s.replace(
        f'val huaweiAppId = secretProp("HUAWEI_APP_ID", "{app_id}")',
        f'val huaweiAppId = secretProp("HUAWEI_APP_ID", "{app_id}")\n        manifestPlaceholders["huaweiAppId"] = huaweiAppId'
    )
s = re.sub(
    r'escapedBuildConfig\("HUAWEI_APP_ID",\s*"[^"]*"\)',
    f'escapedBuildConfig("HUAWEI_APP_ID", "{app_id}")',
    s
)
gradle.write_text(s)

manifest = Path("app/src/main/AndroidManifest.xml")
m = manifest.read_text()
if 'xmlns:android=' not in m.split('>', 1)[0]:
    m = m.replace('<manifest', '<manifest xmlns:android="http://schemas.android.com/apk/res/android"', 1)

permissions = [
    '<uses-permission android:name="android.permission.INTERNET" />',
    '<uses-permission android:name="android.permission.health.WRITE_STEPS" />',
    '<uses-permission android:name="android.permission.health.WRITE_HEART_RATE" />',
    '<uses-permission android:name="android.permission.health.READ_STEPS" />',
    '<uses-permission android:name="android.permission.health.READ_HEART_RATE" />',
]
for perm in permissions:
    if perm not in m:
        close = m.find(">") + 1
        m = m[:close] + "\n    " + perm + m[close:]

queries = '''    <queries>
        <package android:name="com.google.android.apps.healthdata" />
        <package android:name="com.huawei.hwid" />
        <package android:name="com.huawei.health" />
        <package android:name="com.huawei.appmarket" />

        <intent>
            <action android:name="android.health.connect.action.MANAGE_HEALTH_PERMISSIONS" />
        </intent>

        <intent>
            <action android:name="androidx.health.ACTION_HEALTH_CONNECT_SETTINGS" />
        </intent>

        <intent>
            <action android:name="android.intent.action.VIEW" />
            <data android:scheme="market" />
        </intent>

        <intent>
            <action android:name="android.intent.action.VIEW" />
            <data android:scheme="https" />
        </intent>
    </queries>
'''
if "<queries>" not in m:
    app_pos = m.find("<application")
    if app_pos != -1:
        m = m[:app_pos] + queries + "\n    " + m[app_pos:]

meta_line = '<meta-data android:name="com.huawei.hms.client.appid" android:value="appid=${huaweiAppId}" />'
if 'com.huawei.hms.client.appid' not in m:
    app_start = m.find("<application")
    app_open_end = m.find(">", app_start)
    if app_start == -1 or app_open_end == -1:
        raise SystemExit("Could not find <application> in AndroidManifest.xml")
    m = m[:app_open_end + 1] + "\n\n        " + meta_line + m[app_open_end + 1:]
else:
    m = re.sub(
        r'<meta-data\s+android:name="com\.huawei\.hms\.client\.appid"\s+android:value="[^"]*"\s*/>',
        meta_line,
        m
    )
manifest.write_text(m)
PY

echo "==> Current HMS metadata"
grep -n "com.huawei.hms.client.appid\|huaweiAppId\|HUAWEI_APP_ID\|versionName\|versionCode" app/src/main/AndroidManifest.xml app/build.gradle.kts app/src/main/java/com/openhealth/sync/data/remote/HuaweiConfig.kt || true

echo
echo "==> Next checks:"
echo "export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64"
echo "export PATH=\$JAVA_HOME/bin:\$PATH"
echo "./gradlew --no-daemon :app:processReleaseMainManifest :app:compileReleaseKotlin --stacktrace"
echo
echo "==> Then commit:"
echo "git add -A && git commit -m 'fix: add Huawei HMS app id metadata' && git push origin main"
