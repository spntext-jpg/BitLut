# BitLut — Session Handoff

Current handoff date: 2026-08-22.

Use this file together with a fresh repository/Repomix export. Read `CLAUDE.md`
before making code changes. Treat source code plus a fresh successful build as
the final authority when any old historical note disagrees.

## What BitLut is

BitLut is a Kotlin + Jetpack Compose Android bridge:

```text
HUAWEI Health -> BitLut -> Android Health Connect
```

It is activity-only, local-first, open source, and does not generate fake
health records.

## Current state

The project is no longer globally blocked on HUAWEI Health Kit approval.

Confirmed project direction:
- HUAWEI app scope approved
- real-device Huawei authorization has succeeded
- real activity data has been read
- partial Huawei category availability is handled independently
- Health Connect integration and background synchronization are working
- dashboard/cache/import reliability hardening is already in place

On 2026-08-22 a GUI/build recovery sprint removed Haze after Haze 1.7.x brought
Kotlin 2.2 metadata into the Kotlin 2.0.21 project. The correct resolution was
to remove the cosmetic dependency rather than migrate the entire toolchain.

After that change:
- `compileDebugKotlin` passes
- constrained Codespaces `assembleDebug` passes
- Haze is absent from the intended dependency graph
- August v3 is the current UI baseline

## Current UI direction

Forget the old Glass 2.0 / neo-glassmorphism baseline.

August v3 Android adaptation:
- light Canvas
- Navy navigation/dark anchor
- white control surfaces
- Lime filled primary actions with Ink content
- Purple focus/secondary interaction
- restrained motion
- native Compose navigation surfaces
- no Haze blur dependency

Some source filenames still contain `Glass`; they are legacy names, not design
requirements.

## Non-negotiable engineering constraints

1. Preserve working Huawei -> Health Connect synchronization.
2. Never generate fake health data.
3. Do not add biometric/sleep scopes without explicit approval.
4. Do not refactor unrelated sync/data code during UI work.
5. Maintain duplicate protection.
6. Keep Health Connect call volume bounded.
7. Treat coroutine cancellation correctly.
8. Use low-memory Codespaces build settings before assuming dex packaging is hung.
9. Avoid adding libraries for effects native Compose can express simply.
10. Run a full debug assemble before commit.

## Reliable Codespaces command

```bash
./gradlew :app:assembleDebug \
  --no-daemon \
  --max-workers=1 \
  --no-watch-fs \
  --console=plain \
  -Dorg.gradle.jvmargs="-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8" \
  -Pkotlin.compiler.execution.strategy=in-process
```

The normal build previously appeared to stop around dex/global synthetics under
Codespaces resource pressure. The constrained command completed successfully.

## Working convention

- communicate in Russian
- write code/comments/commit messages in English
- use standalone Python patch scripts for non-trivial repository edits
- patch scripts must be idempotent and verify expected source state
- do not manually paste large Kotlin diffs
- doc-only housekeeping should be reviewed before commit/push
- preserve a working baseline instead of doing broad refactors

## Current files to trust

Primary:
- `README.md`
- `CLAUDE.md`
- `CONTEXT.md`
- `SESSION_HANDOFF.md`
- `CHANGELOG.md`

Production references:
- `docs/HEALTH_DATA_PERMISSION_MATRIX.md`
- `docs/HUAWEI_DAILY_CHUNKING_166.md`
- `docs/HUAWEI_PRODUCTION_REVIEW_PACKAGE.md`
- `docs/HUAWEI_50005_APPGALLERY_VERIFICATION.md` for historical/diagnostic context
- `docs/PRIVACY_POLICY.md`

Do not treat removed one-off sprint/recovery documents as active architecture.

## Safe next work

Continue GUI modernization within August v3, but keep it isolated from sync/data
logic. Before adding a dependency, first ask whether the same result can be
implemented with existing Compose APIs and tokenized semantic components.

Larger architecture work such as splitting `FinalBitLutShell.kt`, introducing
new manager abstractions, or migrating the Gradle/toolchain should be separate,
explicitly scoped sprints rather than side effects of UI polish.
