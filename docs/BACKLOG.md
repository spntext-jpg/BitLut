# BitLut Backlog

Updated: 2026-09-03

## Highest priority

- **Scaling: submit Huawei Health Kit Verification** to lift the 100-user test-phase cap -- the top current goal. See `docs/SCALING_ROADMAP.md` section 2 for the concrete action items (~15 working day review, no code changes required).
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
- Health Connect actively-recorded workout metadata, Huawei device manufacturer, stable record version and bundled session/calorie writes.
- Minimal Settings and Health Connect settings deep link.
- Removed dead CSV, widget-visibility, unused goal and achievement-summary layers.
- Modernized cards/buttons/navigation while preserving the August palette.
- Removed one-off delivery patch scripts from the repository.
- Workout session-scoped Distance/Steps/Elevation Health Connect records; corporate wellness app now reliably imports BitLut-synced workouts (confirmed on a real device, `sync.md` section 4.6).
