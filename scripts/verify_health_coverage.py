#!/usr/bin/env python3
from pathlib import Path
import sys

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
    'android.permission.health.READ_SLEEP',
    'android.permission.health.WRITE_SLEEP',
    'android.permission.health.READ_HEART_RATE',
]

manifest = Path('app/src/main/AndroidManifest.xml').read_text()
missing = [p for p in required_manifest_permissions if f'android:name="{p}"' not in manifest]
if missing:
    print('Missing manifest permissions:')
    for p in missing:
        print(f'  - {p}')
    sys.exit(1)

policy = Path('app/src/main/java/com/openhealth/sync/config/HealthPermissionPolicy.kt').read_text()
for token in [
    'StepsRecord', 'DistanceRecord', 'FloorsClimbedRecord', 'ElevationGainedRecord',
    'ActiveCaloriesBurnedRecord', 'ExerciseSessionRecord', 'SleepSessionRecord', 'HeartRateRecord'
]:
    if token not in policy:
        print(f'HealthPermissionPolicy missing {token}')
        sys.exit(1)

feature_flags = Path('app/src/main/java/com/openhealth/sync/config/FeatureFlags.kt').read_text()
if 'HUAWEI_IMPORT_ENABLED: Boolean = true' not in feature_flags:
    print('Huawei import feature flag is not enabled')
    sys.exit(1)

for p in Path('app/src/main/java/com/openhealth/sync').rglob('*'):
    if p.suffix == '.bak' or '.bak' in p.name:
        print(f'Backup artifact still present: {p}')
        sys.exit(1)

for p in Path('.').glob('bitlut_*_patch.py'):
    print(f'Patch artifact should not be committed: {p}')
    sys.exit(1)

print('Health permission coverage verification passed.')
