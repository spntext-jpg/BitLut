# CLAUDE.md

Read this before changing BitLut. This is the current engineering contract; historical details belong in `CHANGELOG.md` and `SESSION_HANDOFF.md`.

## Product boundary

BitLut is a local-first Kotlin/Jetpack Compose Android bridge:

```text
HUAWEI Health -> BitLut -> Android Health Connect -> compatible readers
```

No BitLut backend/account. Production scope is activity/workout data only: steps, distance, floors/elevation, calories when available, and exercise sessions. Do not add sleep, heart rate, SpO2, HRV, stress, or other biometric categories without an explicit product/scope review.

Real-data rule: never fabricate missing metrics. The only approved exception is the existing workout total-calorie estimate used when Huawei supplies no workout calories; keep that exception isolated to `TotalCaloriesBurnedRecord`.

Current top-priority goal: lift the Huawei Health Kit 100-user test-phase cap, and add `HEALTHKIT_CALORIES_READ` if it can be done without an Enterprise account. See `docs/SCALING_ROADMAP.md` for the plan; do not add any Advanced-tier scope (sleep/heart rate/SpO2/stress) regardless -- that remains permanently closed to individual developers.

## Current baseline — 2026-09-10

- Huawei Health Kit authorization and real activity reads work.
- `HuaweiWorkoutTypeMapper` is the single Huawei workout-ID mapping source.
- Per-session Huawei workout distance has priority over aggregate reconstruction.
- Health Connect workouts are `ACTIVELY_RECORDED`, use Huawei device manufacturer metadata, deterministic client record IDs and stable versions, and write session + Distance/Steps as one bundle (elevation and total-calories removed 2026-09-10).
- Workout distance/steps are also written as their own Health Connect records scoped to the exact session interval (gated per exercise type), so third-party readers see real per-workout metrics instead of only a coarser background aggregate. Elevation and total-calories were removed from this bundle on 2026-09-10 to shrink the payload after a corporate reader started failing to sync -- targeted reduction, not a confirmed fix (see `docs/BACKLOG.md`). See `sync.md` section 4.7.
- Dashboard workout metrics are type-aware and omit unavailable values.
- `DashboardCardLayoutPrefs` is the sole dashboard card order/visibility layer.
- `GoalPrefs` stores the steps goal only.
- August colors and system light/dark themes remain the design baseline; surfaces are now quieter and flatter.
- Bottom navbar: all controls share one common height (64dp); Refresh reads as primary via width (84dp pill), not height.
- Codespaces patch scripts run a local compile check only (`:app:compileDebugKotlin`); the full `assembleDebug`/`lintDebug` build runs in GitHub Actions, not locally. See "Local checks vs. CI build" below.

## Architecture anchors

### Huawei

`HuaweiHealthManager` owns authorization/live reads. `HuaweiWorkoutTypeMapper` owns workout type normalization. `HuaweiExportParser` owns bounded local archive import and must use the same mapper.

Do not rebuild workout distance from daily Health Connect overlap aggregates. Use Huawei activity-scoped values when available. Do not maintain a second numeric workout table.

### Health Connect

`GoogleHealthManager` owns read/write behavior. Keep deterministic identities/upsert semantics. Do not change workout recording method back to automatic/unknown. Do not attempt to spoof `DataOrigin`; Health Connect attributes records to the actual writer package (`com.openhealth.sync`).

