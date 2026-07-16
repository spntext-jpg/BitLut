#!/usr/bin/env python3
from pathlib import Path
import re
import sys

errors = []

def read(path):
    p = Path(path)
    if not p.exists():
        errors.append(f"Missing {path}")
        return ""
    return p.read_text(encoding="utf-8")

manifest = read("app/src/main/AndroidManifest.xml")
policy = read("app/src/main/java/com/openhealth/sync/config/HealthPermissionPolicy.kt")
google = read("app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt")
huawei = read("app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt")
main = read("app/src/main/java/com/openhealth/sync/MainActivity.kt")

allowed = [
    "READ_STEPS",
    "WRITE_STEPS",
    "READ_DISTANCE",
    "WRITE_DISTANCE",
    "READ_FLOORS_CLIMBED",
    "WRITE_FLOORS_CLIMBED",
    "READ_ELEVATION_GAINED",
    "WRITE_ELEVATION_GAINED",
    "READ_ACTIVE_CALORIES_BURNED",
    "WRITE_ACTIVE_CALORIES_BURNED",
    "READ_EXERCISE",
    "WRITE_EXERCISE",
]

for permission in allowed:
    if f"android.permission.health.{permission}" not in manifest:
        errors.append(f"Manifest missing {permission}")

for forbidden in [
    "READ_SLEEP",
    "WRITE_SLEEP",
    "READ_HEART_RATE",
    "WRITE_HEART_RATE",
    "READ_OXYGEN_SATURATION",
    "WRITE_OXYGEN_SATURATION",
    "READ_HEART_RATE_VARIABILITY",
    "WRITE_HEART_RATE_VARIABILITY",
    "READ_ACTIVITY_INTENSITY",
    "WRITE_ACTIVITY_INTENSITY",
]:
    if f"android.permission.health.{forbidden}" in manifest:
        errors.append(f"Manifest must not declare {forbidden}")

permissions = re.findall(r"android\.permission\.health\.([A-Z_]+)", manifest)
duplicates = sorted({p for p in permissions if permissions.count(p) > 1})
if duplicates:
    errors.append(f"Manifest has duplicate Health Connect permissions: {duplicates}")

for token in [
    "huaweiImportReadPermissions",
    "importWritePermissions",
    "optionalDashboardReadPermissions: Set<String> = emptySet()",
    "syncPermissions",
    "requestPermissions: Set<String> = syncPermissions",
    "dashboardReadPermissions",
]:
    if token not in policy:
        errors.append(f"HealthPermissionPolicy missing strict token: {token}")

for forbidden in [
    "SleepSessionRecord",
    "HeartRateRecord",
    "HeartRateVariabilityRmssdRecord",
    "OxygenSaturationRecord",
    "READ_SLEEP",
    "WRITE_SLEEP",
    "READ_HEART_RATE",
    "WRITE_HEART_RATE",
    "OXYGEN_SATURATION",
    "HEART_RATE_VARIABILITY",
    "ACTIVITY_INTENSITY",
]:
    if forbidden in policy:
        errors.append(f"HealthPermissionPolicy must not contain {forbidden}")

for forbidden in [
    "SleepSessionRecord",
    "HeartRateRecord",
    "HeartRateVariabilityRmssdRecord",
    "OxygenSaturationRecord",
        "readSleepLastNight",
    "readSleepQualityScoreLastNight",
    "readSleepBars",
    "readHeartRateTodayBars",
    "readHeartRateBars",
    "readAverageHeartRateToday",
    "readLatestSpo2Percent",
    "readStressScoreToday",
    "isPermissionGranted",
]:
    if forbidden in google:
        errors.append(f"GoogleHealthManager must not contain {forbidden}")

if google.count("private suspend fun insertRecords(") != 0:
    errors.append("GoogleHealthManager must not contain legacy insertRecords helper")

if google.count("private suspend fun replaceRecords(") != 1:
    errors.append("GoogleHealthManager must contain exactly one replaceRecords helper")

if "deleteRecords(recordType, emptyList(), clientRecordIds)" not in google:
    errors.append("GoogleHealthManager must delete by clientRecordId before insert")

if "insertRecords(chunk)" not in google:
    errors.append("GoogleHealthManager must insert chunked records")

for token in [
    "HEALTHKIT_STEP_READ",
    "HEALTHKIT_DISTANCE_READ",
    "HEALTHKIT_ACTIVITY_READ",
    "HEALTHKIT_ACTIVITY_RECORD_READ",
]:
    if token not in huawei:
        errors.append(f"HuaweiHealthManager missing approved Huawei scope {token}")

for forbidden in [
    "HEALTHKIT_SLEEP",
    "HEALTHKIT_HEARTRATE",
    "HEALTHKIT_BLOODOXYGEN",
    "HEALTHKIT_STRESS",
]:
    if forbidden in huawei.upper():
        errors.append(f"HuaweiHealthManager must not request {forbidden}")

if "requestGoogleHealthPermissions()" not in main:
    errors.append("MainActivity must wire Google connect button to permission request")

if errors:
    print("Strict Huawei activity sync verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Strict Huawei activity sync verification passed.")
