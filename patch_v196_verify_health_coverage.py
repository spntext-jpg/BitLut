#!/usr/bin/env python3
from pathlib import Path

verify_path = Path('scripts/verify_health_coverage.py')
verify_path.parent.mkdir(parents=True, exist_ok=True)
verify_path.write_text('''#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path('.')

manifest_path = ROOT / 'app/src/main/AndroidManifest.xml'
policy_path = ROOT / 'app/src/main/java/com/openhealth/sync/config/HealthPermissionPolicy.kt'
google_path = ROOT / 'app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt'
huawei_path = ROOT / 'app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt'
main_path = ROOT / 'app/src/main/java/com/openhealth/sync/MainActivity.kt'
requester_path = ROOT / 'app/src/main/java/com/openhealth/sync/ui/PermissionRequester.kt'

required_files = [manifest_path, policy_path, google_path, huawei_path, main_path, requester_path]
missing_files = [str(path) for path in required_files if not path.exists()]
if missing_files:
    print('Health coverage verification failed: missing required files')
    for path in missing_files:
        print(f' - {path}')
    sys.exit(1)

manifest = manifest_path.read_text()
policy = policy_path.read_text()
google = google_path.read_text()
huawei = huawei_path.read_text()
main = main_path.read_text()
requester = requester_path.read_text()

errors = []

def require(condition, message):
    if not condition:
        errors.append(message)

# Required Health Connect activity/basic sport permissions aligned with approved Huawei Health scope.
required_manifest_permissions = [
    'android.permission.ACTIVITY_RECOGNITION',
    'android.permission.INTERNET',
    'android.permission.health.READ_STEPS',
    'android.permission.health.WRITE_STEPS',
    'android.permission.health.READ_DISTANCE',
    'android.permission.health.WRITE_DISTANCE',
    'android.permission.health.READ_FLOORS_CLIMBED',
    'android.permission.health.WRITE_FLOORS_CLIMBED',
    'android.permission.health.READ_ELEVATION_GAINED',
    'android.permission.health.WRITE_ELEVATION_GAINED',
    'android.permission.health.READ_ACTIVE_CALORIES_BURNED',
    'android.permission.health.WRITE_ACTIVE_CALORIES_BURNED',
    'android.permission.health.READ_EXERCISE',
    'android.permission.health.WRITE_EXERCISE',
]
for permission in required_manifest_permissions:
    require(f'android:name="{permission}"' in manifest, f'Manifest missing required permission {permission}')

# Optional dashboard reads are allowed, but they must never become required sync writes.
optional_dashboard_reads = [
    'android.permission.health.READ_SLEEP',
    'android.permission.health.READ_HEART_RATE',
    'android.permission.health.READ_OXYGEN_SATURATION',
    'android.permission.health.READ_HEART_RATE_VARIABILITY',
]
for permission in optional_dashboard_reads:
    require(f'android:name="{permission}"' in manifest, f'Manifest missing optional dashboard read {permission}')

for forbidden in [
    'android.permission.health.WRITE_SLEEP',
    'android.permission.health.WRITE_HEART_RATE',
    'android.permission.health.WRITE_OXYGEN_SATURATION',
    'android.permission.health.WRITE_HEART_RATE_VARIABILITY',
    'android.permission.health.READ_ACTIVITY_INTENSITY',
    'android.permission.health.WRITE_ACTIVITY_INTENSITY',
]:
    require(f'android:name="{forbidden}"' not in manifest, f'Manifest must not declare non-MVP/optional write permission {forbidden}')

for token in [
    'huaweiImportReadPermissions',
    'importWritePermissions',
    'optionalDashboardReadPermissions',
    'syncPermissions',
    'requestPermissions',
    'dashboardReadPermissions',
]:
    require(token in policy, f'HealthPermissionPolicy missing {token}')

for record in [
    'StepsRecord',
    'DistanceRecord',
    'FloorsClimbedRecord',
    'ElevationGainedRecord',
    'ActiveCaloriesBurnedRecord',
    'ExerciseSessionRecord',
]:
    require(record in policy, f'HealthPermissionPolicy missing core sync record {record}')
    require(record in google, f'GoogleHealthManager missing core sync writer/reader record {record}')

for optional_record in [
    'SleepSessionRecord',
    'HeartRateRecord',
    'OxygenSaturationRecord',
    'HeartRateVariabilityRmssdRecord',
]:
    require(optional_record in policy, f'HealthPermissionPolicy missing optional dashboard record {optional_record}')

for forbidden_policy_token in [
    'getWritePermission(SleepSessionRecord::class)',
    'getWritePermission(HeartRateRecord::class)',
    'getWritePermission(OxygenSaturationRecord::class)',
    'getWritePermission(HeartRateVariabilityRmssdRecord::class)',
]:
    require(forbidden_policy_token not in policy, f'Policy must not request optional dashboard write permission {forbidden_policy_token}')

# Current architecture no longer requires FeatureFlags.kt. Huawei import is production code and must not be hidden behind a stale flag.
feature_flags_path = ROOT / 'app/src/main/java/com/openhealth/sync/config/FeatureFlags.kt'
if feature_flags_path.exists():
    feature_flags = feature_flags_path.read_text()
    require('HUAWEI_IMPORT_ENABLED: Boolean = true' in feature_flags, 'Huawei import feature flag exists but is not enabled')

# Huawei authorization must use approved activity/basic sport scopes only.
for token in [
    'HEALTHKIT_STEP_READ',
    'HEALTHKIT_DISTANCE_READ',
    'HEALTHKIT_ACTIVITY_READ',
    'HEALTHKIT_ACTIVITY_RECORD_READ',
]:
    require(token in huawei, f'HuaweiHealthManager missing approved Huawei scope {token}')
for forbidden_huawei_token in [
    'HEALTHKIT_SLEEP_READ',
    'HEALTHKIT_HEARTRATE_READ',
    'HEALTHKIT_BLOODPRESSURE_READ',
    'HEALTHKIT_BLOODOXYGEN_READ',
]:
    require(forbidden_huawei_token not in huawei, f'HuaweiHealthManager must not request unapproved Huawei scope {forbidden_huawei_token}')

# Connect buttons must open real permission windows.
require('launcher.launch(googleManager.permissions)' in requester, 'Google connect action must launch Health Connect permission sheet')
require('requestGoogleHealthPermissions()' in main, 'MainActivity missing Google permission request flow')
require('huaweiAuthorizationLauncher.launch(syncViewModel.huaweiHealthManager.getAuthorizationIntent())' in main, 'MainActivity missing Huawei authorization launch flow')

# Dashboard and export stability.
for token in [
    'optionalDashboardRead',
    'readDashboardSnapshot failed; preserving previous UI snapshot',
    'clientRecordId = generateRecordId',
    'deleteRecords(',
    'insertRecords(chunk)',
]:
    require(token in google, f'GoogleHealthManager missing stability/idempotency token {token}')

for p in Path('app/src/main/java/com/openhealth/sync').rglob('*'):
    if p.suffix == '.bak' or '.bak' in p.name:
        errors.append(f'Backup artifact still present: {p}')

for p in Path('.').glob('bitlut_*_patch.py'):
    errors.append(f'Patch artifact should not be committed: {p}')

if errors:
    print('Health permission coverage verification failed:')
    for error in errors:
        print(' -', error)
    sys.exit(1)

print('Health permission coverage verification passed.')
''', encoding='utf-8')
verify_path.chmod(0o755)
print('patched scripts/verify_health_coverage.py')
