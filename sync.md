# BitLut Sync Architecture

Status: current as of 2026-08-31. This document is the complete technical
record of how BitLut moves activity data from Huawei Health Kit into Google
Health Connect, and of every architectural decision that got the pipeline to
a state where a real third-party corporate wellness app now reliably
imports and accepts BitLut-synced workouts. It complements, and in a few
places supersedes, the narrower running notes in `CLAUDE.md`, `CONTEXT.md`,
`SESSION_HANDOFF.md`, and `CHANGELOG.md` — those remain the token-efficient
session-to-session continuity bridge; this file is the durable reference for
*why the pipeline is built the way it is*.

---

## 1. What BitLut does, in one paragraph

BitLut reads activity data (steps, distance, floors, elevation, active
calories, and full workout sessions) from Huawei Health Kit on GMS-free
Huawei devices, and writes it into Android Health Connect using
Health Connect's standard record types, so any other Health-Connect-aware
app — Google Fit, a corporate wellness program, a training-log app — can
read it as if it had been recorded natively. BitLut is the only bridge
between these two ecosystems for devices that have no access to Google
Mobile Services and therefore cannot use Google Fit's own Huawei
integration (which does not exist) or any GMS-dependent sync path.

The two data sources on the Health Connect side are:

- **Huawei Health Kit** (`HuaweiHealthManager`) — the read side, talking to
  `com.huawei.hms.hihealth.*` APIs.
- **Google Health Connect** (`GoogleHealthManager`) — the write side, and
  also the read side for BitLut's own dashboard, talking to
  `androidx.health.connect.client.*` APIs.

Everything else in the sync pipeline exists to make that one read-then-write
step correct, idempotent, resilient to real-world failures, and legible to
third-party readers.

---

## 2. High-level data flow

```
Huawei Watch/Phone
      │  (Huawei Health Kit sensors + app)
      ▼
Huawei Health app (on-device)
      │  HMS Health Kit APIs (DataController, ActivityRecordsController,
      │  SettingController)
      ▼
HuaweiHealthManager.readSnapshot(startTimeMs, endTimeMs)
      │  produces a HuaweiHealthSnapshot:
      │  steps, distances, floors, elevations, activeCalories, activities
      ▼
GoogleHealthManager.writeSnapshot(snapshot)
      │  writes six independent categories to Health Connect:
      │  StepsRecord, DistanceRecord, FloorsClimbedRecord,
      │  ElevationGainedRecord, ActiveCaloriesBurnedRecord,
      │  and (ExerciseSessionRecord + TotalCaloriesBurnedRecord +
      │        session-scoped DistanceRecord/StepsRecord/
      │        ElevationGainedRecord/ActiveCaloriesBurnedRecord)
      ▼
Android Health Connect (system-level data store)
      │
      ├──► BitLut's own dashboard (GoogleHealthManager.readDashboardSnapshot)
      ├──► Google Fit
      └──► Any third-party Health-Connect-aware app
             (this is what the corporate wellness app reads from)
```

The orchestration layer around this core read/write step — `SyncWorker`,
`SyncOrchestrator`, `BackgroundSyncScheduler`, `SyncRunLease`,
`SyncCircuitBreaker`, `SyncWindowPlanner` — exists because this pipeline
runs unattended, in the background, on real user devices with flaky
connectivity, OEM process death, and Huawei's own incremental,
per-category permission approval model. Section 5 covers that layer.

---

## 3. Reading from Huawei Health Kit (`HuaweiHealthManager`)

### 3.1 Authorization

Huawei Health Kit authorization is a distinct, separate consent flow from
Health Connect's runtime permissions. `HuaweiHealthManager` requests five
scopes:

- `HEALTHKIT_STEP_READ`
- `HEALTHKIT_DISTANCE_READ`
- `HEALTHKIT_ACTIVITY_READ`
- `HEALTHKIT_ACTIVITY_RECORD_READ`
- `HEALTHKIT_HISTORYDATA_OPEN_WEEK`

Two authorization entry points exist: `getAuthorizationIntent()` (via
`SettingController.requestAuthorizationIntent`) and
`getHuaweiIdAuthorizationIntent()` (via `HuaweiIdAuthManager`, requesting the
same scopes through a Huawei ID sign-in flow). `handleAuthorizationResult()`
parses the result and classifies failure into a `HuaweiAuthFailureReason`:
`SCOPE_PENDING_APPROVAL` (error 50005 — AppGallery Health Kit review not yet
approved for this package/SHA-256/scope set), `PRIVACY_NOT_ACCEPTED` (50011),
`CERTIFICATE_MISMATCH` (907135702 / 6003), `INVALID_CONFIGURATION`
(907135000), or `UNKNOWN`.

**50005 is the single most consequential error code in this codebase.** It
means Huawei's servers have not yet approved this exact
package name + release SHA-256 + scope combination for Health Kit access,
even though the user has granted permission on-device. It can also surface
per-category, incrementally, well after initial approval (see 3.3) or
transiently, mimicking a connection race (see 3.4). Every layer of this
pipeline has specific handling for it.

### 3.2 Individual-developer scope ceiling (hard constraint)

Huawei's Health Kit exposes categories in tiers. An **individual developer
account** — which is what BitLut is published under — can only ever be
approved for the **activity tier**: steps, distance, floors, elevation,
active calories, and exercise/workout records. The **advanced tier** —
sleep, heart rate, SpO2, stress — is permanently unavailable to individual
developers, full stop, regardless of scope requests or waiting. This is not
a temporary limitation being worked around; it is a fixed platform ceiling.
No code in this pipeline requests, or should ever request, an advanced-tier
scope or `DataType`. This is a standing hard constraint on the whole
project, not just this pipeline.

### 3.3 Incremental, per-category scope approval

A real device log showed Huawei approving scopes **incrementally per
category**, not atomically: steps, distance, and elevation succeeded with
real data in the same sync attempt where `activeCalories` alone returned a
50005 `SecurityException`. Before this was understood, `readSnapshot()`
constructed a single `HuaweiHealthSnapshot` data class whose constructor
arguments were Kotlin `suspend` calls evaluated eagerly, left-to-right — so
one category throwing discarded every already-successfully-read category
ahead of it, and the whole snapshot read was treated as a total failure.

The fix: each category is read through a `readCategory(label) { block() }`
wrapper that catches `SecurityException` locally, marks that one category as
denied, and returns an empty list for it — without aborting the others.
Only if **every single category** comes back scope-denied with zero
successes does `readSnapshot()` re-throw a `SecurityException`, so
`SyncWorker`'s existing "genuinely fully unauthorized" handling (see 5.6)
still fires correctly for the real all-denied case. A category that is
merely pending approval is retried on the next sync cycle automatically —
no special re-authorization step is needed once Huawei's own review catches
up.

### 3.4 Connection-race retry

A separate real-device log showed the very first Huawei Health Kit call
after a cold process start (or after the HMS client had been idle long
enough to drop its connection) intermittently failing with a "client is not
connected"-style error — sometimes surfaced as a completely different
exception type depending on which Huawei controller made the call (one
attempt saw the daily step summation fail with a `50011`-branded
"not connected" message, and the activity-records read fail right after it
and get logged as a 50005 scope denial — but the same category succeeded
about 20 seconds later with no re-authorization in between). A genuine scope
denial cannot resolve itself in 20 seconds; a connection race clearing up
once the HMS client finishes connecting can.

`retryOnConnectionRace { block() }` wraps calls that showed this pattern,
retrying up to twice (three attempts total) only when the exception message
contains "not connected" (case-insensitive). `SecurityException` and
`CancellationException` are re-thrown immediately on the first attempt,
untouched — retrying a genuine denial would only delay a correct outcome,
not fix anything.

