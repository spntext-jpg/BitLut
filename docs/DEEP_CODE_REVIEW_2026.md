# BitLut deep code review 2026

## 2026-08-29 follow-up

The current code review supersedes older "pending Huawei approval" assumptions. Workout mapping is centralized, workout session distance is activity-scoped, and Health Connect write metadata/upsert behavior is hardened. Final UI cleanup removed proven dead CSV export plumbing, legacy dashboard widget-visibility state, unused non-step goal state, and orphan achievement-summary state.

Cleanup rule learned from this sprint: do not classify code as dead by lexical/private-name inspection alone. Verify call sites/callbacks, then run structural checks, XML locale parity, `assembleDebug`, and `lintDebug` before commit. Lint must be fixed rather than suppressed.

The only approved synthetic health value remains the bounded workout total-calorie fallback documented in `HEALTH_DATA_PERMISSION_MATRIX.md`; the older blanket "never synthetic calories" wording below should be read with that exception.

## Scope

Reviewed production path:

Huawei Health -> BitLut -> Android Health Connect

## Main review findings fixed

### KISS

- Huawei runtime checks are explicit and simple.
- Huawei authorization path now has one clear preflight path.
- Manual sync uses unique WorkManager work instead of allowing accidental parallel runs.

### SOLID / Separation of concerns

- `HmsCoreHelper` owns only package/runtime install and open-intent behavior.
- `HuaweiHealthManager` owns Huawei Health Kit authorization and real-data reads.
- `GoogleHealthManager` remains responsible for Health Connect writes.
- `SyncWorker` orchestrates read/write and persistence of last sync timestamp.

### DRY

- Huawei metric reads now share a single generic read path.
- Intent fallback behavior is centralized in `HmsCoreHelper`.

### YAGNI

- No fake health records.
- No placeholder workouts.
- No synthetic calories/distance/elevation.
- Unsupported Huawei SDK data types are skipped with logs rather than mocked.

### Fail fast / defensive programming

- Invalid sync windows fail before reading.
- Missing HMS Core or Huawei Health fails before authorization/read.
- Huawei authorization `50005` now gives actionable review diagnostics instead of saying no action is needed.
- Security exceptions during reads remain fatal to the worker, because missing permissions should not be silently ignored.

### POLA

- Button tap now either opens Huawei authorization or shows a concrete install/update action.
- Manual sync does not queue multiple parallel syncs.
- Empty Health Connect batches are intentionally no-op success.

### Immutable by default

- Snapshot and metric records are data classes with immutable values.
- Mutable state is localized to session aggregation and UI state.

### SSOT

- Huawei authorization state remains in `HuaweiConfig.PREFS_NAME`.
- Requested runtime Huawei scopes are explicit in `HuaweiHealthManager`.

### Testability

- The production code still has Android/HMS concrete dependencies by design.
- Future testability improvement: introduce small interfaces for Huawei reader and Health Connect writer once behavior stabilizes after approval.

## AppGallery review checklist

- Package must remain `com.openhealth.sync`.
- Huawei App ID must match AppGallery Connect.
- `agconnect-services.json` must belong to the same Huawei app.
- Release SHA-256 must match the signed APK from GitHub Actions.
- Health Kit / Health Service must be enabled.
- Requested scopes must be approved:
  - Step read
  - Distance read
  - Activity read
  - Activity record read
  - Historical data open week

## Production rule

Never generate fake health data.
Only sync records derived from real Huawei Health Kit data.