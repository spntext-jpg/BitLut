#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(relative: str) -> str:
    path = ROOT / relative
    if not path.exists():
        raise SystemExit(f"Missing {relative}")
    return path.read_text(encoding="utf-8")

huawei = read("app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt")
google = read("app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt")
scheduler = read("app/src/main/java/com/openhealth/sync/data/worker/BackgroundSyncScheduler.kt")
worker = read("app/src/main/java/com/openhealth/sync/data/worker/SyncWorker.kt")

errors = []
def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

require('fields("FIELD_STEPS_DELTA", "FIELD_STEPS")' in huawei, "step delta field fallback missing")
require("ActivityRecordReadOptions.Builder()" in huawei, "ActivityRecordsController workout read missing")
require("getActivityRecordsController(context)" in huawei, "Huawei workout controller missing")
require("catch (e: CancellationException)" in huawei, "Huawei cancellation propagation missing")
require("cont.resumeWithException(error)" in huawei, "HMS Task failures still converted to cancellation")
require("cont.cancel(error)" not in huawei, "legacy Task cancellation bridge still present")
require("client.deleteRecords(recordType, emptyList(), clientRecordIds)" not in google, "invalid-UID pre-delete still present")
require("clientRecordVersion = 1L" in google, "Health Connect upsert version missing")
require("ExistingWorkPolicy.APPEND_OR_REPLACE" in scheduler, "active worker can still be replaced/cancelled")
require("ExistingWorkPolicy.REPLACE,\n            request" not in scheduler, "legacy destructive immediate-sync policy remains")
require("failedWithData" in worker, "record-bearing partial failures can still advance the cursor")
require("SYNC_INTEGRITY_BACKFILL_KEY" in worker, "one-time repair backfill missing")

if errors:
    print("BitLut sync integrity verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("BitLut sync integrity verification passed.")