### 3.5 Daily steps: summation API, not raw deltas

`readDailyStepTotals()` deliberately does **not** read raw
`DT_CONTINUOUS_STEPS_DELTA` samples directly. Huawei documents — and this
project confirmed on-device — that raw delta samples are not the number
Huawei Health itself displays; wearable/workout steps in particular can
exist *only* in daily/activity statistics with no delta samples backing
them at all. Instead, `dataController.readDailySummation(...)` is queried
for the app's whole 7-day activity window (`ACTIVITY_HISTORY_WINDOW_DAYS`),
producing one authoritative total per calendar day. If a day appears twice
(some OEM builds expose duplicate collectors), the **max** of the two is
kept rather than summing them, since `readDailySummation` already returns
statistical totals — summing two collectors for the same real total would
double-count.

### 3.6 Distance, floors, elevation, active calories: type/field resolution by reflection

Huawei's `DataType` and `Field` constants are resolved by **string name via
reflection** (`firstDataType(vararg names)`, `fields(vararg names)`), trying
several plausible constant names in priority order and taking the first one
that actually exists on the installed HMS SDK/device combination. This
exists because different Huawei device/firmware/HMS-Health-app combinations
expose different subsets of `DataType` constants for the same underlying
metric — for example, floors climbed is not exposed as a supported
`DataType` at all on some builds, and that is handled as a graceful,
logged, per-category skip (`emptyListWithLog`), not a crash or a total sync
failure.

`readMetric()` (the shared helper behind distance/floors/elevation/active
calories) reads points via the chunked `readPoints()` path (3.9) and returns
plain `HuaweiMetricSample(startTimeMs, endTimeMs, value)` tuples, filtered
to `value > 0.0` and `startTimeMs < endTimeMs` by each specific caller.

### 3.7 Workout sessions: `ActivityRecordsController`

Workouts are not continuous intensity samples; Huawei's supported API for
them is a completely separate controller,
`HuaweiHiHealth.getActivityRecordsController(context)`, covered by the
`HEALTHKIT_ACTIVITY_RECORD_READ` scope. `readActivitySessions()` builds an
`ActivityRecordReadOptions` requesting `readActivityRecordsFromAllApps()`
over the 7-day window, with two additional "detail" `DataType`s attached via
`.read(DataType)`:

1. `DataType.DT_CONTINUOUS_STEPS_DELTA` — carried because some Huawei Health
   builds require *some* approved detail type to be attached for the
   activity-record list to be returned at all; it is not actually consumed
   as steps data from this path (see 3.8 for why).
2. Whichever distance `DataType` `firstDataType(...)` resolves
   (`DT_CONTINUOUS_DISTANCE_DELTA` / `_TOTAL` / `DT_INSTANTANEOUS_DISTANCE`)
   — this **is** consumed, as a fallback distance source (3.10).

For each returned `ActivityRecord`, the mapping pipeline is:

1. Read `getStartTime`/`getEndTime` via reflection-guarded accessors
   (`activityRecordTime`); reject the record if either is missing or the
   interval is non-positive.
2. Read the raw activity type ID (`getActivityTypeId`/`getActivityType`)
   and raw name (`getName`).
3. Map the raw type through `HuaweiWorkoutTypeMapper` (3.11) to a canonical
   lowercase name and a Health Connect `EXERCISE_TYPE_*` constant. A record
   whose canonical type maps to `null` (a non-workout sensor state — see
   3.11) is dropped entirely, not exported as `EXERCISE_TYPE_OTHER_WORKOUT`.
4. Resolve the workout summary metrics via `readActivityRecordSummary()`
   (3.8) and the distance fallback via `readActivityRecordDistance()` (3.10).
5. Build an `ActivitySessionData` carrying start/end, title, exercise type,
   distance, total calories, elevation, and steps.

Duplicate `(startTimeMs, endTimeMs)` pairs are removed at the end via
`distinctBy`.

### 3.8 Workout summary metrics: sum across all matching points

`readActivityRecordSummary()` reads `record.getActivitySummary()
.getDataSummary()` — Huawei's own per-activity statistical summary, which
Huawei documents as part of the exercise record itself (no separate
per-metric OAuth scope required). Each returned `SamplePoint` carries one
`DataType` and one or more `Field`s; the function inspects the point's type
name (lowercased) and buckets it into distance, calories, elevation, or
steps based on substring matches (`"distance.total"`, `"calories.total"`,
`"height.total"`/`"ascend.total"`, `"steps.total"`).

**Historical bug and fix (2026-08-29):** the original version only took the
value of the **first** matching point per metric (`firstOrNull()`). A real
device log showed Huawei splitting a single activity's summary across
*multiple* points for the same metric — a 2.5&nbsp;km walk showed only
around 200 steps, because distance happened to sum correctly via its
separate fallback path (3.10) while steps took only the first of several
summary points. The fix sums (`positiveValues.sumOf { it.second }`) **all**
matching points per metric within one activity record, not just the first.
This is now correct for distance, calories, and elevation.

**Steps: still under investigation as of 2026-08-31.** The sum-across-points
fix did not fully resolve steps specifically. A later real-device log showed
a walking activity where the diagnostic logging (added 2026-08-30, see
below) reported `stepsTotalPointsMatched=0` — Huawei's own `dataSummary`
apparently emitted **zero** points whose type name matched `"steps.total"`
for that activity, a different failure mode than the "only took the first of
several" bug the sum fix addressed. A raw-stream fallback mirroring the
distance fallback (3.10) — reading `DT_CONTINUOUS_STEPS_DELTA` samples
scoped to the record via `getSampleSet(record)` — was considered and
deliberately **not** implemented: this file's own prior, hard-won lesson
(3.5, `readDailyStepTotals()`'s doc comment) already established that raw
step-delta samples are unreliable/absent for Huawei step totals in general.
Reusing that same category of fix for the per-activity case without direct
evidence would risk repeating a mistake already paid for once. Instead,
`readActivityRecordSummary()` now logs, for every raw summary point: its
type name and every field name/value pair (matched or not), plus a final
per-activity summary line (`totalPoints`, `stepsTotalPointsMatched`,
`summedSteps`). This is pure, zero-behavior-change instrumentation, added so
the next real-device sync produces ground truth for a properly-targeted
structural fix rather than a third blind guess.

### 3.9 Chunked, deduplicated point reading

`readPoints()` is the shared low-level reader behind every metric read. Two
behaviors matter:

- **Day-chunking.** Reads whose descriptor (type + time range + label) does
  not look like an activity/exercise/session/sport/workout query (per
  `shouldBypassChunkingForHuaweiRead`) are split into 24-hour chunks
  (`HUAWEI_READ_CHUNK_MS`) if the requested window exceeds one day. This
  exists because some Huawei Health builds silently truncate or degrade
  responses for very wide raw-sample queries; chunking by day keeps every
  individual request small and reliable. Activity/session/workout reads
  bypass chunking entirely (`ActivityRecordReadOptions` already scopes its
  own time window correctly for the whole 7-day request in one call).
- **Identity-based deduplication.** Adjacent chunk boundaries can each
  return the same boundary sample twice. Deduplication keys on the sample's
  **actual identity** — `(startTimeMs, endTimeMs, firstNumericValue(dedupFields))`
  — not on `SamplePoint.toString()` or object identity. An earlier version
  used `Any` typing and string-based dedup; both were rejected as unsafe:
  `Any` throws away compile-time type safety for no benefit (the list only
  ever holds `SamplePoint`s), and two genuinely different samples that
  happen to stringify identically would be wrongly collapsed, silently
  dropping real health data — "the single worst kind of bug for an app
  whose entire purpose is accurate data transfer," per the code's own
  comment.

### 3.10 Per-activity distance fallback: `getSampleSet(record)`

`readActivityRecordDistance()` exists because Huawei's coarse background
distance-delta stream (the same stream `readDistance()` reads for the daily
aggregate, 3.6) reports samples whose own time window frequently does
**not** line up with the actual workout's start/end — a real 28&nbsp;km,
~2-hour bike ride was measured showing only 0.7&nbsp;km on the dashboard, a
~40x undercount consistent with a wide background sample being credited
only for the small geometric sliver of its reported window that happened to
overlap the workout's exact interval (an artifact of time-overlap-fraction
math, not of the underlying distance value, which was correct in total —
just wrongly attributed across time).

