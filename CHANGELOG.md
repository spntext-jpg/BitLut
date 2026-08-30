# Changelog

## 2026-08-29 (b) -- bottom navbar resize, animated background-sync status

- Bottom navbar: Today/Settings destination buttons shrunk ~20% (button
  height 58->46dp, icon 21/20->17/16dp, icon tile 30->24dp, tile radius
  12->10dp); center Refresh (sync) button grown ~20% (60->72dp, icon
  28->34dp). Both destination buttons remain identical to each other
  (shared composable, `Modifier.weight(1f)`), preserving symmetry.
- Today screen header: new "Updating..." status line under the existing
  "<source> - <last sync>" text, shown only while a sync is actually in
  flight (`SyncUiState.isSyncing`, already tracked but never rendered
  before this patch). Fades in/out via `AnimatedVisibility` +
  `fadeIn`/`fadeOut` (`AugustMotion.MediumMs` + `StandardEasing`, the same
  tokens already used elsewhere in this file) rather than snapping.
- New string resource `sync_status_updating`, EN + RU, parity preserved
  (255 keys each locale).
- Delivered as `patch_navbar_resize_v1.py` and
  `patch_sync_status_indicator_v1.py`; both removed after verification per
  standing process (one-off delivery scripts are not kept in the repo).

## 2026-08-29 -- workout interoperability hardening, build/lint recovery, UI cleanup

- Corrected Huawei workout IDs and centralized mapping in `HuaweiWorkoutTypeMapper`; non-workout states are filtered.
- Preserved workout type and available metrics in Huawei archive imports.
- Fixed workout distance source: per-session Huawei activity samples win over coarse Health Connect overlap aggregates.
- Health Connect workouts are written as `ACTIVELY_RECORDED`, use Huawei device metadata, deterministic client IDs/versions, and bundle the exercise session with related total calories.
- Dashboard workout metrics are exercise-type aware: pace for walk/run, speed for cycling, pace/100 m for swimming, elevation for hiking, and duration/calories-focused strength cards.
- Repaired the post-hardening Kotlin regressions, restored two live dashboard helpers, fixed Glance `RestrictedApi` usage, and restored EN/RU resource parity. Final verification is `assembleDebug + lintDebug`; lint is not suppressed or baselined.
- Settings remains intentionally minimal: one data-source selector, one grouped action surface, Health Connect settings deep link, and steps goal only.
- UI refinement keeps the August palette but moves to a quieter 2026 content-first surface model: flat outlined cards, restrained hero depth, pill controls, one primary Settings action, larger icon controls and restrained navigation motion.
- Removed dead CSV-export plumbing, legacy `WidgetVisibilityPrefs` dashboard visibility layer, unused non-step goals, and orphan achievement-summary state.
- Removed one-off patch/hotfix/verify delivery scripts after verification.
- Corporate wellness import remains unresolved. Leading evidence points to reader-side Health Connect source-origin allowlisting; BitLut cannot spoof `Metadata.dataOrigin`.

## 2026-08-22 (d) -- dark-mode invisible icons/text, navbar bounce on every button, biking's 4th metric fixed

Fourth patch of the day, on real-device feedback after the dark theme and
Tangerine/navbar work shipped: several elements were still unreadable in
dark mode, and a bike workout card showed "Steps" as its 4th metric, which
made no sense for cycling.

- Root cause for all dark-mode gray text/icons (Last 7 Days card numbers,
  Personal Records trophy/flame icons, workout-type icons on
  WorkoutRecencyCard, several Settings/onboarding icons): `HealthAccent`
  (`activity`/`mind`/`violet`) was a single fixed `AugustColor.InkSoft`
  alias, correct against light mode's white Surface but never made
  theme-aware. Measured against dark mode's NavyRaised card background,
  InkSoft contrasts at ~1.2:1 -- effectively invisible, matching the report
  exactly. `palette.secondaryText` (used for some of the same labels) was
  already correctly theme-aware before this fix and needed no change --
  the bug was entirely in `HealthAccent`.
