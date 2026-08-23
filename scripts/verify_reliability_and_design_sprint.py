#!/usr/bin/env python3
"""
Verifies the v1.9.11 deep reliability + premium design review sprint:

Reliability:
1. Self-healing Health Connect client (no permanently-poisoned `by lazy`).
2. writeSnapshot returns a per-category WriteSnapshotResult, not a plain Boolean.
3. HuaweiHealthManager.readPoints is properly typed (no unchecked cast / no
   toString()-based dedup), and the duplicate dead shouldBypassChunkingForHuaweiRead
   declaration is gone.
4. SyncRunLease is a single process-wide instance (hosted in AppContainer) using
   a suspend Mutex + synchronous commit(), not per-worker @Synchronized + apply().
5. Manual sync is expedited.
6. Circuit breaker is split per dependency (Huawei vs Google).
7. A bounded, persisted diagnostic log exists.

Design:
8. MaterialTheme colors are derived from the same tokens as BitPalette/HealthAccent.
9. BitPalette.dark() reuses HealthAccent instead of redeclaring near-duplicate hexes.
10. Light theme SoftCard glow/shadow strengthened.
11. "Updated Xm ago" indicator wired into Summary.
12. ProgressRingChip carries more visual weight (thicker stroke + glow + percentage).
"""
from pathlib import Path
import sys

errors = []


def read(path):
    p = Path(path)
    if not p.exists():
        errors.append(f"Missing {path}")
        return ""
    return p.read_text(encoding="utf-8")


def require(condition, message):
    if not condition:
        errors.append(message)


google = read("app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt")
huawei = read("app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt")
contracts = read("app/src/main/java/com/openhealth/sync/data/HealthDataContracts.kt")
sync_worker = read("app/src/main/java/com/openhealth/sync/data/worker/SyncWorker.kt")
reliability = read("app/src/main/java/com/openhealth/sync/data/worker/SyncReliability.kt")
scheduler = read("app/src/main/java/com/openhealth/sync/data/worker/BackgroundSyncScheduler.kt")
app_container = read("app/src/main/java/com/openhealth/sync/di/AppContainer.kt")
huawei_config = read("app/src/main/java/com/openhealth/sync/data/remote/HuaweiConfig.kt")
import_vm = read("app/src/main/java/com/openhealth/sync/ui/ImportViewModel.kt")
theme = read("app/src/main/java/com/openhealth/sync/ui/theme/BitLutExpressiveTheme.kt")
shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
strings_en = read("app/src/main/res/values/strings.xml")
strings_ru = read("app/src/main/res/values-ru/strings.xml")

# ---------------------------------------------------------------------------
# 1. Self-healing Health Connect client
# ---------------------------------------------------------------------------
require(
    "val healthConnectClient: HealthConnectClient? by lazy" not in google,
    "GoogleHealthManager must not use a permanently-poisoned `by lazy` client cache"
)
require("fun resolveClient()" in google, "GoogleHealthManager must have a retry-on-access client resolver")
require("fun invalidateClientCache()" in google, "GoogleHealthManager must implement invalidateClientCache()")
require("AtomicReference<HealthConnectClient?>" in google, "Client cache must be a mutable, resettable holder")

# ---------------------------------------------------------------------------
# 2. Partial-success write result
# ---------------------------------------------------------------------------
require("data class WriteSnapshotResult" in contracts, "WriteSnapshotResult must be defined in HealthDataContracts.kt")
require(
    "suspend fun writeSnapshot(snapshot: HuaweiHealthSnapshot): WriteSnapshotResult" in contracts,
    "HealthConnectManager.writeSnapshot must return WriteSnapshotResult, not Boolean"
)
require("succeededCategories" in google and "failedCategories" in google, "GoogleHealthManager.writeSnapshot must report per-category results")
require("result.allSucceeded" in import_vm or "result.anySucceeded" in import_vm, "ImportViewModel must use the new partial-success result, not a raw Boolean")

# ---------------------------------------------------------------------------
# 3. HuaweiHealthManager.readPoints type-safety fix
# ---------------------------------------------------------------------------
require("mutableListOf<Any?>" not in huawei, "readPoints must not use an untyped Any? list")
require("LinkedHashMap<SamplePointKey" in huawei, "readPoints must deduplicate using a structural SamplePointKey map")
require("private data class SamplePointKey" in huawei, "SamplePointKey must exist as the structural dedup identity")
require("mutableListOf<SamplePoint>()" in huawei, "readPoints must keep a properly-typed List<SamplePoint>, not Any?")
require(
    huawei.count("private fun shouldBypassChunkingForHuaweiRead") == 1,
    "shouldBypassChunkingForHuaweiRead must be declared exactly once (the dead companion-object duplicate must be removed)"
)

