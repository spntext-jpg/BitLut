# BitLut — Session Handoff

Current handoff date: 2026-08-22.

Read `CLAUDE.md` and this file before changing code. Source code plus a fresh
successful build are the final authority if an older historical note conflicts.

## Product

BitLut is a local-first Kotlin + Jetpack Compose Android bridge:

```text
HUAWEI Health -> BitLut -> Android Health Connect
```

Current product scope is activity-only. BitLut must never synthesize missing
health data.

## End-of-session baseline

Four patches shipped and built successfully today (2026-08-22), in this order:

1. Workout cards narrowed from six metrics to four, for every exercise type
   (Duration, Distance, Avg speed, Steps).
2. August v3 dark theme activated -- system-driven (`isSystemInDarkTheme()`),
   not a manual in-app toggle. `BitPalette.dark()` already existed in the
   codebase but was unreachable; this activated it.
3. Steps Hero card given a two-value layout (Steps + Distance each as their
   own big number), new Tangerine accent color for Settings toggles and the
   navbar Refresh button, navbar narrowed slightly and Refresh button
   enlarged 15%.
4. Dark-mode follow-up fixes from real-device feedback: several icons/text
   were still gray/invisible in dark mode (root cause: `HealthAccent` was
   not theme-aware, now fixed -- see "Dark theme" below); navbar buttons
   given a light spring-based bounce on press; biking's 4th workout metric
   changed from Steps (illogical for cycling) to Elevation gain.

Also still true from before today:

- HUAWEI -> Health Connect synchronization working on a real device.
- Manual and periodic WorkManager synchronization.
- Sync lease/reuse protection against concurrent jobs.
- Partial Huawei scope denial handled per category instead of failing the whole sync.
- Health Connect request-storm protection and bounded dashboard reads.
- Last-known permission state preserved across transient Health Connect provider failures.
- Dashboard freshness timestamp tied to real data changes rather than app-open time.
- Haze removed; no blur dependency/toolchain migration.
- Settings daily goals reduced to the only currently used goal: steps.

## Dark theme (2026-08-22)

System-driven, not an in-app toggle. Dark Canvas = Navy, dark Surface =
NavyRaised, dark Soft = NavySoft (extends the existing Navy ramp rather than
a second palette). Steps Hero card is NavyRaised in both modes, unchanged.
Lime stays a filled surface with Ink content in both modes.

`HealthAccent` (`activity`/`mind`/`violet`) is now `@Composable`, resolving
to Lime in dark mode (~14.5:1 contrast against NavyRaised) and the original
InkSoft in light mode. This was the root cause of a real-device bug found
today: these three properties were a single fixed InkSoft value that
measured ~1.2:1 contrast against dark-mode cards -- effectively invisible.
Affected the Last 7 Days card's numbers, Personal Records' icons, and
workout-type icons on `WorkoutRecencyCard`, among others. If you add a new
`HealthAccent` consumer, remember it must be called from a `@Composable`
context -- `BitPalette.light()`/`dark()` cannot call it and instead hardcode
their own matching fixed values directly.

If something still looks gray/low-contrast in dark mode that wasn't covered
by today's fix, it is very likely another hardcoded `AugustColor.*`
reference that bypasses both `palette` and `HealthAccent` -- grep for direct
`AugustColor.InkSoft`/`AugustColor.Muted` usage in the same style as
`HealthAccent` had before today's fix.

## Workout metric contract (revised 2026-08-22)

Every recent-workout card shows four slots. The first three are the same for
every exercise type; the fourth is exercise-type-aware:

1. Duration
2. Distance
3. Average speed
4. **Steps** for most exercise types, **Elevation gain** specifically for
   `ExerciseSessionRecord.EXERCISE_TYPE_BIKING`

Data rules (unchanged from before):

- Duration comes from the real ExerciseSessionRecord interval.
- Distance comes only from real imported/session/Health Connect distance data.
- Average speed is derived only when real distance exists.
- Steps come from real Health Connect step data overlapping the workout.
- Elevation comes only from real elevation data.
- Missing metrics render as `—`.
- Never estimate distance from steps.
- Never estimate calories from duration/body assumptions.
- Never invent elevation or speed.

