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

contracts = read("app/src/main/java/com/openhealth/sync/data/HealthDataContracts.kt")
google = read("app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt")
huawei = read("app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt")
container = read("app/src/main/java/com/openhealth/sync/di/AppContainer.kt")
dashboard = read("app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt")
sync_vm = read("app/src/main/java/com/openhealth/sync/ui/SyncViewModel.kt")
import_vm = read("app/src/main/java/com/openhealth/sync/ui/ImportViewModel.kt")
requester = read("app/src/main/java/com/openhealth/sync/config/GoogleHealthPermissionRequester.kt")

def require(condition, message):
    if not condition:
        errors.append(message)

require("interface HealthConnectManager" in contracts, "Missing HealthConnectManager interface")
require("interface HuaweiHealthReader" in contracts, "Missing HuaweiHealthReader interface")
require("class GoogleHealthManager(" in google and ": HealthConnectManager" in google, "GoogleHealthManager must implement HealthConnectManager")
require("class HuaweiHealthManager(" in huawei and ": HuaweiHealthReader" in huawei, "HuaweiHealthManager must implement HuaweiHealthReader")

for token in [
    "override val permissions",
    "override fun requiredPermissions",
    "override fun getStatus",
    "override suspend fun missingRequiredPermissions",
    "override suspend fun hasAllPermissions",
    "override suspend fun readDashboardSnapshot",
    "override suspend fun writeSnapshot",
]:
    require(token in google, f"GoogleHealthManager missing {token}")

for token in [
    "private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO",
    "return withContext(ioDispatcher)",
    "override suspend fun readSnapshot",
]:
    require(token in huawei, f"HuaweiHealthManager missing IO hardening token: {token}")

require("val googleHealthManager: HealthConnectManager" in container, "AppContainer must expose HealthConnectManager")
require("val huaweiHealthManager: HuaweiHealthReader" in container, "AppContainer must expose HuaweiHealthReader")

for name, text in [
    ("DashboardViewModel", dashboard),
    ("SyncViewModel", sync_vm),
    ("ImportViewModel", import_vm),
    ("GoogleHealthPermissionRequester", requester),
]:
    require("HealthConnectManager" in text, f"{name} must depend on HealthConnectManager")
    require("GoogleHealthManager" not in text, f"{name} must not depend on concrete GoogleHealthManager")

require("HuaweiHealthReader" in sync_vm, "SyncViewModel must depend on HuaweiHealthReader")
require("HuaweiHealthManager" not in sync_vm, "SyncViewModel must not depend on concrete HuaweiHealthManager")

for forbidden in [
    "SleepSessionRecord",
    "HeartRateRecord",
    "OxygenSaturationRecord",
    "HeartRateVariabilityRmssdRecord",
    "READ_SLEEP",
    "READ_HEART_RATE",
    "READ_OXYGEN_SATURATION",
    "READ_HEART_RATE_VARIABILITY",
]:
    require(forbidden not in contracts, f"Contracts must stay activity-only: {forbidden}")

if errors:
    print("Architecture hardening interface verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Architecture hardening interface verification passed.")