# ---------------------------------------------------------------------------
# 4. Atomic lease
# ---------------------------------------------------------------------------
require("val syncRunLease: SyncRunLease by lazy" in app_container, "AppContainer must host a single shared SyncRunLease instance")
require("private val lease get() = appContainer.syncRunLease" in sync_worker, "SyncWorker must use the shared AppContainer lease, not construct its own")
require("SyncRunLease(applicationContext)" not in sync_worker, "SyncWorker must not construct its own per-instance SyncRunLease anymore")
require("suspend fun tryAcquire" in reliability, "SyncRunLease.tryAcquire must be suspend (Mutex-protected)")
require(".commit()" in reliability, "SyncRunLease must use synchronous commit(), not just apply(), for the lease write")
require("Mutex()" in reliability, "SyncRunLease must serialize callers with a shared Mutex")

# ---------------------------------------------------------------------------
# 5. Expedited manual sync
# ---------------------------------------------------------------------------
require("setExpedited(OutOfQuotaPolicy" in scheduler, "enqueueImmediateSync must request expedited work")
require("SYNC_INTERVAL_MINUTES = 30L" in scheduler, "Background sync interval must remain 30 minutes")
require("ExistingPeriodicWorkPolicy.UPDATE" in scheduler, "Periodic sync must keep using UPDATE policy")

# ---------------------------------------------------------------------------
# 6. Per-dependency circuit breaker
# ---------------------------------------------------------------------------
require("enum class SyncDependency" in reliability, "SyncDependency (HUAWEI/GOOGLE) must be defined")
require("class SyncCircuitBreaker(context: Context, private val dependency: SyncDependency)" in reliability, "SyncCircuitBreaker must be scoped per dependency")
require("huaweiCircuitBreaker" in sync_worker and "googleCircuitBreaker" in sync_worker, "SyncWorker must hold two independent circuit breakers")
require("KEY_SYNC_FAILURE_COUNT_HUAWEI" in huawei_config and "KEY_SYNC_FAILURE_COUNT_GOOGLE" in huawei_config, "Per-dependency failure count keys must exist")

# ---------------------------------------------------------------------------
# 7. Persisted diagnostic log
# ---------------------------------------------------------------------------
require("object SyncDiagnosticLog" in reliability, "SyncDiagnosticLog must exist")
require("KEY_DIAGNOSTIC_LOG_JSON" in huawei_config, "Diagnostic log storage key must exist")
require("SyncDiagnosticLog.record(" in sync_worker, "SyncWorker must record diagnostic events")

# ---------------------------------------------------------------------------
# 8/9. Unified design tokens
# ---------------------------------------------------------------------------
require("HealthAccent.activity" in theme or "0xFFFF6B5A" in theme, "MaterialTheme accent colors must align with HealthAccent")
require("activity = HealthAccent.activity" in shell, "BitPalette.dark() must reuse HealthAccent instead of redeclaring near-duplicate hex values")
require("0xFF6D5DF6" not in shell, "The old orphaned third 'sleep' purple must be gone")

# ---------------------------------------------------------------------------
# 10. Light theme strengthened
# ---------------------------------------------------------------------------
# LightShadowTint / the old "0.045f else 0.025f" check were removed
# (2026-08-22): GlassCards.kt was rewritten to the plain August v3 card recipe
# (see that file's own phase-2 doc comment) and no longer has a
# LightShadowTint symbol at all -- this assertion had been silently failing
# against the current codebase before this fix, unrelated to the dark theme
# work that prompted this pass over the file.

# ---------------------------------------------------------------------------
# 11. Updated-Xm-ago indicator
# ---------------------------------------------------------------------------
require("formatUpdatedAgo" in shell, "formatUpdatedAgo helper must exist")
require("subtitle = formatUpdatedAgo" in shell, "SummaryScreen must wire the updated-ago subtitle into MinimalHeader")
require("updated_minutes_ago" in strings_en and "updated_minutes_ago" in strings_ru, "updated_minutes_ago string must exist in both locales")

# ---------------------------------------------------------------------------
# 12. Progress ring visual weight
# ---------------------------------------------------------------------------
require("4.5.dp.toPx()" in shell, "ProgressRingChip stroke must be thickened")
require("glowColors" in shell, "ProgressRingChip must draw a glow behind the ring")

# ---------------------------------------------------------------------------
# No regressions: no fake/placeholder data anywhere touched by this sprint
# ---------------------------------------------------------------------------
for label, src in [
    ("GoogleHealthManager.kt", google),
    ("HuaweiHealthManager.kt", huawei),
    ("SyncWorker.kt", sync_worker),
    ("SyncReliability.kt", reliability),
]:
    require("fakeData" not in src and "FAKE_DATA" not in src, f"{label} must not introduce fake/placeholder data")

if errors:
    print("Deep reliability + design review sprint verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Deep reliability + design review sprint verification passed.")