Active calories and (for non-biking types) elevation gain were deliberately
removed from the card display entirely -- not hidden conditionally, removed
as a display contract -- because Huawei frequently scope-denies
`activeCalories` (50005) and elevation is rarely populated for the same
underlying reason, so the old six-slot layout mostly showed four real values
and two permanent dashes. `ActivitySessionData.activeCaloriesKcal` /
`.elevationMeters` are still read/synced for CSV export and daily totals;
only card display was narrowed.

The current distance boundary fallback is deliberately conservative:

- it runs only when exact aggregate/session distance is missing;
- it queries a narrow window around the displayed workout;
- it attributes only exact temporal overlap;
- source records longer than three hours are rejected;
- if no real overlap exists, distance remains missing.

**Do not reopen this fallback logic.** This is the same standing rule as
before today; nothing about today's four-metric-slot or biking-elevation
change touches this fallback at all.

## Health Connect quota rules

Do not reintroduce unbounded pagination into dashboard hot paths.

Keep:

- bounded newest-first dashboard reads;
- coalesced/throttled dashboard refreshes;
- permission caching;
- one authoritative post-sync snapshot;
- narrow per-workout fallback only where necessary.

CSV export or explicit diagnostic tools may use broader reads because they are
not hot-path UI operations.

## August v3

Canonical roles (light mode):

- Canvas `#F7F8FC`
- Surface `#FFFFFF`
- Ink / Navy `#151728`
- Navy Raised `#1C1E33`
- Navy Soft `#24263D`
- Lime `#DFFF6A`
- Lime Active `#C3E93E`
- Purple `#6E5CF6`
- Muted `#6F7385`
- Tangerine `#F28500` (2026-08-22)
- Tangerine Active `#DD7A00` (2026-08-22)

Dark mode (system-driven, 2026-08-22): dark Canvas = Navy, dark Surface =
NavyRaised, dark Soft = NavySoft. See "Dark theme" section above for the
full rationale and the `HealthAccent` gotcha.

Rules:

- Steps card is the dark Hero, in both light and dark theme.
- Normal cards are white Surface in light mode, NavyRaised in dark mode.
- Lime is the primary filled action color with Ink content, both modes.
- Tangerine is the "on/active" signal for Settings toggles and the navbar
  Refresh button only -- not a second primary CTA.
- Purple is for focus/selection/secondary interaction, unchanged role.
- Inter Variable is global typography.
- Nav bar press feedback uses a light spring bounce (explicit exception);
  everything else stays restrained motion.
- Do not reintroduce Haze or permanent glassmorphism.

## Settings goals

Only the steps goal is currently exposed in Settings.

Active-minutes and calorie goals are not product controls and should not be
reintroduced unless those goals become real product features with downstream use.

## Build gate

Use the constrained Codespaces build:

```bash
./gradlew :app:assembleDebug \
  --no-daemon \
  --max-workers=1 \
  --no-watch-fs \
  --console=plain \
  -Dorg.gradle.jvmargs="-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8" \
  -Pkotlin.compiler.execution.strategy=in-process
```

A full `assembleDebug` must pass before commit.

## Working convention

For all coding in this project:

- reason about code in English;
- write code, comments, identifiers, and commit messages in English;
- prefer one standalone Python patch script;
- embed verification in that script when practical;
- final delivery should contain the patch and one command block only;
- make surgical changes and preserve working behavior;
- every new patch script filename must differ from all previous ones in the
  project (append v2, v3, etc.) -- never reuse or overwrite a prior patch
  script's filename, even for a fix to that same patch.

## Trusted current docs

- `README.md`
- `CLAUDE.md`
- `CONTEXT.md`
- `SESSION_HANDOFF.md`
- `CHANGELOG.md`
- `docs/HEALTH_DATA_PERMISSION_MATRIX.md`
- `docs/HUAWEI_DAILY_CHUNKING_166.md`
- `docs/HUAWEI_PRODUCTION_REVIEW_PACKAGE.md`
- `docs/PRIVACY_POLICY.md`

## Next-session rule

Start from the working sync baseline. Do not reopen the workout-distance
problem by trying to force a number into a session that has no real distance
record. Do not revert the dark-theme `HealthAccent` fix back to a plain
non-composable object without an equally thorough audit of every call site's
theme-awareness. Focus future work on new explicitly scoped product
improvements.