The fix uses Huawei's `ActivityRecordsController` API correctly: the
distance `DataType` requested via `.read(distanceDetailType)` on the
`ActivityRecordReadOptions` (3.7) is retrievable per-record via
`reply.getSampleSet(record)`, which returns exactly the detail samples
Huawei itself scoped to that one activity — not a separate query needing
manual time-window reconciliation. This pattern is confirmed against
Huawei's own published sample code
(`HealthKitActivityRecordControllerActivity.java` in Huawei's
`hms-health-demo-java` repository), which shows the identical
`getSampleSet(activityRecord) → sampleSet.getSamplePoints()` shape. One
detail remains inferred rather than independently confirmed for Huawei
specifically: whether calling `.read(DataType)` a second time (for distance,
alongside the already-required steps-delta detail type) *accumulates* both
requested detail types rather than replacing the first — inferred from
Google Fit's near-identical, explicitly documented
`SessionReadRequest.Builder.read(DataType)` behavior, and from this file's
own pre-existing treatment of `.read(...)` as additive. This is exactly the
class of real HMS-SDK behavior a sandbox cannot verify directly; Paulo's
real `assembleDebug` build is the actual compile/behavior gate for it, and
it has since been confirmed working on-device.

Distance from this path is summed per-record from real Huawei sample data
scoped to that exact activity — never prorated or estimated. A record with
no matching distance samples correctly yields `null` (displayed as "—" on
the dashboard), consistent with the project's "real data only, never
fabricate" rule.

### 3.11 Workout type mapping (`HuaweiWorkoutTypeMapper`)

Huawei's numeric activity-type IDs (per the current Health Kit activity
table, including IDs 161/marathon and 162/pickleball added after the
original table) are mapped through two stages:

1. **`canonicalName(rawType)`** — normalizes a raw numeric ID or string into
   a canonical lowercase English name (e.g. `56` → `"running"`,
   `"football_american"` → `"american football"`).
2. **`healthConnectType(canonicalType)`** — maps the canonical name to a
   Health Connect `ExerciseSessionRecord.EXERCISE_TYPE_*` int constant,
   resolved via reflection (`getField(name).getInt(null)`) so an unmapped or
   future Huawei type degrades to `EXERCISE_TYPE_OTHER_WORKOUT` rather than
   crashing.

A small set of Huawei "activity-like sensor states that are not actual
workouts" — `elevator`, `escalator`, `in vehicle`, `sleep`, `still`,
`tilting` — are explicitly rejected (`healthConnectType` returns `null`),
rather than being exported as a bogus `EXERCISE_TYPE_OTHER_WORKOUT` session.
This mapper is the single source of truth for Huawei-type-ID-to-Health-
Connect-type translation; nothing else in the codebase should duplicate it.

---

## 4. Writing to Health Connect (`GoogleHealthManager`)

### 4.1 Client lifecycle: self-healing cache

`HealthConnectClient` creation is cached in an `AtomicReference`, but unlike
a naive `by lazy { ... }`, a **failed** creation is not cached — the next
access retries `HealthConnectClient.getOrCreate()` fresh. This matters
because a single transient failure right after device boot (or an OEM
process killing the Health Connect provider) previously disabled Google
Health for the rest of the app process's lifetime with no recovery path
short of a force-stop. A `Mutex` (`clientLock`) serializes concurrent
creation attempts so manual and periodic sync paths racing on client
creation don't call `getOrCreate()` twice concurrently.
`invalidateClientCache()` is called explicitly whenever a
`SecurityException` suggests the cached client reference has gone stale
(e.g. Health Connect itself was reinstalled/updated underneath the app).

### 4.2 Permission checks: coalesced and cached

Multiple near-simultaneous callers (dashboard load, resume-triggered
auto-sync preflight, a manual sync button's own preflight, and
`SyncWorker`'s independent preflight) used to each hit the Health Connect
provider separately for a permission snapshot. Under load, that made a
transient IPC hiccup more likely to happen twice in a row — exhausting a
single-retry safety net and incorrectly flashing a "Connect Health Connect"
prompt over data that was actually fine. `grantedPermissionsOrEmpty()` now
coalesces this behind a `Mutex` plus a 30-second TTL cache
(`PERMISSION_CACHE_TTL_MS`), so a whole burst of calls within the TTL window
shares one real provider result. A single transient failure gets one quick
retry (400ms, `TRANSIENT_PERMISSION_RETRY_DELAY_MS`); if that retry also
fails, the last-known-good permission set is preserved rather than treating
a rate limit as a real denial (unless there is no prior known state, in
which case the exception propagates).

### 4.3 `writeSnapshot()`: six independent categories, partial-failure-tolerant

```kotlin
val results = listOf(
    "steps" to writeStepsBatch(snapshot.steps),
    "distance" to writeDistanceBatch(snapshot.distances),
    "floors" to writeFloorsBatch(snapshot.floors),
    "elevation" to writeElevationBatch(snapshot.elevations),
    "activeCalories" to writeActiveCaloriesBatch(snapshot.activeCalories),
    "activitySessions" to writeActivitySessionsBatch(workoutFilterPrefs.apply(snapshot.activities))
)
```

Each category writes independently and reports its own success/failure,
rather than collapsing into one Boolean. This lets a permanently-failing
category (e.g. floors, unsupported on some Huawei device/firmware
combinations — see 3.6) fail forever without blocking every *other*
category's sync cursor from advancing.

**This list's evaluation order is load-bearing** (documented explicitly in
`writeSnapshot()` since 2026-08-31): `writeStepsBatch`'s "complete daily
summation" branch (4.4) can delete-then-reinsert an entire day's
`StepsRecord`s as part of reconciling Huawei's authoritative daily total.
Since 2026-08-31, `writeActivitySessionsBatch` also writes a
workout-scoped `StepsRecord` for some exercise types (4.7). Because these
are sequential `suspend` calls inside one list literal — not launched
concurrently — `writeStepsBatch`'s delete-then-reinsert always fully
completes before `writeActivitySessionsBatch` runs, so the daily
reconciliation never wipes out a workout's freshly-written step record. If
this list is ever parallelized, `activitySessions` must be kept strictly
after `steps`, or that ordering guarantee breaks silently.

### 4.4 Steps: two write modes

`writeStepsBatch()` branches on whether every incoming `StepData` record
carries a `sourceId` (only `readDailyStepTotals()`'s daily-summation output
sets this; nothing else does):

