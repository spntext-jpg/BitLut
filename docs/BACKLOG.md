# BitLut Backlog

Updated: 2026-09-16

## Highest priority

- **Open verification: corporate wellness app sync failures ("binder died" / rate-limit errors after ~2 minutes), reported late August/early September 2026.** In addition to the Google Health 5.05 connection regression (fixed in 5.07), code review found a concrete BitLut churn amplifier: every 30-minute daily-step reconcile deleted all BitLut `StepsRecord`s across the 7-day Huawei window, including workout-scoped Steps introduced on 2026-08-30, then recreated them. The 2026-09-16 v2 fix removes that range delete, gives unchanged daily totals stable versions, and defers Health Connect binder failures to WorkManager backoff. Phone verification is still required before calling this incident resolved; do not change workout serialization/metadata meanwhile.
- **Scaling: submit Huawei Health Kit Verification** to lift the 100-user test-phase cap -- the top current scaling goal. See `docs/SCALING_ROADMAP.md` section 2 for the concrete action items (~15 working day review, no code changes required).
- **Scaling: request `HEALTHKIT_CALORIES_READ`** scope for real per-workout active-calorie data -- Basic-tier, individual-developer-reachable, no Enterprise account needed. See `docs/SCALING_ROADMAP.md` section 3.
- Add focused unit tests for `HuaweiWorkoutTypeMapper` and workout metric selection.
- Add screenshot/UI tests for Summary, Settings, dashboard editor, light mode and dark mode.
- Walking-steps undercount: awaiting a real-device diagnostic log showing `ActivitySummary.dataSummary`'s actual contents for a failing activity before attempting a structural fix (see `sync.md` section 8, `SESSION_HANDOFF.md`).

## Nice to have

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