- `HealthAccent`'s three properties became `@Composable` functions reading
  `isSystemInDarkTheme()` directly (`HealthAccent.activity` ->
  `HealthAccent.activity()`, etc.), resolving to Lime in dark mode
  (~14.5:1 contrast against NavyRaised, contrast-checked) and unchanged
  InkSoft in light mode. All ~43 call sites across ~15 composables were
  converted from property access to function calls in the same patch.
  `BitPalette.light()`/`dark()` -- plain non-composable factory functions
  that previously also read `HealthAccent.activity`/`.mind` -- could not
  follow the same conversion (a non-composable function cannot call a
  `@Composable` one), so each now hardcodes its own already-correct value
  directly instead (InkSoft for `light()`, Lime for `dark()`).
- Navbar: all three buttons' press-release scale animation changed from a
  flat `tween` to a `spring` (`Spring.DampingRatioMediumBouncy`,
  `Spring.StiffnessMedium`), producing a slight overshoot-then-settle "light
  bounce" on release, as requested for every button. The two side
  destination buttons (Today/Settings) also gained a small icon tilt
  (-8 degrees on press, same spring) as their own distinct press flourish,
  echoing but not literally copying the Refresh button's existing -24-degree
  rotation, which is unchanged.
- Biking's 4th workout-card metric: `workoutMetricDisplays()` now takes the
  session's `exerciseType` and swaps Steps for Elevation gain specifically
  for `EXERCISE_TYPE_BIKING` (confirmed choice over Active Calories --
  elevation is more semantically meaningful for cycling despite being, like
  Steps, frequently unpopulated for a given ride; falls back to `--` same as
  every other slot). This re-introduces `workout_stat_elevation_label` /
  `workout_elevation_value` to `strings.xml` (en+ru), correctly removed as
  dead code by the four-metrics patch three days ago -- a deliberate,
  same-project follow-up reversal driven by new product direction, not an
  accidental duplicate of already-completed work. Active Calories is
  untouched: still dropped from the card entirely everywhere else, still
  scope-denied by Huawei independent of exercise type.
- Found and fixed in passing: `scripts/verify_workout_nav_freshness_sprint.py`
  still asserted the retired `AugustColor.LimeActive` string for the navbar
  Refresh button's pressed-fill token -- the Tangerine patch earlier this
  week (see below) changed that token to `AugustColor.TangerineActive` but
  never updated this assertion, which had been silently failing since that
  patch landed. Unrelated to today's five requests; fixed while already in
  this exact file for the elevation-related assertion updates.

## 2026-08-22 (c) -- Steps Hero two-value layout, Tangerine accent, narrower navbar

Third patch of the day. Three independent, confirmed UI changes.

- Steps Hero card: Distance now renders as its own big-number +
  small-"km" block, the same visual weight as Steps, instead of being
  folded into Steps' small trailing unit string ("steps · 0.1 km"). New
  `StepsHeroCard`/`HeroMetricBlock` composables handle this; `MinimalMetricCard`
  itself is untouched and stays in use everywhere else it already appeared
  (Connect Google lock screen, the Distance card inside
  `DashboardOrderedCard`, etc.) -- this is a dedicated Hero-only composable,
  not a generalization of the existing one. The steps-goal progress ring
  moved below both numbers instead of sitting beside them, since two
  big-number blocks plus a ring all competing for one row was too tight
  once Distance became first-class instead of trailing text. Added
  `distance_unit_km` string (en+ru) -- `distance_today_value` bundles the
  number and "km" into one template string, which is exactly why Distance
  couldn't be split into a big number + small unit before this patch.