- **Complete daily summation** (all records have a `sourceId`, i.e. a
  calendar date string): this is Huawei's own authoritative per-day total.
  The write does an explicit `client.deleteRecords(StepsRecord::class,
  TimeRangeFilter.between(deleteStart, deleteEnd))` across the full affected
  date range **before** inserting the new totals. Health Connect
  automatically restricts a time-range delete to records owned by the
  calling app, so this cannot touch another app's step data — only BitLut's
  own previously-written (now-superseded) step records for those days. This
  prevents old, now-stale raw-delta-derived records from double-counting
  alongside the new authoritative daily total. The delete uses a synchronous
  path (see 4.9 for the general upsert pattern) and only proceeds if the
  delete succeeds.
- **Partial/non-daily records** (any record lacks a `sourceId`): falls
  through to the ordinary `replaceRecords()` upsert path (4.9) with no
  delete step.

### 4.5 Distance, floors, elevation, active calories: plain upsert

`writeDistanceBatch`, `writeFloorsBatch`, `writeElevationBatch`, and
`writeActiveCaloriesBatch` are structurally identical: filter to
`value > 0.0 && startTimeMs < endTimeMs`, map to the corresponding Health
Connect record type with a stable `clientRecordId` (via `bitlutMetadata`,
4.8), and call the shared `replaceRecords()` upsert helper (4.9). No delete
step — `insertRecords` with a stable `clientRecordId` and a newer
`clientRecordVersion` is itself an upsert in Health Connect's own model.

### 4.6 Workout sessions: the interoperability-critical write path

`writeActivitySessionsBatch()` is the single most important function in this
document, because it is the one whose evolution actually fixed third-party
import.

**Preprocessing.** Incoming records are deduplicated by
`(startTimeMs, endTimeMs)`, filtered to `startTimeMs < endTimeMs`, and
sorted by start time.

**Per-session write.** For each valid session:

1. `persistWorkoutSummary(session)` — writes the session's Huawei-sourced
   summary metrics (distance, total calories, elevation, steps) to a local
   `SharedPreferences` sidecar (`bitlut_workout_summary_v1`), keyed by
   `"$startTimeMs:$endTimeMs"`. **This is a local-only cache for BitLut's own
   dashboard**, not anything Health Connect or a third party ever sees — see
   4.10 for why it still exists after the interoperability fix.
2. `workoutRecordVersion(session)` — computes a stable
   `clientRecordVersion`. A SHA-256 fingerprint of the session's type,
   title, distance, calories, elevation, and steps (`workoutFingerprint`,
   truncated to 12 hex bytes) is compared against the last-stored
   fingerprint for that exact `(startTimeMs, endTimeMs)` key; if unchanged,
   the previous version number is reused (so downstream readers are not
   forced to re-process every unchanged historical workout on every
   30-minute background sync); if changed, a new version
   (`max(now, previousVersion + 1)`) is generated and persisted. This is
   what lets a genuine Huawei-side correction to an already-synced workout
   upsert cleanly instead of either being silently ignored or creating a
   duplicate.
3. Build the `ExerciseSessionRecord` itself: `startTime`/`endTime` with
   correct `ZoneOffset`s (via `zoneRules.getOffset(instant)`), the mapped
   `exerciseType`, the (possibly localized) `title`, and
   `bitlutWorkoutMetadata("exercise", ...)` — `Metadata.activelyRecorded`
   (see 4.8), not `autoRecorded`, because Huawei documents exercise
   ActivityRecords as data produced only after the user explicitly starts a
   workout.
4. Resolve total calories: `session.totalCaloriesKcal` if Huawei provided a
   real summary value, otherwise a MET-formula estimate
   (`WorkoutCalorieEstimator`, 4.11) — **only** so that a third-party reader
   sees a non-zero, plausible calorie figure for workouts on Huawei
   device/firmware combinations that never populate this field via the
   summary API at all. If a value is available either way, it is bundled as
   a `TotalCaloriesBurnedRecord`, keyed under the stable
   `"exercise_calories_estimate"` client-ID type so a later real Huawei
   value naturally upgrades an earlier estimate in place rather than
   duplicating it.
5. **(Since 2026-08-30/31)** Resolve and bundle session-scoped
   `DistanceRecord`, `StepsRecord`, `ElevationGainedRecord`, and — forward-
   compatible, currently always null in practice —
   `ActiveCaloriesBurnedRecord`, gated per exercise type by
   `sessionSubMetricsFor()` (4.7). This is the interoperability fix; see
   4.7 for the full rationale.
6. All of the above (`ExerciseSessionRecord` + `TotalCaloriesBurnedRecord` +
   any applicable session-scoped sub-records) are inserted in **one single
   `client.insertRecords(bundle)` call**, so a reader never observes a
   bare, newly-written session before its associated summary data arrives.

**Per-session failure isolation.** Each session's insert is wrapped in its
own `try`/`catch`; one malformed or overlapping Huawei session failing to
write does not prevent the rest of that sync's valid workouts from being
written. `SecurityException` still propagates (and invalidates the client
cache) since that indicates a genuine, sync-wide permission problem, not a
per-session data issue.

### 4.7 Session-scoped sub-records: the actual interoperability fix

**This is the change that made the corporate wellness app start accepting
BitLut's workouts**, confirmed directly (not inferred) after this exact
patch was applied.

**The problem.** `session.distanceMeters`, `session.steps`, and
`session.elevationMeters` were computed correctly by `HuaweiHealthManager`
(3.8, 3.10) — but before 2026-08-30, they were used **only** for BitLut's
own dashboard display (via the `persistWorkoutSummary`/
`storedWorkoutSummary` local sidecar, 4.10). They were never written to
Health Connect as records belonging to the workout's own time window.

Health Connect has **no explicit link** between an `ExerciseSessionRecord`
and any `DistanceRecord`/`StepsRecord`/`ElevationGainedRecord` that might
describe the same workout. Per Health Connect's own documented pattern (its
"Add exercise routes" guide's `readExerciseSessions()` sample), a reader
determines a session's own distance by querying `DistanceRecord` over the
**same time range** as the exercise session — a pure time-overlap
convention, not a foreign key. Before this fix, the only
`DistanceRecord`/`StepsRecord`/`ElevationGainedRecord` that existed in a
workout's time window was the **separate, coarser background aggregate**
written by `writeDistanceBatch`/`writeStepsBatch`/`writeElevationBatch` from
Huawei's own daily/background streams — and those streams' sample windows
are independently documented (3.6, 3.10) as frequently **not** lining up
cleanly with an exact workout interval. A third-party reader — Google Fit,
Health Connect's own session-detail UI, or the corporate wellness app —
querying that workout's own metrics by time-range overlap had nothing
trustworthy to find: either nothing at all, or a value smeared across the
wrong time window.

**The fix.** `writeActivitySessionsBatch()` now bundles
`DistanceRecord`/`StepsRecord`/`ElevationGainedRecord`/
`ActiveCaloriesBurnedRecord` into the **same `insertRecords` call** as the
`ExerciseSessionRecord`, scoped to the session's **exact** `startTime`/
`endTime` — so a time-range-overlap query from any reader now finds real,
accurately-scoped data for that specific workout, not a coarse background
guess.

**Per-exercise-type gating (`sessionSubMetricsFor`).** Not every exercise
type can plausibly produce every metric — writing a fabricated `DistanceRecord`
for a strength-training or yoga session would itself be untrustworthy data,
in the opposite direction from the original bug. `sessionSubMetricsFor()`
mirrors, metric-for-metric, the exact per-type contract already established
by the dashboard's own `workoutMetricDisplays()` in `FinalBitLutShell.kt`
(so there is exactly one place that decides "what metrics make sense for
this exercise type," reused for both what gets *shown* and what gets
*written*):