The corporate wellness app started reliably importing BitLut-origin workouts after the 2026-08-31 session-scoped Distance/Steps/Elevation sub-metric write, but sync failures ("binder died" / rate-limit errors) were reported again in late August/early September 2026. Elevation and total-calories were removed from the workout bundle 2026-09-10 as a targeted payload-reduction response -- not a confirmed fix. Do not mutate workout write metadata further without new evidence (a corporate-app-side timestamped log correlated with BitLut's own sync times).

`writeActivitySessionsBatch()` currently contains three helper functions -- `workoutInteropScore()`, `preferWorkoutSession()`, `normalizeWorkoutSessionsForHealthConnect()` -- that resolve overlapping Huawei sessions before the write loop. These are easy to lose sight of because they sit between the write path's doc comment and the function itself; see "Never reconstruct a code block from memory" below for why this specific spot already caused a real regression once.

### Sync and resilience

`SyncWorker` / `SyncOrchestrator` own synchronization. Preserve retry/lease behavior unless a task explicitly targets sync reliability. `DashboardSnapshotCache` is the last-known-good UI cache. Never create demo/fake health records to make the dashboard look populated.

### UI

`FinalBitLutShell` owns current screens. `DashboardViewModel` owns dashboard state. Keep Settings minimal and preserve the existing Huawei/Google/Health Connect flows. Split files only when there is a concrete maintenance benefit; file size alone is not a reason.

## UI contract

- Keep August palette: Navy, Lime, Tangerine, Purple and Inter Variable.
- Normal cards: flat, subtle outline, no fake press animation. Hero may keep restrained depth.
- Pill buttons, practical touch targets, restrained tween motion. No routine bounce/elastic motion.
- One obvious primary action per group; Settings primary action is `Sync now`.
- Icon-only actions require content descriptions.
- Missing workout metrics are omitted, never replaced with invented zeroes.

## Localization contract

- UI strings belong in Android resources, not locale maps/hardcoded Kotlin.
- Every new/removal resource change must preserve key parity between `values/strings.xml` and `values-ru/strings.xml`.
- Parse both XML files before build.
- Never silence `MissingTranslation`; fix the locale resource.

## Cleanup rules

Apply YAGNI/KISS/DRY/SOLID conservatively:

- Do not delete a private method/import/layer from a lexical scan alone. Check all call sites and callbacks first.
- Remove plumbing only when the user-facing trigger and all remaining consumers are truly gone.
- Do not refactor unrelated working paths during cleanup.
- One-off patch/hotfix/verify scripts are delivery artifacts and should not remain in the repository after a successful sprint.

## Never reconstruct a code block from memory

**This is the single most important rule in this file. Violating it caused a real, shipped regression on 2026-09-10 that cost two multi-minute Codespaces builds to catch.**

What happened: a patch needed to remove two record types from the middle of a ~300-line function. Instead of taking the function's real, current text and deleting exactly those lines, the block was retyped from a template/memory of what the function looked like in an earlier session. That retyped version silently dropped three real helper functions (`workoutInteropScore`, `preferWorkoutSession`, `normalizeWorkoutSessionsForHealthConnect`) that had been added since, because they weren't in the remembered template. The mistake was repeated a second time on the very next attempt, against a freshly re-synced source, for the same underlying reason: the new block was written out again instead of derived from the real file.

Why the sandbox didn't catch it: without a real Android/Kotlin toolchain, the only available self-check was that the hand-typed block's own braces/parens balanced internally -- which they did, because a fabricated-but-self-consistent block is just as balanced as a correct one. Brace-counting only proves internal consistency, not correctness against the surrounding file. Byte-diffing the patch script's output against a hand-edited mirror only proves the *script* faithfully reproduces the *mirror* -- it proves nothing about whether the mirror itself is a correct edit of reality, if the mirror's new content was retyped rather than derived by editing the real captured text in place.

**The rule going forward:**

- When a change needs to modify existing code, take the literal current text of the affected region (from a real repomix export or a direct file read) and apply the *minimum necessary* removals/edits to it in place. Never write out a "new version" of a function or block from memory, template, or a prior session's version of it, even when confident about what it looked like.
- If a block is large or its surroundings are unclear, extract the exact boundaries first (e.g. `sed -n 'START,ENDp'`) and verify the extracted text is what you think it is before editing it -- don't assume the region is unchanged since a previous session.
- After editing, diff the result against the *original real file*, not just against your own new block, to see the full, minimal, real change -- a diff with unrelated large deletions is the signature of this exact mistake and should stop the patch before delivery.
- This applies with equal force to documentation edits describing code behavior: verify the current doc text with a fresh read/grep before assuming a prior session's edit still matches, since other sessions or the person's own manual edits can move content around without changing its meaning enough to show up in a casual skim.

## Local checks vs. CI build

Paulo runs the full build via GitHub Actions. Patch scripts delivered for Codespaces must **not** run `:app:assembleDebug` or `:app:lintDebug` -- those are slow (multiple minutes) and duplicate what CI already does. Instead:

- **Local gate in the patch script: `:app:compileDebugKotlin` only.** This is a real (not faked) Kotlin compiler invocation, fast, and would have caught this session's regression immediately (unresolved reference, type-inference errors) without needing a full resource merge or lint pass.
- **Static, non-Gradle checks stay in the patch script** and run before even the Kotlin compile step, since they're closer to free: brace/paren balance as an early sanity signal (not a correctness proof, see above), real-XML-parser validation for any touched `.xml`, and EN/RU string key parity counts.
- **Full `assembleDebug` + `lintDebug` is a CI (GitHub Actions) concern**, not something a Codespaces patch script should run. Do not silently reintroduce the full build into a patch script's gate; if a specific change seems to need it (e.g. a manifest or resource-merge-sensitive change), say so explicitly and ask, rather than defaulting to the slow gate.

## Verification guardrails

Established by earlier sessions' failed intermediate patches; still in force:

1. Run static structural checks before Gradle: duplicate declarations, dangling references, XML parse, EN/RU key parity.
2. Run `:app:compileDebugKotlin` as the local gate (see "Local checks vs. CI build" above). Compiling is the minimum bar; it is not a substitute for eventually running the full CI build before relying on a change.
3. Do not suppress lint or create a baseline merely to obtain green output.
4. If verification fails, print the concrete Kotlin/lint errors and stop before commit/push.
5. Keep Gradle console output compact; do not use `--stacktrace` unless specifically debugging a Gradle infrastructure failure.
6. Never include `git diff -- ...` in delivery commands.
7. Patch scripts should be idempotent/fail-closed where practical and must not guess when source anchors differ.
8. When a patch script's compile gate fails partway through, its file edits may already be on disk (uncommitted) even though nothing was committed. The next patch script must handle three possible states for any file it touches -- untouched, already-correctly-fixed, or left-broken-by-the-failed-attempt -- rather than assuming a clean starting point.

## Local compile gate

```bash
./gradlew :app:compileDebugKotlin \
  --no-daemon \
  --max-workers=1 \
  --no-watch-fs \
  --console=plain \
  -Dorg.gradle.jvmargs="-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8" \
  -Pkotlin.compiler.execution.strategy=in-process
```

Full `assembleDebug`/`lintDebug` runs in GitHub Actions CI, not here.

## Documentation discipline

- A claim about current behavior ("the corporate app now reliably imports...", "this record is written to Health Connect") that appears in more than one doc file tends to drift: one file gets updated when something changes and the others are missed. Before considering a doc pass finished, grep for the specific claim's key terms across *all* of `CLAUDE.md`, `CONTEXT.md`, `SESSION_HANDOFF.md`, `README.md`, `sync.md`, and `docs/*.md` -- not just the files remembered as relevant -- since this session repeatedly found "one more" stale mention on repeated sweeps that a single targeted edit missed.
- `README.md` and `docs/PRIVACY_POLICY.md` are user-facing; treat inaccuracies there as more urgent than internal docs, since they're read by people outside the project, and check them even when a change seems purely internal (a Health-Connect-write change is exactly the kind of thing the privacy policy describes).
- When another person (or another session) has made their own real edits to a doc since the last known state, don't blindly reapply a previously-planned edit -- read the file's current content first and make the minimal edit that fits what's actually there, preserving their additions.
