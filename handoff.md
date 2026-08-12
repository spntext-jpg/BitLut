# BitLut — Session Handoff (2026-08-05 → 2026-08-11)

This document is a dump of one long working session, meant to bootstrap a **new** conversation (the person's stated plan for that next session is a design pass, not more feature plumbing). Paste/attach this alongside the repo's own `CLAUDE.md` and `SESSION_HANDOFF.md` — this file is a supplement covering what happened in *this* session specifically, not a replacement for the persistent project brief.

---

## ⚠️ READ THIS FIRST: current build status is NOT confirmed green

The last **confirmed-working** checkpoint was after `fix_cold_launch_sync_reliability.py` — the person said "Сейчас всё нормально" (everything's fine now) at that point.

Every script after that point (`remove_elevation_card.py` through `fix_composable_context_error.py`, see timeline below) has been delivered and rigorously tested *in the assistant's sandbox* (see Methodology section — programmatic diff generation, idempotency-checked, byte-diffed against a hand-edited mirror), but **the person has not yet confirmed a successful real build after the most recent fix** (`fix_composable_context_error.py`). Two real bugs were found and fixed along the way (see below) — there is a real chance a third one is still lurking, since none of this has been visually tested on a device, only compiled.

**First action in the new session: ask for the current `:app:compileDebugKotlin` output (or confirmation it's green) before doing anything else.** If it's still red, fix that before touching anything else — do not layer new work on an unconfirmed build.

---

## What BitLut is (quick orientation)

Free, open-source, ad-free Android app that reads activity data (steps, distance, active calories, elevation/floors, workout sessions — **not** sleep/heart-rate/SpO2/HRV/stress, permanently unavailable under the individual-developer Huawei registration tier) from Huawei Health via Huawei Health Kit, and writes it into Google Health Connect so other apps on the device can read it. Published on Huawei AppGallery. Solo non-specialist developer (Paulo), works in Russian, all code/comments/commits in English, UI strings in both `values/` (EN) and `values-ru/` (RU).

**Hard constraint carried into every session:** never expand the Health Connect / Huawei permission scope without it being an explicit, deliberate decision — everything built this session works within the *existing* granted scope (steps, distance, active calories, elevation, floors, exercise sessions).

**Workflow convention (unchanged, load-bearing):** every change is delivered as a standalone Python patch script, run directly by the person from the repo root in their GitHub Codespace. Never inline diffs, never manual edits requested of the person. Scripts back up touched files, apply text-anchored edits, gate `git commit && push` behind a successful `./gradlew :app:compileDebugKotlin`.

---

## Session timeline — scripts delivered, in order

Run in this order if reproducing from scratch (later scripts assume earlier ones already applied, though most are independent enough to tolerate reordering — the two bugfixes specifically target damage from the two scripts immediately before them).

| # | Script | What it did | Status |
|---|--------|-------------|--------|
| 1 | `fix_workout_icons_and_achievements.py` | Fixed workout card icons (was always the running icon regardless of type — added `workoutIcon(exerciseType)` mapping). Removed the Achievements card entirely (call site + composables + strings) per request. | ✅ Confirmed applied |
| 2 | `fix_cold_launch_sync_reliability.py` | Fixed 3 real, log-diagnosed cold-launch sync bugs: (a) `MainActivity.onResume()` had no guard against system permission/auth screens returning, causing sync-trigger stampedes — added `awaitingSystemResult` flag; (b) `BackgroundSyncScheduler.schedulePeriodic()` used `UPDATE` policy, which could cancel an in-flight periodic run on every cold launch — switched to versioned `KEEP`; (c) Huawei Health Kit calls right after cold launch could race the client's own connection handshake — added `retryOnConnectionRace()`, wraps both the daily-step-summation and activity-session reads, up to 2 retries. | ✅ Confirmed applied ("Сейчас всё нормально") |
| 3 | `remove_elevation_card.py` | Removed the "Подъём"/Elevation card from the Today screen per request (call site + `ElevationSummaryCard`/`elevationAndFloorsText`/`InsightValueRow` composables + unused strings). Kept `dashboard_elevation_value` — still used by `PersonalRecordsCard`. | Delivered, not explicitly confirmed |
| 4 | `add_workout_pace_and_filter.py` | Added per-session distance (bulk `DistanceRecord` read + time-overlap attribution, **not** one query per session — avoids the rate-limit-cascade class of bug) → pace on workout cards. Redesigned `WorkoutRecencyCard` to a max-4-stat grid (When/Duration/Distance/Pace). New `WorkoutFilterPrefs` (min duration + excluded exercise types), applied in `GoogleHealthManager.writeSnapshot()` before writing sessions — steps/distance/calories for that time are unaffected. Settings UI is self-contained (local state + direct `WorkoutFilterPrefs` reads), not threaded through the ViewModel. | Delivered, not explicitly confirmed |
| 5 | `add_activity_rings_and_goal_progress.py` | Wired the Steps card's already-built-but-unused `ProgressRingChip` (`progress` param was never passed) + added "N to go / goal reached" text. New "Activity rings" card: 3 concentric animated rings (steps/active minutes/calories) using `DashboardUiState.stepsProgress/activeMinutesProgress/caloriesProgress`, which already existed, fully computed from `GoalPrefs`, just never consumed anywhere. New "Daily goals" Settings section with +/- steppers, wired to `DashboardViewModel.setStepsGoal/setActiveMinutesGoal/setCaloriesGoalKcal` — these already existed too, with a doc comment literally saying "Called from the Settings goals editor," which never existed until this script. | ⚠️ Hit a real bug (see below), now fixed |
| 6 | `add_dashboard_card_layout_editor.py` | New `DashboardCardLayoutPrefs` (config package): persists order + visibility for the reorderable Today-screen cards (Activity rings, both workout cards, 7-day summary, personal records, streak — **Steps stays pinned first, not part of this list**). Wired in `StreakCard` for the first time — fully built in an earlier sprint (comment: "v1.9.12, sprint 4"), never actually called. New pencil-icon button in the Today header (top-right); sync-time text now sits to its left instead of being the rightmost element. Full-screen editor: up/down buttons to reorder (no drag-and-drop — avoids a new Gradle dependency), switch to show/hide each card, persists immediately on every change. | ⚠️ Hit 2 real bugs (see below), now fixed |
| 7 | `fix_duplicate_goals_string.py` | **Bugfix.** Script 5 introduced a string named `goals_section_title` without checking it already existed — a dead leftover (`goals_section_title`/`goal_steps_label`/`goal_distance_label`/`goal_active_minutes_label`/`goal_calories_label`) near the Data Source section from an earlier, already-abandoned "Daily goals" UI. Broke `:app:mergeDebugResources`. Renamed the newly-introduced one to `dashboard_goals_section_title`; the old dead strings are untouched (still dead — see Known Issues). | ✅ Confirmed: resolved that specific error, build progressed further |
| 8 | `fix_composable_context_error.py` | **Bugfix.** Script 6 placed `LocalContext.current` and `remember(cardLayoutVersion) { ... }` directly inside the `LazyColumn { ... }` content lambda, between two `item { }` blocks — not a valid `@Composable` context (only the `LazyListScope` DSL functions themselves are valid to call directly there). Compiled fine to read, failed at `compileDebugKotlin`. Hoisted both calls to the top of `SummaryScreen`'s function body, before `LazyColumn(...)` starts. | **Not yet confirmed by the person** |

---

## Architecture / patterns added this session

- **`DashboardCardType` (enum) + `DashboardCardLayoutPrefs`** (`config/DashboardCardLayoutPrefs.kt`, new file): order + visibility for reorderable Today-screen cards. `DashboardOrderedCard(...)` in `FinalBitLutShell.kt` is the dispatcher (`when (cardType) { ... }`) mapping each enum value to its composable call.
- **`WorkoutFilterPrefs`** (`config/WorkoutFilterPrefs.kt`, new file): min-duration + excluded-exercise-type filtering, applied at write time in `GoogleHealthManager.writeSnapshot()`.
- **`retryOnConnectionRace()`** in `HuaweiHealthManager.kt`: generic retry wrapper for the cold-launch Huawei-client-not-connected race. Two call sites currently (daily steps, activity sessions) — worth reaching for again if new Huawei read paths show the same `"...not connected"` error pattern in logs.
- **Per-session distance attribution pattern** in `GoogleHealthManager.readDistanceForSessions()`: bulk-read once, attribute by time-overlap fraction, rather than one query per item. This is now the established pattern for "I need data at a finer grain than what's bulk-fetched" — reach for it again rather than looping queries.
- **Settings sections now come in two flavors** — pick deliberately per case:
  - *ViewModel-threaded* (Goals): needed because the value is also displayed live elsewhere (the rings), so staleness after a Settings change would be visible. Threaded through `DashboardViewModel` → `MainActivity` → `FinalBitLutShell` → `SettingsScreen`.
  - *Self-contained* (Workout filter, and the card-layout editor): no other screen needs to react live to the change, so it just reads/writes its own `*Prefs` class directly via `LocalContext.current`, no ViewModel plumbing. Lower risk, less wiring, but **do not use this pattern if another visible screen needs to reflect the change without a restart.**

## Dormant/half-built features found and (mostly) reconnected this session

A recurring pattern in this codebase: a feature is fully built at the data/ViewModel layer, with a doc comment describing its intended UI consumer, but the UI call site was never added (or got disconnected by a manual edit). Found and reconnected this session:
- `ProgressRingChip` — existed, unused on the Steps card. Now wired.
- `GoalPrefs` + `DashboardViewModel.setStepsGoal/setActiveMinutesGoal/setCaloriesGoalKcal` + `stepsProgress/activeMinutesProgress/caloriesProgress` — existed, fully computed, unused anywhere. Now wired (rings + Settings goals editor).
- `StreakCard` — fully built (v1.9.12), never called. Now wired into the card list.
- `WidgetVisibilityRow` — built, never called anywhere. Reused for the workout-filter per-type toggles.
- `requestGoogleHealthPermissions()` — doc comment claimed it returns `Boolean` specifically for `MainActivity` to consume, but it actually returned `Unit`. Fixed to genuinely return `Boolean` as part of the sync-reliability work, then wired into the `awaitingSystemResult` guard.

**Still dormant, not touched this session** (flag if relevant to the redesign):
- `goals_section_title`/`goal_steps_label`/`goal_distance_label`/`goal_active_minutes_label`/`goal_calories_label` strings near the Data Source section — dead leftover from an earlier abandoned goals UI, still unused, still sitting in both locale files.
- `ui/components/GlassCards.kt` — an empty stub file (imports only, no code), duplicate of the real `GlassCards.kt` at the package root. Flagged early this session, never cleaned up (out of scope each time).
- `MinimalSquareTile` composable in `FinalBitLutShell.kt` — defined, zero call sites, despite a detailed comment describing a "2x2 grid" that doesn't currently exist anywhere.

## Remaining items from "the last sprint" — not started

The person's original 5-item list for this sprint, only 3.5 of 5 done:
1. ✅ Activity rings + goals in Settings
2. ✅ Reorder/hide dashboard cards + edit pencil
3. ❌ **Trends / comparison-with-self** ("more active than your average Tuesday") — not started. Needs a decision on comparison basis (day-of-week historical average vs. simple N-day rolling average — the simpler N-day version is much cheaper, since day-of-week averaging would need a wider Health Connect read window than what's currently fetched).
4. ✅ Goal-progress text inside the Steps card
5. ❌ **Modern animations / hover effects** — not started. Note: this is a phone app, not a device with a mouse/stylus hover state in the traditional sense — worth clarifying with the person whether they mean press/transition animation polish (which fits) or literal pointer-hover (only meaningful on foldables/Chromebook/tablet-with-stylus contexts).

## Known issues / lessons learned this session (methodology)

Documenting the mistakes candidly since a new session should not repeat them:

1. **Hallucinated "already-fixed" code mid-diagnosis.** While diagnosing the cold-launch sync log, the assistant convinced itself (and initially told the person) that `awaitingSystemResult`, the `KEEP` policy, and a Huawei retry helper already existed in the codebase — they did not; the assistant had written them into its own working mirror during exploration and then mis-attributed them as pre-existing. Caught by re-diffing against the actual uploaded repomix export before delivering anything. **Lesson: never trust "I recall seeing this" about code state — diff against the real source every time, especially mid-session after a lot of exploration.**
2. **String-resource name collision.** `goals_section_title` was introduced without checking it already existed (as an unused leftover elsewhere in the same file). Broke `mergeDebugResources`. **Lesson: grep the full string name across both locale files before introducing any new one, not just near the insertion point.**
3. **Composable-context violation.** `LocalContext.current` / `remember()` placed directly inside a `LazyColumn` content lambda outside `item { }` — compiles-fine-to-read but is invalid Compose. **Lesson: composable calls inside `LazyColumn`/`LazyRow` bodies must be either inside `item { }`/`items { }` or hoisted above the `LazyColumn(...)` call entirely; this class of error only surfaces at `compileDebugKotlin`, not from reading the diff.**

**Process that emerged as reliable by the end of the session** (worth continuing): for any patch script bigger than a couple of edits, generate the old/new text blocks **programmatically** — apply the edits by hand to a working mirror first, then run Python's `difflib.SequenceMatcher` between a clean baseline and the hand-edited mirror to extract exact, byte-verified before/after blocks, auto-checking (a) each anchor is unique in the base file and (b) the old anchor does *not* remain a substring of the new text (the specific bug pattern that broke idempotency three separate times this session for pure-insertion edits — where the old anchor spans only one side of the insertion point, e.g. "append one import after the last one" rather than "insert between two existing imports"). Hand-transcribing large edits from memory was the direct cause of at least one of the bugs above.

---

## Recommended first steps in the new session

1. Ask for the current build status / latest `compileDebugKotlin` output before anything else (see banner at top).
2. If green: re-read this doc's "Remaining items" section and confirm with the person whether Trends/Animations are still wanted, or whether the design pass supersedes them.
3. If red: get the log, diagnose the same way — real device/log evidence over code-reading assumptions, diff-verify against the actual current repo state before claiming anything is "already there."
4. Re-read the repo's own `CLAUDE.md` at session start, per standing convention — it may have been updated independently of this document.