| Exercise type(s) | Distance | Steps | Elevation |
|---|---|---|---|
| Walking, Running, Running (treadmill) | ✓ | ✓ | |
| Hiking | ✓ | ✓ | ✓ |
| Biking (outdoor) | ✓ | | ✓ |
| Biking (stationary) | ✓ | | |
| Swimming (open water, pool) | ✓ | | |
| Strength training, Weightlifting, HIIT, Yoga, Pilates | | | |
| Everything else (fallback) | ✓ | ✓ | ✓ |

`ActiveCaloriesBurnedRecord` is written whenever
`session.activeCaloriesKcal` is non-null and positive, with no per-type
gate — it is currently always `null` in practice, since neither
`HuaweiHealthManager` nor the archive/CSV import parser populates that field
today (Huawei's activeCalories category is itself scope-gated behind 50005
for this individual-developer account, per `WorkoutCalorieEstimator`'s own
doc comment). The write path handles it correctly regardless, so a future
data source populating it needs no further plumbing change here.

**Applies to every workout, from every import source.** Live sync
(`HuaweiHealthManager.readActivitySessions`) and archive/CSV import
(`HuaweiExportParser`) both produce the same `ActivitySessionData` shape and
flow through this one `writeActivitySessionsBatch()` write path — the fix
covers both without any source-specific code.

**No new Health Connect permissions required.** BitLut already held write
permission for all four record types (`HealthPermissionPolicy`, 4.13),
since they were already being written as background aggregates.

### 4.8 Metadata: `autoRecorded` vs `activelyRecorded`, and device attribution

Two metadata factory functions exist, both building on a shared
`bitlutRecordingDevice = Device(type = TYPE_UNKNOWN, manufacturer = "Huawei")`:

- **`bitlutMetadata(...)`** → `Metadata.autoRecorded(...)`. Used for passive
  background streams (steps, distance, floors, elevation, active calories)
  — data Huawei's sensors produce continuously without explicit user action.
- **`bitlutWorkoutMetadata(...)`** → `Metadata.activelyRecorded(...)`. Used
  for exercise sessions and their calorie/distance/steps/elevation
  sub-records — Huawei documents this data as produced only after the user
  explicitly starts a workout, and Health Connect's own metadata semantics
  distinguish the two cases. Preserving this distinction (rather than
  describing everything as however BitLut itself happened to relay the
  record) matches the *source's* actual recording semantics, which is what
  Health Connect's metadata model is designed to convey to readers.

`manufacturer = "Huawei"` (with `model` deliberately left unset,
`Device.TYPE_UNKNOWN` preserved) was added 2026-08-27, based on Health
Connect's own metadata guidance that supplying manufacturer/model — not just
a bare `type` — "helps with attribution in reader applications, so users can
understand which device or application recorded their data." This was one
of several previously-unaddressed reasons a stricter third-party reader
might decline a record whose device info was empty beyond
`TYPE_UNKNOWN`. "Huawei" (with no specific model) is used because that much
is genuinely true regardless of which specific Huawei phone or wearable
actually recorded the activity — BitLut relays whatever Huawei Health itself
already attributed the data to, and has no reliable per-record model signal
of its own. Guessing a specific model would not be true in the same way.

Every `clientRecordId` is generated by `generateRecordId(type, startTimeMs,
endTimeMs, discriminator)` → `"bitlut_${type}_${startTimeMs}_${endTimeMs}${suffix}"`,
giving every write a stable, deterministic identity independent of process
restarts, so re-syncing the same underlying Huawei data always upserts the
same Health Connect record rather than duplicating it.

### 4.9 `replaceRecords()`: the shared upsert helper

Nearly every write path (everything except the two special cases in 4.4 and
4.6) funnels through one shared helper:

```kotlin
records.chunked(WRITE_BATCH_SIZE).forEach { chunk ->
    client.insertRecords(chunk)
}
```

`insertRecords` **is** an upsert in Health Connect's model when
`clientRecordId` is stable and `clientRecordVersion` is newer than what's
already stored — this is explicitly called out in the code because an
earlier version of this pipeline **deleted** a record by ID before its
first insert, which produced Health Connect's "invalid UID" error (you
cannot delete something that was never inserted with that specific
version). `WRITE_BATCH_SIZE = 400` chunks large batches to stay within
Health Connect's per-call practical limits. `SecurityException` invalidates
the client cache (a stale reference is a plausible cause) and re-throws;
any other exception is logged and returns `false` for that category, letting
`writeSnapshot()`'s per-category failure isolation (4.3) do its job.

### 4.10 The local dashboard sidecar (`workoutSummaryPrefs`) — still needed, and why

A `SharedPreferences`-backed local cache
(`persistWorkoutSummary`/`storedWorkoutSummary`, keyed by
`"$startTimeMs:$endTimeMs"`) stores each Huawei-sourced workout's exact
summary metrics **on-device only**. This exists because `ExerciseSessionRecord`
itself, as a Health Connect record type, carries no distance/calorie/step
fields at all — those live in separate record types. When BitLut's own
dashboard reads workouts back from Health Connect (`readRecentWorkouts()`),
it gets a bare session with no metrics attached; the local sidecar is what
lets the dashboard recover the exact original Huawei numbers without
re-deriving them from Health Connect's own (coarser, aggregate-based)
records.

**This remains fully necessary after the 4.7 interoperability fix and is
not made redundant by it.** The sidecar and the Health Connect sub-records
serve two different consumers through two different mechanisms:

- The sidecar is **local-only**, read only by `readRecentWorkouts()` for
  **BitLut's own UI**, and is never seen by Health Connect or any other app.
- The 4.7 sub-records are **Health-Connect-visible**, written specifically
  so **other apps** can read a workout's real metrics via the standard
  time-range-overlap convention.

`readRecentWorkouts()` never reads the 4.7 sub-records back for display —
it always prefers the local sidecar (`storedWorkoutSummary`) when Huawei/
BitLut is the selected data source, falling back to Health Connect
aggregation (`enrichDisplayedWorkoutMetrics`, 4.12) only for the two most
recently displayed workouts, and only when the sidecar has nothing.

### 4.11 Calorie estimation (`WorkoutCalorieEstimator`) — the one explicit exception to "never fabricate data"

Real per-workout active-calorie data from Huawei requires the
`HEALTHKIT_CALORIES_READ` scope, which BitLut has never requested (its
current scope array is Step/Distance/Activity/ActivityRecord/HistoryWeek
only — see `docs/SCALING_ROADMAP.md` section 3). This is why
`activeCalories` reads return 50005: an unrequested scope, not a denied
one. It is **not** part of the permanently-closed Advanced tier (3.2
correctly lists active calories as part of the individual-developer-
reachable activity tier) and is understood, per Huawei's own developer
documentation, to be unrestricted, quickly-approved Basic-tier data — see
`docs/SCALING_ROADMAP.md` for the request plan. Until that scope is
requested and approved, to give third-party readers *something* non-zero
to import for a workout's total calories,
`WorkoutCalorieEstimator.estimateTotalCaloriesKcal(exerciseType,
startTimeMs, endTimeMs)` computes a standard MET-formula estimate:

```
kcal = MET * 3.5 * 70.0(kg reference weight) * durationMinutes / 200.0
```

MET values are the "general/moderate" variant per exercise type, drawn from
the Compendium of Physical Activities (Ainsworth et al.) — the standard
reference most fitness calorie calculators cite — since Huawei's activity
records carry no separate intensity signal that would justify picking a
different band. The 70&nbsp;kg reference weight is the conventional default
used across MET calculators when no real body weight is available; BitLut
has no access to the user's actual weight, and adding that would introduce
a new data category, which this feature is explicitly scoped to avoid.

