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

The working baseline at the end of this session includes:

- HUAWEI -> Health Connect synchronization working on a real device.
- Manual and periodic WorkManager synchronization.
- Sync lease/reuse protection against concurrent jobs.
- Partial Huawei scope denial handled per category instead of failing the whole sync.
- Health Connect request-storm protection and bounded dashboard reads.
- Last-known permission state preserved across transient Health Connect provider failures.
- Dashboard freshness timestamp tied to real data changes rather than app-open time.
- August v3 applied as the active product design system.
- Haze removed; no blur dependency/toolchain migration.
- Two recent workout cards enriched from real Health Connect data.
- Settings daily goals reduced to the only currently used goal: steps.

## Latest diagnostic interpretation

The latest real-device log showed a healthy sync pipeline:

- Huawei daily steps were read and written successfully.
- Health Connect dashboard read completed without quota errors.
- No `Rate limited request quota has been exceeded` loop was present.
- The first sync took several seconds mainly inside Huawei SDK reads; the workout
  distance fallback completed inside the same dashboard second and was not the
  dominant delay.
- `50005` / `50062` responses still appear for Huawei categories whose scope/data
  is not currently available. They are treated as category-level partial denials.

Important: these scope failures do not justify fabricating values.

## Workout metric contract

Every recent-workout card must show the same six slots, in the same order:

1. Duration
2. Distance
3. Average speed
4. Steps
5. Active calories
6. Elevation gain

Data rules:

- Duration comes from the real ExerciseSessionRecord interval.
- Distance comes only from real imported/session/Health Connect distance data.
- Average speed is derived only when real distance exists.
- Steps come from real Health Connect step data overlapping the workout.
- Calories come only from real active-calorie data.
- Elevation comes only from real elevation data.
- Missing metrics render as `—`.
- Never estimate distance from steps.
- Never estimate calories from duration/body assumptions.
- Never invent elevation or speed.

The current distance boundary fallback is deliberately conservative:

- it runs only when exact aggregate/session distance is missing;
- it queries a narrow window around the displayed workout;
- it attributes only exact temporal overlap;
- source records longer than three hours are rejected;
- if no real overlap exists, distance remains missing.

This behavior is correct. Example from the latest real-device log:

- latest walking workout: real `steps=251`, but no matching distance record;
- previous walking workout: real `distance=3252.7 m` and `steps=519`.

The UI must therefore keep the same six labels for both cards while showing `—`
for the latest workout's missing distance/speed.

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

Canonical roles:

- Canvas `#F7F8FC`
- Surface `#FFFFFF`
- Ink / Navy `#151728`
- Navy Raised `#1C1E33`
- Lime `#DFFF6A`
- Lime Active `#C3E93E`
- Purple `#6E5CF6`
- Muted `#6F7385`

Rules:

- Steps card is the dark Hero.
- Normal cards are white Surface cards.
- Lime is the primary filled action color with Ink content.
- Purple is for focus/selection/secondary interaction.
- Inter Variable is global typography.
- Keep motion restrained.
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
- make surgical changes and preserve working behavior.

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

Start from the working sync baseline. Do not reopen the workout-distance problem
by trying to force a number into a session that has no real distance record.
Focus future work on new explicitly scoped product improvements.
