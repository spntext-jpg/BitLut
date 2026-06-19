# BitLut Backlog

## Done in current sprint

- Hardened Health Connect permission coverage.
- Added verification script for health permission coverage.
- Preserved Huawei Health -> Android Health Connect sync pipeline.
- Added UI/localization sprint documentation.
- Updated README into premium marketing-style project material.
- Added clean English and Russian resource strings for the next localization migration.

## Current product structure

- Summary / Сводка
- History / История
- Settings / Настройки

Settings owns all connection and sync actions:

- Google Health Connect permissions
- Huawei Health authorization
- Manual sync
- Last sync / sync status

## Next sprint: localization cleanup

- Replace remaining `BText` adapter in `MainActivity.kt` with `stringResource(...)`.
- Keep `values-ru` and `values` as the only source of user-visible copy.
- Add a CI/local script check for hardcoded English/Russian UI strings in Kotlin files.

## Next sprint: UI polish

- Improve Summary hero card hierarchy.
- Improve History charts and seven-day metric cards.
- Improve Settings connection cards and state descriptions.
- Keep the sync pipeline unchanged while polishing UI.

## Huawei Health Kit validation

After Health Kit approval:

1. Use release SHA-256 build.
2. Log in with reviewer/test Huawei account.
3. Authorize Huawei Health Kit.
4. Run manual sync.
5. Verify Health Connect records for steps, distance, floors, elevation, active calories and exercise sessions.
6. Capture logs for empty data, 50005, missing Huawei Health and HMS Core failures.

## Guardrails

- Do not commit `.bak` files.
- Do not commit temporary patch scripts.
- Do not commit `.kotlin/errors` logs.
- Do not change `HuaweiHealthManager`, `SyncWorker` or `GoogleHealthManager` during pure UI sprints.
- Do not fake unsupported Health Connect records.

## UI Expressive Final Sprint

- [x] Move product navigation to Summary / History / Settings.
- [x] Add hero KPI and activity rings to Summary.
- [x] Add 7-day trend cards to History.
- [x] Add Google/Huawei/manual sync cockpit to Settings.
- [ ] Replace remaining runtime text helpers with canonical Android string resources in a later low-risk localization refactor.
- [ ] Add screenshot tests after Health Kit approval is complete.

- [x] Sprint: expand Health Connect permissions, localize workout names, and simplify Summary hierarchy.