This is documented, in the code itself and in
`docs/HEALTH_DATA_PERMISSION_MATRIX.md`, as the **one explicit, deliberate
exception** to this project's otherwise-absolute "never synthesize fake
health data" rule — made only because a plausible-but-labeled estimate
serves interoperability better than a hard zero, and only for total
calories specifically, never for distance, steps, or elevation, which are
always either real Huawei data or omitted. The same formula and MET table
back both the Health Connect write (`estimatedTotalCaloriesKcal`, called
from `writeActivitySessionsBatch`) and the workout card's own calorie
display fallback (`workoutMetricDisplays` in `FinalBitLutShell.kt`) — a
single shared implementation (extracted 2026-08-26) so the two call sites
can never silently drift apart.

### 4.12 Dashboard reads: quota-bounded, aggregate-then-recover

`readDashboardSnapshot()` — BitLut's own read path, structurally separate
from the write path but sharing the same `HealthConnectClient` — is
deliberately quota-bounded. An earlier version drained every page of five
30-day record streams on every dashboard refresh; overlapping refresh
triggers (app resume, manual sync completion, periodic sync completion) could
quickly exhaust Health Connect's request quota. The current version reads
exactly one newest-first page per stream (`readBoundedRecentRecords`,
`READ_PAGE_SIZE = 1000`, `ascendingOrder = false`), and only ever calls
`client.aggregate(...)` for the **two** most recently displayed workout
cards (`enrichDisplayedWorkoutMetrics`), not for the full 30-day ledger.

