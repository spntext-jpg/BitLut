# BitLut Backlog

Updated: 2026-11-18

## Highest priority

- November recovery device acceptance remains open: compare actual BitLut-origin Health Connect records with a timestamped corporate-reader run. See `HEALTH_CONNECT_RECOVERY.md`; the corporate code/logs were not supplied.
- Validate the deliberate Health Connect 1.2.0-alpha06 exception on Android 13 APK and Android 14+ platform providers, including Huawei auth, background export, permission denial and corrected source values.
- Run push/PR CI and the device matrix in `VALIDATION_2026_11.md`; source checks do not establish rendering or corporate import.
- Nutrition migration, decimal input, all macro states, offline catalog, edit/delete/undo and immediate Today totals need device acceptance. Review store declarations before release.
- Review optional background-read declarations/consent and distinguish export success from cache freshness.
- Historical fallbacks remain unresolved without new evidence: per-workout Huawei steps may be absent; the prior English-title experiment is not proof of a reader bug; Google daily origins still require device evidence before expansion.
- Existing raw continuous Distance records may overlap workout records; broad distance deduplication is not claimed by this patch. Preserve exact session values and obtain real source intervals before changing representation.
- Huawei verification/user-cap and calorie-scope console work remains in `SCALING_ROADMAP.md`.

## Nice to have

- Nutrition: profile long-term journal growth before introducing a transactional database; preserve history in any migration.
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
