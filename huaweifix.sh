cat > bitlut_patch_111_workouts_scopes.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path
import re

# Version bump
p = Path("app/build.gradle.kts")
s = p.read_text()
s = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 12', s)
s = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "1.1.1"', s)
p.write_text(s)

# Manifest: add Health Connect exercise permission + Android activity recognition
p = Path("app/src/main/AndroidManifest.xml")
s = p.read_text()

perms = [
    '<uses-permission android:name="android.permission.ACTIVITY_RECOGNITION" />',
    '<uses-permission android:name="android.permission.health.WRITE_EXERCISE" />',
    '<uses-permission android:name="android.permission.health.READ_EXERCISE" />',
]

for perm in perms:
    if perm not in s:
        insert_at = s.find(">") + 1
        s = s[:insert_at] + "\n    " + perm + s[insert_at:]

p.write_text(s)

# GoogleHealthManager: add ExerciseSessionRecord permission
p = Path("app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt")
s = p.read_text()

if "androidx.health.connect.client.records.ExerciseSessionRecord" not in s:
    lines = s.splitlines()
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("import "):
            insert_at = i + 1
    lines.insert(insert_at, "import androidx.health.connect.client.records.ExerciseSessionRecord")
    s = "\n".join(lines) + "\n"

# Add workout permission near HeartRate/Steps permissions.
if "HealthPermission.getWritePermission(ExerciseSessionRecord::class)" not in s:
    s = s.replace(
        "HealthPermission.getWritePermission(HeartRateRecord::class)",
        "HealthPermission.getWritePermission(HeartRateRecord::class),\n        HealthPermission.getWritePermission(ExerciseSessionRecord::class)"
    )

p.write_text(s)

# MainActivity imports only if it uses explicit permissions somewhere.
p = Path("app/src/main/java/com/openhealth/sync/MainActivity.kt")
s = p.read_text()
if "androidx.health.connect.client.records.ExerciseSessionRecord" not in s and "ExerciseSessionRecord" in s:
    lines = s.splitlines()
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("import "):
            insert_at = i + 1
    lines.insert(insert_at, "import androidx.health.connect.client.records.ExerciseSessionRecord")
    s = "\n".join(lines) + "\n"
p.write_text(s)

# HuaweiHealthManager: better error mapping.
p = Path("app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt")
s = p.read_text()

old = 'AppLogger.e(TAG, "Huawei Health Kit authorization failed: ${result?.errorCode ?: "no result"}'
if old in s:
    s = s.replace(
        old,
        'AppLogger.e(TAG, "Huawei Health Kit authorization failed: ${result?.errorCode ?: "no result"}'
    )

needle = '''        if (success) {
            AppLogger.i(TAG, "Huawei Health Kit authorization granted")
        } else {
            AppLogger.e(TAG, "Huawei Health Kit authorization failed: ${result?.errorCode ?: "no result"}'''
if needle in s:
    s = s.replace(
        needle,
        '''        if (success) {
            AppLogger.i(TAG, "Huawei Health Kit authorization granted")
        } else {
            val code = result?.errorCode
            val hint = when (code) {
                50005 -> "Scope unauthorized. Check Health Kit Data Application: Steps, Heart Rate, and Activity/Exercise Records must be approved for Read."
                50011 -> "Huawei Health privacy/authorization was not accepted. Open Huawei Health > Me > Privacy management > HUAWEI Health Kit, then revoke BitLut authorization and try again."
                else -> "Check Huawei Health Kit enablement, SHA-256, agconnect-services.json, and test account permissions."
            }
            AppLogger.e(TAG, "Huawei Health Kit authorization failed: ${code ?: "no result"}. $hint")'''
    )

p.write_text(s)
PY

rm -f compile_errors.log
EOF

chmod +x bitlut_patch_111_workouts_scopes.sh
./bitlut_patch_111_workouts_scopes.sh