For those two cards, metric resolution priority is: **session-level data
first** (from `workout.distanceMeters` etc., i.e. the local sidecar, 4.10),
then Health Connect's own `aggregate()` over the exact session window, then
a conservative raw-record-overlap recovery
(`recoverWorkoutDistanceFromRawRecords`) for sessions with no per-activity
Huawei distance at all — padding the query window by two hours
(`WORKOUT_DISTANCE_QUERY_PADDING_SECONDS`), ignoring source records longer
than three hours (`MAX_WORKOUT_DISTANCE_SOURCE_RECORD_MS`, so a daily-scale
background record cannot smear its total into a single workout), and
requiring at least 25 recovered meters (`MIN_RECOVERED_WORKOUT_DISTANCE_METERS`)
before trusting the result at all. This three-tier priority (session →
aggregate → raw-overlap-recovery) exists specifically because trusting the
aggregate *first* previously showed a real 28&nbsp;km bike ride as
0.7&nbsp;km (3.10's bug, from the read side rather than the write side) —
whenever session-level Huawei data is available, it now always wins.

The wider 30-day dashboard ledger (`readDailyActivitySummaries`) reads each
already-approved stream **once**, groups by calendar day locally, and
separately attributes time-overlap fractions of those same records to the
two displayed workout cards — one query per record type, not one query per
workout.

### 4.13 Health Connect permissions requested (`HealthPermissionPolicy`)

Activity-only, matching the Huawei individual-developer ceiling (3.2)
exactly:

```kotlin
Read + Write: StepsRecord, DistanceRecord, FloorsClimbedRecord,
              ElevationGainedRecord, ActiveCaloriesBurnedRecord,
              ExerciseSessionRecord, TotalCaloriesBurnedRecord
```

No sleep, heart rate, SpO2, or stress permission is requested anywhere in
this codebase, matching the hard constraint in 3.2.

---

## 5. Orchestration: making an unattended background pipeline resilient

Everything in this section exists because `readSnapshot()` +
`writeSnapshot()` (sections 3 and 4) run unattended, on real devices, with
real network flakiness, real OEM process death, and Huawei's own
incremental approval model — not because the core read/write logic itself
needed help.

### 5.1 Two independent trigger paths, one shared lease

Sync can be triggered two structurally different ways:

- **Periodic**: `BackgroundSyncScheduler.schedulePeriodic()` registers a
  `PeriodicWorkRequest` for `SyncWorker` every 30 minutes
  (`SYNC_INTERVAL_MINUTES`, 5-minute flex), under the unique work name
  `bitlut_periodic_sync_v2`, with `ExistingPeriodicWorkPolicy.KEEP`. This
  runs on every cold launch (`MainActivity.onCreate` →
  `setupPeriodicSync()`), but `KEEP` deliberately means it does nothing if
  a non-cancelled periodic request already exists — `UPDATE` was tried and
  rejected (5.2) because it can cancel an in-flight run.
- **Manual/on-launch**: `SyncOrchestrator.triggerImmediateSync()` (called
  from `MainActivity` for both the "Sync now" button and automatic
  sync-on-launch) enqueues a **one-time** `SyncWorker` request under the
  unique name `bitlut_sync_now_v2`
  (`BackgroundSyncScheduler.enqueueImmediateSync`).

Because these are two *different* WorkManager unique-work names, WorkManager
itself does **not** serialize them against each other. `SyncRunLease`
(backed by `SharedPreferences`, with a process-wide `Mutex` and a
synchronous `commit()` rather than async `apply()`) is the cross-cutting
guard that actually prevents a periodic and a manual `SyncWorker` instance
from running concurrently and racing on the same Huawei read / Health
Connect write. `SyncWorker.doWork()` calls `lease.tryAcquire(owner, now,
LEASE_TTL_MS)` (10 minutes) before doing any real work; if another owner
already holds it, the worker returns `Result.success(reason =
"sync_already_running")` immediately as a safe no-op — the active worker
already owns the catch-up window, and every write is independently
idempotent (stable `clientRecordId`s throughout), so there is nothing unsafe
about simply deferring.

**Real, confirmed race pattern** (2026-08-31 device log): up to four
separate `SyncWorker` instances were observed starting within about ten
seconds of a single cold launch — one periodic worker (already due) plus
three manual/launch-triggered attempts, each losing the lease race and
returning `sync_already_running` almost immediately, while the periodic
worker did the real ~10-second Huawei read + Health Connect write. This
pattern, once well-understood, is what motivated the sync-activity UI signal
fix in 5.7.

### 5.2 Why `ExistingPeriodicWorkPolicy.KEEP`, not `UPDATE`

`schedulePeriodic()` runs on **every single cold launch**. `UPDATE`
re-applies the periodic request even when it is byte-for-byte identical to
what is already scheduled — and WorkManager can cancel a currently
**RUNNING** instance of that periodic work in order to do so. A real device
log showed exactly this: `"Sync cancelled by WorkManager/system: Job was
cancelled"` firing in the same second as `schedulePeriodic()`'s own log
line, immediately followed by a retry. `KEEP` is a true no-op whenever a
non-cancelled `bitlut_periodic_sync_v2` request already exists, so a normal
cold launch never touches an in-flight periodic run. A one-time
version-migration helper (`clearLegacyPeriodicSyncOnce`) moved existing
installs off the old `UPDATE`-scheduled unique work name exactly once; if
the schedule parameters (interval/constraints/backoff) ever need to change
again, the unique work name itself should be bumped to a new version
(matching the same versioned-migration pattern already used once) rather
than relying on `UPDATE` mid-run.

### 5.3 `SyncWindowPlanner`: incremental cursor with bounded catch-up and overlap

Ordinary metric syncing (steps/distance/floors/elevation/active calories)
uses an incremental cursor persisted as `KEY_LAST_SYNC_MS`. `SyncWindowPlanner.plan()`:

- Falls back to a 24-hour lookback (`DEFAULT_LOOKBACK_MS`) if no cursor is
  saved yet, or if the saved cursor is corrupted into the future (logged as
  a warning and treated as "no cursor").
- Clamps the lookback to a maximum of 7 days (`MAX_LOOKBACK_MS`) even after
  a long gap (app uninstalled and reinstalled, long-idle device, etc.) —
  bounded catch-up, not unbounded.
- Subtracts a 5-minute overlap (`OVERLAP_MS`) from whatever start point is
  chosen, so a metric right at a previous sync's boundary is never missed
  due to a Huawei-side reporting delay. Every downstream write is
  idempotent, so re-reading a small overlapping window on every sync is
  free — it never produces duplicates.

Workout sessions do **not** use this incremental cursor at all — see 5.4.

### 5.4 Workouts always query the full 7-day window

Because workouts are sparse (unlike continuous steps/distance) and Huawei's
granted history scope is exactly one week
(`HEALTHKIT_HISTORYDATA_OPEN_WEEK`, `ACTIVITY_HISTORY_WINDOW_DAYS = 7`),
`readActivitySessions()` is queried over the **complete** allowed 7-day
window on every single sync run, regardless of the incremental
`KEY_LAST_SYNC_MS` cursor used for other metrics. This is safe and
idempotent precisely because of the stable `clientRecordId` + fingerprint-
based versioning scheme (4.6) — a workout synced in five different sync
runs in a row upserts to the same Health Connect record five times, never
duplicating, while ensuring a workout from two days ago that only just
became visible in Huawei Health (late watch sync to the phone, etc.) is
never permanently missed by an incremental cursor that had already moved
past its timestamp.

### 5.5 Retry, backoff, and per-dependency circuit breakers

`SyncWorker.executeWithRetries()` retries a failed sync attempt up to
`SyncRetryPolicy.MAX_ATTEMPTS = 3` times within a single `doWork()`
invocation, using AWS-style exponential backoff with full jitter (delay
drawn uniformly from `[1s, min(2^attempt * 1s, 30s)]`) — full jitter
specifically to prevent concurrent retries (across this worker's own retry
loop, or in principle across multiple devices) from all retrying in
lockstep and creating a thundering-herd spike.

Beyond that in-process retry loop, two **independent, per-dependency**
circuit breakers (`SyncCircuitBreaker`, one for `SyncDependency.HUAWEI`, one
for `SyncDependency.GOOGLE`) track failures across sync *attempts* (i.e.
across separate `WorkManager` job runs, persisted in `SharedPreferences`).
Three consecutive failures (`failureThreshold`) opens that dependency's
breaker for 30 minutes (`openDurationMs`); while open, `SyncWorker.doWork()`
skips the attempt entirely as a graceful no-op rather than repeatedly
hammering a dependency that's already known to be failing. The two breakers
being independent — rather than one earlier monolithic breaker — means a
long-standing Huawei-side issue (e.g. the 50005 pending-approval state) does
not drag down an otherwise-healthy Health Connect dependency's own failure
count, and vice versa.

`SyncDiagnosticLog` persists the last 40 structured sync events
(circuit-open, write-partial-retry, panic, security-exception, etc.) as a
small JSON array in `SharedPreferences`, specifically because
`AppLogger`'s in-memory ring buffer is lost the instant the process dies —
exactly when understanding *why* a circuit breaker opened matters most (the
user reopens the app after a problem and the in-memory history is already
gone).

### 5.6 Genuine full authorization failure vs. partial/incremental approval

`SyncWorker.runSingleAttempt()`'s `catch (e: SecurityException)` block
checks specifically for the `50005` code in the exception message. If
present, `huaweiManager.markAppGalleryVerificationRequired()` is called
(flipping local authorization state back to "pending approval," which
degrades every subsequent sync attempt to a graceful no-op until the user's
own next authorization action, or Huawei's review, resolves it) and the
outcome is `NonRetryableFailure` — this requires user action, not a retry.
Any other `SecurityException` is treated the same way (also
`NonRetryableFailure`) since it also indicates a permission problem needing
user intervention. This is the **fully-denied** case; the **per-category**
partial-denial case (3.3) is handled entirely inside `HuaweiHealthManager`
and never reaches this level, by design — this catch block only ever fires
when `readSnapshot()` itself decided every category was denied.

### 5.7 UI sync-activity signal: a real device log exposed a real gap

**The problem, confirmed on-device (2026-08-31):** `SyncUiState.isSyncing`
was wired **only** to `SyncViewModel.markSyncStarted()`/`markSyncCompleted()`,
which `MainActivity` calls **only** from its two UI-triggered sync paths
(the "Sync now" button, and automatic sync-on-launch via
`SyncOrchestrator.triggerImmediateSync`). `SyncWorker` itself — whether
running as the periodic 30-minute job or a one-time manual job — is a plain
`CoroutineWorker` with no reference to `SyncViewModel` at all; it
structurally cannot flip that flag.

A real device log showed the periodic background worker winning the
`SyncRunLease` race (5.1) and doing the real ~10-second Huawei read + Health
Connect write, while the UI-triggered attempt lost that race almost
instantly: `markSyncStarted()` fired, the worker hit the lease check inside
a second, returned `sync_already_running`, and `markSyncCompleted()` fired
right after — collapsing the entire `isSyncing=true → false` window to well
under a second, far too fast for even a correctly-implemented fade
animation to ever render a visible frame. The "Syncing…" indicator was,
from the user's perspective, simply never appearing, even though real
syncs were completing successfully underneath it.

**The fix.** A new tag, `HuaweiConfig.SYNC_ACTIVITY_TAG`, is applied only to
`SyncWorker`'s two enqueue sites (`schedulePeriodic` and
`enqueueImmediateSync` in `BackgroundSyncScheduler`) — deliberately **not**
the pre-existing, broader `SYNC_WORKER_TAG`, which is also applied to the
unrelated `EveningReminderWorker` (a periodic job that only reads the cached
dashboard snapshot to decide whether to post a notification; it does no
Huawei/Health-Connect I/O and has nothing to do with syncing). Reusing the
broader tag would have made the indicator falsely activate whenever an
evening-reminder job happened to run.

`MainActivity.observeBackgroundSyncActivity()` (called once from
`onCreate()`) observes `WorkManager.getWorkInfosByTagLiveData(SYNC_ACTIVITY_TAG)`,
tied to the Activity's own lifecycle via `LiveData.observe(this, ...)` (no
manual `removeObserver()` needed), and computes "is any tagged work
currently `RUNNING`, `ENQUEUED`, or `BLOCKED`" on every change to that set —
recomputed on every change, not queried once, since WorkManager can hold
multiple tagged requests concurrently (the periodic job plus a
momentarily-enqueued manual one, exactly the 5.1 race). That boolean feeds
a new `SyncViewModel.setBackgroundSyncActive(Boolean)`.

`SyncUiState.isSyncing` is now a **computed property**:

```kotlin
val isSyncing: Boolean get() = isUiTriggeredSyncing || isBackgroundSyncActive
```

— true whenever *either* signal is true, so the indicator now correctly
reflects whichever `SyncWorker` instance, periodic or manual, is actually
doing the real work, independent of which path happened to trigger it.
`isUiTriggeredSyncing`/`isBackgroundSyncActive` are ordinary (not `private`)
constructor properties — deliberately not made `private`, because a
`private` constructor property's generated `copy()` parameter is only
accessible from *inside* that class in Kotlin, not from `SyncViewModel`
even though both live in the same file; Kotlin scopes member visibility to
the class, not the file. `syncStatus` (the specific success/error outcome
message) is left driven only by the UI-triggered path, since that is the
only one that actually observes and can meaningfully report a concrete
result.

