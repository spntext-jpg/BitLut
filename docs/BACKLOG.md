# BitLut Backlog

Updated: 2026-10-16

## Highest priority

- **Open verification: 2026-10-15/16 UI sprint, on a real phone, in light and dark themes.** None of it has been seen rendered. Check: (1) the navbar with four labels, including the Russian "Тренировки" on a narrow phone (labels shrink from 11sp to 9sp, then ellipsize), and the dumbbell and fork-and-knife glyph shapes; (2) the Today hero panel: greeting size next to the two 48dp buttons, the status line, and the white stat tiles on the dark hero in the dark theme (if they glare, change the tile background in `HeroStatTile`); (3) the 250dp loading skeleton against the real hero height (estimated, not measured); (4) the Nutrition add dialog with the keyboard open, deleting an entry, and day browsing; (5) the eight starter Workouts tips (`workout_tip_*`) for tone and accuracy. Before the next store release, also update the AppGallery data declarations for the local food journal.
- **Open verification: Google Health workouts (2026-10-08, OnePlus 7 Pro).** Workout sessions are now read from Google Fit AND Google Health (`com.fitbit.FitbitMobile`) origins; confirm on the device that workouts appear. If not, read the one-time in-app log line listing the exercise-session origins in Health Connect and adjust the origin family from that evidence. Do not extend daily totals to a second origin without it.
- **Open verification: corporate wellness app sync failures ("binder died" / rate-limit errors after ~2 minutes), reported late August/early September 2026.** In addition to the Google Health 5.05 connection regression (fixed in 5.07), code review found a concrete BitLut churn amplifier: every 30-minute daily-step reconcile deleted all BitLut `StepsRecord`s across the 7-day Huawei window, including workout-scoped Steps introduced on 2026-08-30, then recreated them. The 2026-09-16 v2 fix removes that range delete, gives unchanged daily totals stable versions, and defers Health Connect binder failures to WorkManager backoff. Phone verification is still required before calling this incident resolved; do not change workout serialization/metadata meanwhile.
- **New candidate cause added to the same open investigation (2026-09-16 (b)): fallback workout-title language.** Paulo observed the corporate reader's failures coincide with BitLut's fallback workout titles (used only when Huawei supplies no name) switching from English to Russian text. As an experiment, `HuaweiWorkoutTypeMapper.exportDisplayName()` now always writes English fallback titles to Health Connect regardless of device locale, while the existing `localizedDisplayName()` (dashboard-only) is unchanged. Not yet confirmed -- awaiting a real-device retest with the corporate reader. If this does not resolve the failures, revert the two call sites in `HuaweiHealthManager.kt`/`HuaweiExportParser.kt` back to `localizedDisplayName()`.
- **Scaling: submit Huawei Health Kit Verification** to lift the 100-user test-phase cap -- the top current scaling goal. See `docs/SCALING_ROADMAP.md` section 2 for the concrete action items (~15 working day review, no code changes required).
- **Scaling: request `HEALTHKIT_CALORIES_READ`** scope for real per-workout active-calorie data -- Basic-tier, individual-developer-reachable, no Enterprise account needed. See `docs/SCALING_ROADMAP.md` section 3.
- Add focused unit tests for `HuaweiWorkoutTypeMapper` and workout metric selection.
- Add screenshot/UI tests for Summary, Settings, dashboard editor, light mode and dark mode.
- Walking-steps undercount: awaiting a real-device diagnostic log showing `ActivitySummary.dataSummary`'s actual contents for a failing activity before attempting a structural fix (see `sync.md` section 8, `SESSION_HANDOFF.md`).

## Nice to have

- Nutrition follow-ups, only if wanted: a daily calorie goal, comparing eaten with burned calories, editing an entry, a food database (that would need a source and a privacy review).
- Workouts: replace or extend the starter tips; one `WorkoutTip` line plus two strings per language per tip.
- Split `FinalBitLutShell.kt` into screen files only when there is a concrete maintenance benefit; do not refactor just for file size.
- Revisit adaptive/large-screen layout after phone UI is stable.

## Completed

- Correct Huawei workout ID mapping and non-workout filtering.
- Per-session Huawei workout distance.
- Type-aware dashboard metrics.
- Health Connect actively-recorded workout metadata, Huawei device manufacturer, stable record version, and bundled session/Distance/Steps writes.
- Minimal Settings and Health Connect settings deep link.
- Removed dead CSV, widget-visibility, unused goal and achievement-summary layers.
- Modernized cards/buttons/navigation while preserving the August palette.
- Removed one-off delivery patch scripts from the repository.
- Workout session-scoped Distance/Steps Health Connect records (Elevation and total-calories removed 2026-09-10, see Highest Priority); corporate wellness app started reliably importing BitLut-synced workouts once this began (confirmed on a real device, `sync.md` section 4.7).