- New `AugustColor.Tangerine`/`TangerineActive` tokens: replaces Purple as
  the "on/active" signal in exactly two places -- the two Settings toggle
  tracks (`DataSourceToggleRow`, `WidgetVisibilityRow`) and the navbar's
  center Refresh button fill (was Lime). Purple keeps every other existing
  role (focus rings, links, selection detail) untouched, including the
  navbar's own focus-visible ring. `#F28500` is the commonly documented
  "Tangerine" named color (ColorHexa/Wikipedia's canonical value), not any
  single company's brand orange. `TangerineActive` (`#DD7A00`, the Refresh
  button's pressed-state fill) is derived by applying the same relative HSV
  saturation/value shift that produces `LimeActive` from `Lime`, not
  eyeballed. Ink-on-Tangerine clears ~6.9:1 WCAG AA; white-on-Tangerine
  fails at ~2.6:1, so the Refresh icon moved from `LimeInk` to the
  equivalent `Ink`.
- Navbar: outer horizontal margin increased 16.dp -> 24.dp
  (`NAV_BAR_OUTER_HORIZONTAL_MARGIN`) so the two side destination buttons
  shrink and the pill reads narrower -- a deliberately conservative first
  pass, not the ~44.dp a literal "20% narrower" derivation would produce on
  a typical ~400.dp-wide screen, since that number could not be visually
  verified in this environment. The Refresh button itself grew 15%
  (58.dp -> 67.dp, icon 27.dp -> 31.dp) to read as the dominant middle
  action against the now-narrower side buttons.
- Found and fixed in passing: one pre-existing unused import
  (`AugustColor.AugustRadius`) in `GlassNavigation.kt` -- every shape in
  that file uses a raw `RoundedCornerShape(N.dp)` literal, never
  `AugustRadius.*`, verified by grep before removal.

## 2026-08-22 (b) -- August v3 dark theme activated, driven by system appearance

Second patch of the day. `BitPalette.dark()` already existed in
`FinalBitLutShell.kt` but was completely unreachable: the one call site was
hardcoded to `BitPalette.light()`, and two separate verify-script guardrails
explicitly asserted that OS dark mode must NOT be wired up. This was mostly
"finish and activate a dark theme someone already half-built," not a
from-scratch design.

- New `AugustDarkScheme` (`darkColorScheme(...)`) in `BitLutExpressiveTheme.kt`,
  wired to `isSystemInDarkTheme()`; status bar color and icon contrast now
  follow the active scheme. Dark Canvas = Navy, dark Surface = NavyRaised,
  dark Soft = NavySoft -- extending the existing Navy ramp's role rather
  than inventing a second, unrelated dark palette, matching the light
  scheme's own Canvas -> Surface -> Soft elevation relationship, just
  inverted. The source August v3 doc (re-attached this session) has no
  "dark mode" section of its own -- it only specifies Navy as a permanent
  architectural anchor inside an otherwise light-canvas product (a
  different product, a web media tool) -- so this dark theme's actual
  surface mapping is this session's own design decision, not a literal
  doc translation.
- Every reused color pairing checked against real WCAG contrast math before
  reuse, not eyeballed: Surface/DarkSecondaryText/Lime/Ink all clear 7:1+
  against Navy/NavyRaised/NavySoft. `DangerFg` (tuned for white) drops to
  2.62:1 on NavyRaised and was deliberately NOT reused for dark error text;
  `AugustColor`'s pre-existing but previously-unused `DarkErrorContainerFg`
  (`#FFC9C9`) is used instead, clearing 11:1+ against both Navy and
  NavyRaised.
- Confirmed product decisions (not inferred): Lime stays a filled surface
  with Ink text in both modes; the Steps Hero card stays NavyRaised
  unchanged in both modes (`SoftCard`'s `hero` branch in `GlassCards.kt`
  already hardcoded `NavyRaised` independent of `palette`, so it needed no
  change at all).
- Flipped the two verify-script guardrails in
  `scripts/verify_sync_august_v3_recovery.py` that explicitly forbade dark
  mode; added assertions for the new `AugustDarkScheme` content itself.
- Found and fixed in passing: a stale comment in `MainActivity.kt` that
  described an `isSystemInDarkTheme()` call inside `FinalBitLutShell` which
  did not actually exist anywhere in the codebase before this patch; two
  already-broken, unrelated verify-script assertions in
  `scripts/verify_reliability_and_design_sprint.py` (a `sleep =
  HealthAccent.sleep` check referencing a field removed by an earlier
  sleep-feature removal, and a `LightShadowTint` check referencing a symbol
  that no longer exists after `GlassCards.kt`'s phase-2 rewrite); one
  now-dead `glass_cards` file-read variable in that same verify script,
  orphaned by removing its only two checks.

## 2026-08-22 (a) -- workout cards narrowed to four metrics for every exercise type

First patch of the day, prompted by a real-device diagnostic log review.
The log's "last workout shows wrong steps, no distance" turned out to be
confirmed-expected data staleness, not a bug: that workout was more than 7
days old, outside BitLut's continuous per-minute Huawei sync window, and its
`steps=251` figure was a legitimate Health Connect aggregate over a
historical interval with genuinely sparse underlying Huawei source data
(0 distance points, 0 activeCalories, separately scope-denied). No code
path was misbehaving; this matches the project's own "do not reopen the
workout-distance fallback" rule.

- The requested change instead: `workoutMetricDisplays()` rewritten to drop
  Active Calories and Elevation gain from the workout card display
  entirely (not conditionally hidden -- removed as a display contract) for
  ALL exercise types, leaving Duration, Distance, Avg speed, Steps.
  Rationale: Huawei `activeCalories` is frequently scope-denied (50005) and
  elevation is rarely populated for the same reason, so the old six-slot
  layout mostly showed four real values and two permanent dashes.
  `ActivitySessionData.activeCaloriesKcal`/`.elevationMeters` are unchanged
  -- still read/synced for CSV export and daily totals; only this card's
  display was narrowed.
- `WorkoutStatsGrid`'s cap changed from `metrics.take(6)` to `metrics.take(4)`.
- Removed the now-dead `workout_stat_calories_label`/`workout_calories_value`/
  `workout_stat_elevation_label`/`workout_elevation_value` strings (en+ru) --
  nothing referenced them after the display change. (Two of these four were
  re-added three patches later the same day for biking's 4th metric; see
  2026-08-22 (d) above -- a deliberate follow-up, not a mistake undone.)
- Updated `scripts/verify_workout_nav_freshness_sprint.py`, which had
  hard-coded the old six-slot contract as a regression gate; left unpatched
  it would have permanently failed after this legitimate change.

## 2026-07-22 -- partial Huawei scope denial no longer discards the whole sync

Real device log evidence this time: `localHuaweiAuthorized=true`, with
steps (176 points) and distance (232 points) both read and deduplicated
successfully -- the first confirmed real-device authorization success in
this project's history. In the same sync attempt, `activeCalories` alone
failed with `HUAWEI_SCOPE_UNAUTHORIZED` (50005), while steps/distance/
elevation succeeded -- Huawei approves scopes incrementally, and the code
did not handle that.

- Root cause: `HuaweiHealthManager.readSnapshot()` built its
  `HuaweiHealthSnapshot` by evaluating all 6 category reads as constructor
  arguments in one expression. A `SecurityException` from any one of them
  (deliberately re-thrown by `readPointsRaw()`, "propagate to caller") threw
  out of the whole function, discarding every already-successfully-read
  category. `SyncWorker`'s catch block then called
  `huaweiManager.markAppGalleryVerificationRequired()` unconditionally on
  ANY 50005 -- which sets `isAuthorized=false`/`pendingApproval=true` --
  incorrectly resetting a *correctly obtained* authorization state back to
  "not authorized," so every subsequent sync attempt regressed to a full
  graceful no-op without even trying to read data again.
- Fix: `readSnapshot()` now reads each of the 6 categories (steps,
  distance, floors, elevation, activeCalories, activitySessions)
  independently, catching `SecurityException` per category and simply
  skipping that one (same graceful-degradation shape already used for
  floors on SDKs without a floors DataType). Authorization is only treated
  as fully denied -- re-throwing to trigger `SyncWorker`'s existing 50005
  handling exactly as before -- if EVERY category comes back denied with
  zero successes. A partial denial now proceeds normally with whatever
  categories ARE authorized, and no longer touches the persisted
  authorization state at all.
- Updated the stale comment on `readPointsRaw()`'s `SecurityException`
  re-throw (previously said "must propagate to SyncWorker" -- it now
  propagates to `readSnapshot()`, which decides skip-one-category vs.
  fully-unauthorized, not directly to `SyncWorker` for a single-category
  failure).
- Updated CLAUDE.md: refreshed "Current status" (first confirmed real
  device auth success; this fix), corrected Gotcha 13's now-stale "working
  theory" framing, added Gotcha 14 documenting the exact bug and fix.

## 2026-07-18 -- Huawei auth failure reasons + retry button (post-AppGallery-rejection)

Triggered by a real AppGallery review rejection: "does not collect to
Huawei Health successfully." The test evidence quoted was BitLut's own
`toast_huawei_pending` string, confirmed via exact text match -- meaning
the reviewer hit the same 50005 wall real devices had shown for weeks, with
no way to tell from that one message which of 5 different HMS failure
codes was actually in play (all 5 triggered the identical toast).

- Added `HuaweiAuthFailureReason` enum (`SCOPE_PENDING_APPROVAL`,
  `PRIVACY_NOT_ACCEPTED`, `CERTIFICATE_MISMATCH`, `INVALID_CONFIGURATION`,
  `UNKNOWN`) to `HealthDataContracts.kt`, plus `lastAuthFailureReason()` on
  `HuaweiHealthReader`.
- `HuaweiHealthManager.handleAuthorizationResult()` now classifies and
  persists the specific reason via a new `classifyFailure()` mapping (HMS
  codes 50005/50011/907135702/6003/907135000 -> the enum above), separately
  from the pre-existing `isAuthorized()`/`isPendingApproval()` booleans.
- Generalized the Settings screen's single 50005-only explanation card
  (`HuaweiPendingApprovalCard`) into `HuaweiAuthIssueCard`, which shows the
  right explanation for whichever of the 5 reasons actually happened --
  previously the other 4 cases showed nothing at all in Settings, just the
  same generic toast.
- Added a "Try connecting again" retry button on the card, shown only for
  `SCOPE_PENDING_APPROVAL` and `PRIVACY_NOT_ACCEPTED` (the two reasons a
  fresh attempt can plausibly fix) -- deliberately not shown for
  `CERTIFICATE_MISMATCH`/`INVALID_CONFIGURATION`, which need an AppGallery
  Connect-side fix first and would just fail the same way again.
- Replaced the old generic `toast_huawei_pending` toast (now dead, deleted)
  with `toast_huawei_failed`, which points to Settings for the specific
  explanation instead of trying to cram reason-specific detail into a
  fleeting Toast.
- Added `huawei_reason_*_title`/`_body` string resources for the 4
  previously-unhandled reasons, plus `huawei_retry_connect`, in both
  `values/strings.xml` and `values-ru/strings.xml`.
- Removed the now-dead `SyncUiState.isHuaweiPendingApproval` boolean field
  (fully superseded by `lastHuaweiAuthFailureReason`, confirmed zero
  remaining reads via grep) and its population in `refreshStatuses()`.

Separately: while this fix was in progress, Huawei approved BitLut's
Health Kit scope application at the app level (App ID 117824685). Device
logs taken immediately after still showed `localHuaweiAuthorized=false`/
50005 -- expected, not a regression, since that's a locally-cached flag
from the last real OAuth attempt, decoupled from the server-side approval
(see CLAUDE.md Gotcha 12). The new retry button exists specifically to
make the next required action -- a fresh authorization attempt -- obvious,
since Huawei's approval notification arrives outside the app entirely and
BitLut has no way to detect it on its own.

## 2026-07-16 -- two real-device hotfixes: widget colors, edge-to-edge insets, widget stuck while pending

Two separate real-device reports after the 2026-07-14 sprint below shipped,
each root-caused from device logs/screenshots rather than guessed.

**Widget colors (`Gradle compileDebugKotlin` failure, caught before commit)**
- `ColorProvider(day = Color(...), night = Color(...))` does not exist in
  `glance-appwidget:1.1.1` -- only `ColorProvider(color: Color)` and
  `ColorProvider(resId: Int)` do (see CLAUDE.md Gotcha 9). Switched
  `widget/HomeWidget.kt` to resource-qualified colors instead: added
  `widget_card`/`widget_text`/`widget_secondary_text` to both
  `values/colors.xml` (light) and a new `values-night/colors.xml` (dark).

**Edge-to-edge inset regression ("Copy button half covered" in Log Viewer)**
- `PermissionsOnboardingScreen` and `LogViewerScreen` both render as
  siblings of the main `Scaffold`, not through its content slot, so they
  never got the Scaffold's automatic safe-area inset padding -- invisible
  before `enableEdgeToEdge()`, a real visible bug the moment it shipped
  (see CLAUDE.md Gotcha 10). Fixed with `.statusBarsPadding()`/
  `.navigationBarsPadding()` on both screens' root `Box`. The 2026-07-14
  sprint's own new `DataScopesScreen` was unaffected -- it renders inside
  `SettingsScreen`, inside the Scaffold's own padding.

**Home screen widget stuck showing nothing while Huawei stayed pending**
- `SyncWorker` only ever called `refreshDashboardCacheAfterWrite()` (the
  function the widget's data ultimately comes from) deep inside the
  Huawei-sync-succeeded branch. While Huawei was pending -- true for weeks
  -- that branch was never reached, so the widget stayed stuck indefinitely
  even though Health Connect could already contain real data from other
  apps regardless of Huawei's state (see CLAUDE.md Gotcha 11). Fixed by
  calling the refresh on the `isPendingApproval()` and
  `!localHuaweiAuthorized` graceful-no-op paths too.
- Investigated but deliberately did NOT change: a separately reported
  "sync only works after opening Google Fit first" symptom. Traced
  `DashboardViewModel.load()`'s live `readDashboardSnapshot()` call and
  confirmed it does not depend on Huawei's auth state at all -- with
  Huawei still blocked at the time, BitLut could not have been writing the
  data being seen, so it was very likely coming from another app (Google
  Fit) that may only push to Health Connect when opened. Not a BitLut bug
  as far as the evidence showed; worth re-checking once Huawei sync is
  actually live and BitLut itself is writing on its own schedule.

## 2026-07-14 -- Sprint 2: edge-to-edge/predictive back, trust screen, Huawei pending-approval card, CSV export, home screen widget

Delivered as two scripts: Part 1 (no new Gradle dependency) and Part 2 (the
home screen widget, which adds `androidx.glance:glance-appwidget:1.1.1`),
kept separate specifically so a problem in the higher-risk widget piece
wouldn't block the other four.

**Edge-to-edge + predictive back**
- `MainActivity.onCreate()` now calls `enableEdgeToEdge()` before
  `setContent`. `AndroidManifest.xml`'s `<application>` tag gained
  `android:enableOnBackInvokedCallback="true"` for the predictive back
  gesture. targetSdk stayed at 35 (not bumped to 36) since the current AGP
  version doesn't support compileSdk 36.

**"What data is shared" trust screen**
- New `DataScopesScreen` composable, reachable any time from a link in
  Settings (not a one-time onboarding step) -- lists the actual 5 Huawei
  Health Kit scopes BitLut requests, matching `requestedScopeNames()`
  verbatim in substance, plus a one-line statement that everything goes to
  Google Health Connect on-device and nowhere else. Answers the most common
  complaint pattern in reviews of similar sync apps: "I don't understand
  what's being synced where."

**Huawei pending-approval status card**
- `SyncUiState` gained `isHuaweiPendingApproval`; a new
  `HuaweiPendingApprovalCard` in Settings explains the 50005 wait state in
  plain language instead of a silent no-op degrade, so a new install
  doesn't read "no data" as "broken." (Generalized into
  `HuaweiAuthIssueCard` on 2026-07-18 above -- this card's specific name
  and single-reason scope no longer exist as of that date.)

**CSV export**
- New `util/CsvExporter.kt`: writes daily totals (`GoogleHealthManager.
  readDailyTotals()`, added alongside it, same raw-records-not-aggregate
  pattern as the dashboard) plus recent workouts to a CSV in `cacheDir/
  export/`, handed off via a new `FileProvider` (`res/xml/file_paths.xml`)
  to the system share sheet. Reachable from a link in Settings.

**Home screen widget (Jetpack Glance)**
- New `widget/HomeWidget.kt` + `HomeWidgetReceiver`: one tile, today's
  steps + last-sync time, tap anywhere enqueues the same
  `BackgroundSyncScheduler.enqueueImmediateSync` work request the Settings
  "Sync now" button uses. Reads `DashboardSnapshotCache` only, never Health
  Connect directly, so `provideGlance()` stays cheap. New
  `res/xml/home_widget_info.xml` provider info (2x1 cell, 30-minute
  fallback `updatePeriodMillis`, real refresh driven by `SyncWorker`
  calling `updateAll()` after every successful cache write).

## 2026-07-14 -- full removal sprint: sleep/HR/SpO2/stress + History deleted outright

Follow-up to the 2026-07-10 series. That sprint removed History from the
bottom nav and stubbed sleep/heart-rate/SpO2/stress fields to empty/null,
but deliberately left the underlying code in place, dormant, as minimal-diff
precedent. This sprint changes that precedent for code proven to be
permanently dead (see CLAUDE.md Gotcha 8) and deletes it outright instead.

**Sleep / heart-rate / SpO2 / stress -- removed in full**
- `GoogleDashboardSnapshot`, `DashboardUiState`, and `DashboardSnapshotCache`
  no longer carry `sleepHours`, `sleepQualityScore`, `heartRateBpm`,
  `heartRateTodayBars`, `stressScore`, `spo2Percent`, `sleepBars`, or
  `heartRateBars` fields at all -- previously these existed and were just
  hardcoded to `0.0`/`null`/`emptyList()`.
- `HealthAccent.heart` deleted outright (confirmed zero real UI usage --
  only ever referenced by the also-deleted `BitPalette.heart` mapping).
  `HealthAccent.sleep` renamed to `HealthAccent.violet`: it *was* live UI
  (the Manual Sync card's accent color in Settings), just never actually
  representing sleep data, so the color stays and only the misleading name
  goes. `BitPalette.sleep`/`BitPalette.heart` fields deleted (confirmed
  zero reads anywhere, only ever assigned).
- Corrected a stale doc comment above `HealthAccent` describing a "Sleep
  progress ring on Summary" that had not existed in the UI for several
  sprints, and two similarly stale comments in `MinimalSquareTile`/
  `ProgressRingChip` referencing a "Heart/Sleep" 2x2 grid and "Sleep vs the
  8h reference" that describe a design that was never actually shipped.
- Removed 8 dead sleep/heart-rate-named string resources (`bpm`,
  `bpm_unit`, `avg_bpm_7d`, plus 5 History-only strings listed below) from
  both `values/strings.xml` and `values-ru/strings.xml`, confirmed unused
  via a full `R.string.<name>` grep first.

**History -- removed in full, not left dormant**
- Deleted `HistoryScreen`, `HistoryRangeChips`, and `WorkoutTypeCard`
  composables from `FinalBitLutShell.kt` (confirmed unreachable from the
  `MainTab` enum / nav dispatch -- History was already removed from the
  bottom nav in the 2026-07-10 sprint, this just finishes the job).
- Deleted the bar-chart infrastructure that existed solely to feed
  History's chart, once confirmed to have zero other callers: `MetricBar`
  data type, `computeMetricBarRanges`/`bucketsOfEqualSize`/
  `calendarMonthBuckets`, `readStepsBars()`, `readWorkoutSummariesByType()`,
  `MiniSparkline`, `formatBarValueShort()`, `barDateLabel()`. Deleted the
  entire `ui/components/MetricCharts.kt` file (existed only for the now-gone
  `MetricBarChartCard`) and the standalone `MetricBarReflectionTest.kt`
  scratch file (only exercised the now-gone `MetricBar` type).
- Removed the `stepsBars`/`workoutSummaries` fields from
  `GoogleDashboardSnapshot`/`DashboardUiState` and their
  `DashboardSnapshotCache` JSON (de)serialization -- these existed only to
  feed the deleted History chart and per-type workout list.
- Removed `HISTORY_RANGE_OPTIONS`, `DashboardViewModel.onHistoryRangeSelected()`,
  `DashboardUiState.selectedHistoryRangeDays`, and the
  `onHistoryRangeSelected` parameter/wiring through `FinalBitLutShell` and
  `MainActivity`.
- `HealthConnectManager.readDashboardSnapshot()` lost its `daysBack`
  parameter (in the interface, the `GoogleHealthManager` implementation,
  and the `SyncWorker` call site that had hardcoded it to `7` anyway) --
  it was only ever there to plumb History's range-chip selection through,
  and had been fully unused inside the function body since the 2026-07-10
  trim.
- Removed 6 dead History-named string resources (`tab_history`,
  `history_title`, `history_subtitle`, `history_short_title`, `tab_7days`,
  `history_title_final`) plus 3 more that were dead *and* referenced the
  removed screen in their text (`permissions_body`, `onboarding_step5`,
  `connect_google_history_body`) from both locale files, and reworded
  `widget_visibility_section_body` to drop its now-inaccurate "...and in
  history" clause.
- Updated `CLAUDE.md` to match: Gotcha 8's "deliberately unused, don't
  clean up reflexively" list no longer includes anything from History
  (only `DashboardWidgetGrid`/`WeeklyComparisonCard`/
  `readWeekOverWeekComparison` remain dormant by that precedent -- unrelated
  to today's change, still awaiting a possible future UI return).

## 2026-07-10 -- sync reliability + UI simplification sprint series

Six days, one continuous thread: get the log-viewer build green, get the
HUAWEI Health Kit application resubmitted cleanly, then chase a sync
freshness bug through five distinct real root causes using actual device
logs rather than guessing. Ends with a fully working, tested sync pipeline
that is simply waiting on HUAWEI's own scope approval to show real data.

**Build fix**
- Added the missing `collectAsStateWithLifecycle` import that broke the
  log-viewer build (the other two reported compiler errors were cascades
  from this one, not separate bugs).

**HUAWEI Health Kit application**
- Diagnosed the "Basic activity management permission and scenario
  description are not provided" rejection: Huawei's Data Usage Scenario
  tab requires a description for every checked scope, matched 1:1 -- ours
  was missing for the already-approved basic scope.
- Confirmed individual developers cannot access HUAWEI's advanced data tier
  (sleep/heart-rate/SpO2/stress) at all, regardless of application quality
  -- dropped those from scope entirely rather than fighting an unwinnable
  approval.
- Drafted the Data Usage / App Info / Self-Check sheet content for the 5
  scopes actually used in code (Step, Distance/ascent/altitude, Activity
  record, Activity, Reading historical data).

**Health-data cleanup**
- Removed 24 unused sleep/heart-rate/SpO2/stress string resources (in both
  `values/strings.xml` and `values-ru/strings.xml`) left over from before
  the activity-only pivot -- confirmed unused via a full grep for
  `R.string.<name>` across every `.kt` file first.
- Fixed a stale README section that falsely described pulse/sleep/SpO2/
  stress as currently-working features; removed 4 stale rows from the
  "supported Health Connect records" table for the same reason.

**History screen removed**
- The unresolved "history bars don't update on range toggle" bug was never
  fully root-caused; the screen was removed from the bottom nav entirely
  instead (2-tab nav: Today, Settings). Its composables/view-model logic
  were left in place, unreachable, not deleted.

**Sync reliability chase (chronological, each one a real fix to a real
regression, found from actual device logs)**
1. Cold launch showed cached data with no auto-refresh -> added an
   automatic Huawei -> Health Connect sync trigger.
2. That trigger only ran once (`onCreate`, once per process) -> moved to
   `onResume()` so every return to the app re-triggers it, not just the
   first one.
3. A lease-collision race meant a no-op "already syncing" result could
   trigger a premature dashboard refresh before the real sync had actually
   finished writing -> `SyncOrchestrator` now checks the completion reason
   and defers follow-up refreshes instead of refreshing immediately on a
   no-op.
4. Concurrent permission checks at cold launch could produce a false
   "permissions missing" flash -> coalesced behind a mutex + 3s cache in
   `GoogleHealthManager`.
5. Root cause of "only fresh after opening Google Fit first":
   `HealthConnectClient.aggregate()` is a provider-side cache that lags
   behind recent writes -> switched steps/distance/calories reads to raw
   `readRecords()` + manual sum, matching the pattern already used
   (correctly) by workout-minutes/active-hours reads.
6. Root cause of "sync got worse, widgets disappear, Connect Health Connect
   flashes": `DashboardViewModel.load()` was making ~16 Health Connect calls
   per invocation, including ~9 for screens/cards removed from the UI
   sprints ago (`stepsBars` alone was one call per day in range) -> trimmed
   to only what's actually rendered, and added a 5-second debounce on
   manual/resume sync triggers. A real device log showed 11+ triggers in 60
   seconds before this fix; confirmed gone after.
7. `DashboardViewModel.load()` was catching its own routine
   `CancellationException` (from cancelling a superseded prior call) as a
   generic error, logging noise and forcing `isLoading=false` on jobs that
   were only ever superseded -> re-throw `CancellationException` before the
   generic catch, matching the guard already used everywhere else in this
   codebase.

Confirmed via a clean final device log: no rate-limit errors, no swallowed
cancellations, no foreground-only read failures. The only remaining blocker
to real data is HUAWEI's own scope approval (`localHuaweiAuthorized=false`,
error 50005) -- not a code issue.

**UI simplification sprint**
- Today screen fixed to exactly 5 widgets matching the actual data scope:
  steps today, workout time, personal records, streak, last imported
  workout. Removed the calories/active-hours mini-grid and the
  week-over-week comparison card from the UI (their code was left dormant,
  see the trimming fix above for why the *data calls* also had to go, not
  just the UI).
- Both remaining screens switched from scrolling `LazyColumn` to a fixed,
  compact `Column`. Settings: connection cards dropped their body/status
  text (title + icon only), Connect/Refresh buttons compacted onto one row
  each. Daily goals moved to the top of Settings, calories dropped from it.
  Widget-visibility toggle section removed entirely -- widget set is fixed
  now, not user-configurable.
- Added a centered, larger (66dp vs 54dp), warm-orange manual refresh
  button to the bottom nav, wired to the same action as Settings' "Sync
  now".
- Fixed the steps-today value font clipping past 10,000 (dynamic font size
  based on formatted string length instead of a fixed 56sp).