### 5.8 Sync status indicator: alpha-only, fixed-height animation

Separately from *whether* `isSyncing` correctly reflects reality (5.7), a
second real-device bug affected *how* it was displayed once true.
`MinimalHeader`'s "Syncing…" status line originally used
`AnimatedVisibility(visible = isSyncing, enter = fadeIn(...), exit = fadeOut(...))`.
Fading opacity alone still lets `AnimatedVisibility` collapse the
composable's layout height to zero the instant it becomes invisible at the
end of the exit animation — this yanked the subtitle text below it upward
the moment a sync finished, a visible, jarring layout jump confirmed on a
real device.

The fix: the status line's `Column` is now **always present**, at a fixed
reserved height (`SYNC_STATUS_LINE_HEIGHT = 18.dp`) — only its `alpha`
animates, via `graphicsLayer { alpha = syncStatusAlpha }` with
`syncStatusAlpha` driven by `animateFloatAsState(targetValue = if (isSyncing)
1f else 0f, ...)`. Presence/layout never toggles; only visual opacity does.
This mirrors the same alpha-only pattern already used elsewhere in this file
(`AugustDestination`'s press-scale `graphicsLayer` in `GlassNavigation.kt`).

---

## 6. Dashboard cache and the midnight-rollover fix

`DashboardSnapshotCache` persists the most recently read
`GoogleDashboardSnapshot` to disk (with `savedAtMs`/`dataChangedAtMs`
timestamps) so the dashboard can render instantly on cold launch, before a
live Health Connect read completes, and so the home-screen widget
(`HomeWidget`, which only ever reads this cache, never calling Health
Connect directly) has something to show between syncs.

**The midnight problem.** If the on-disk cache was last written on a
*previous* calendar day (app closed overnight, etc.), showing its
steps/distance/calories as if they were *today's* numbers is actively
misleading — a new day has genuinely started with zero activity so far.
`DashboardViewModel.buildInitialState()` already guarded against this
(2026-08-26): if `Instant.ofEpochMilli(cached.savedAtMs)`'s local date is
before today, daily-total fields are zeroed (`zeroedDailyTotals()`) while
`recentWorkouts` (real history, not a "today" figure) is left untouched.

**The gap, found via a real device log (2026-08-31).** `refreshFromCache()`
— called both right after a sync's own completion, and from
`SyncOrchestrator`'s lease-collision retry loop (`onDashboardRefresh`, fired
at 8s and 12s after the *deferred* sync's own `sync_already_running` result,
independent of when the *winning* sync's cache write actually lands, per
5.1's race) — applied the cached snapshot **unconditionally**, with no
staleness check at all. Right after midnight, that retry could read the
on-disk cache in the narrow window *before* the winning sync's fresh
write for the new day had landed, silently re-applying yesterday's real
numbers back over the dashboard's already-correctly-zeroed initial state —
for the few seconds until a later refresh (or the winning sync's own
completion callback) corrected it again. A user report matched this exactly:
yesterday's steps briefly reappeared on open, then cleared a few seconds
later when the first sync completed.

**The fix.** The zeroing logic was extracted into a shared
`DashboardUiState.zeroedDailyTotals()` extension, used identically by both
`buildInitialState()` and `refreshFromCache()` — the latter now applies the
same "cached date is before today" check before committing the cache,
zeroing daily totals instead of briefly re-showing yesterday's numbers.

---

## 7. Data model reference

### 7.1 `HuaweiHealthSnapshot` (read-side output)

```kotlin
data class HuaweiHealthSnapshot(
    val steps: List<StepData>,
    val distances: List<DistanceData> = emptyList(),
    val floors: List<FloorsData> = emptyList(),
    val elevations: List<ElevationData> = emptyList(),
    val activeCalories: List<ActiveCaloriesData> = emptyList(),
    val activities: List<ActivitySessionData> = emptyList()
)
```

### 7.2 `ActivitySessionData` (shared shape: live sync AND archive import)

```kotlin
data class ActivitySessionData(
    val startTimeMs: Long,
    val endTimeMs: Long,
    val title: String = "Huawei activity",
    val exerciseType: Int = ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT,
    val distanceMeters: Double? = null,
    val activeCaloriesKcal: Double? = null,   // always null in practice today (4.7)
    val totalCaloriesKcal: Double? = null,
    val elevationMeters: Double? = null,
    val steps: Long? = null
)
```

This is the one shape both `HuaweiHealthManager.readActivitySessions()`
(live sync) and `HuaweiExportParser` (archive/CSV import) produce, and the
one shape `GoogleHealthManager.writeActivitySessionsBatch()` consumes — the
4.7 interoperability fix therefore applies uniformly to both import sources
with no source-specific code.

### 7.3 Health Connect records written per workout (since 2026-08-30/31)

For a single workout, up to six records now share the exact same
`startTime`/`endTime` and are inserted together in one `insertRecords`
call:

1. `ExerciseSessionRecord` — always written (the workout itself).
2. `TotalCaloriesBurnedRecord` — written if a real or estimated total is
   available (4.6, 4.11).
3. `DistanceRecord` — written if the exercise type plausibly has distance
   (4.7 table) and a value is available.
4. `StepsRecord` — written if the exercise type plausibly has steps (4.7
   table) and a value is available.
5. `ElevationGainedRecord` — written if the exercise type plausibly has
   elevation (4.7 table) and a value is available.
6. `ActiveCaloriesBurnedRecord` — written if a value is available (currently
   never, in practice — 4.7).

---

## 8. Known open issues (as of 2026-08-31)

- **Steps can still be missing for some walking/running workouts.** Root
  cause is Huawei-side: `ActivitySummary.dataSummary` appears to sometimes
  emit zero points matching `"steps.total"` for an activity that
  Huawei Health itself clearly recorded steps for. Diagnostic logging is in
  place (3.8); no structural fix has been attempted yet, deliberately,
  pending a real-device log showing what `dataSummary` actually contains
  for a failing activity. **Do not** add a raw-delta-stream fallback for
  steps without that evidence — this project already has one documented,
  hard-won lesson (3.5) that raw step-delta samples are generally
  unreliable for Huawei step totals, and repeating that category of fix
  blind for the per-activity case would risk the same failure mode again.
- **Floors climbed is unsupported on some Huawei device/firmware
  combinations** (3.6) — handled as a graceful, logged per-category skip,
  not a bug to fix.
- **Advanced health categories (sleep, heart rate, SpO2, stress) are
  permanently out of scope** for this individual-developer Huawei account
  (3.2) — not a bug, a fixed platform ceiling. No future work should assume
  this will change.

---

## 9. Standing constraints that shaped every decision in this document

These are restated here because they are the lens through which every
architectural choice above should be read — most of the resilience and
gating logic in sections 3–6 exists specifically *because* these
constraints rule out simpler alternatives:

- **No new Health Connect or Huawei permissions** without explicit product
  approval. Every fix in this document (including the 4.7 interoperability
  fix) works within permissions BitLut already held.
- **No historical sync beyond the existing 7-day window** (5.4) — Huawei's
  own granted history scope ceiling, not an arbitrary choice.
- **No advanced-category code paths** — ever (3.2).
- **Never synthesize fake health data**, with exactly one documented,
  narrow exception: the MET-formula total-calorie estimate (4.11), and only
  for that one field.
- **Real data only in the UI**: a missing metric shows as absent/"—", never
  as a fabricated zero standing in for "no data."
- **Individual-developer Huawei account**: the activity-tier scope ceiling
  (3.2) is permanent, not a temporary review backlog.
