# UI Architecture Cleanup Sprint

Goal: improve AID/SOC/YAGNI without touching the stable Huawei -> Health Connect sync pipeline.

## Changes

- Removed duplicate imports from `MainActivity.kt`.
- Extracted the current final Compose shell from `MainActivity.kt` into `ui/screens/FinalBitLutShell.kt` when the expected marker is present.
- Removed old `DashboardScreen.kt` only when it is truly unreferenced.
- Added `scripts/verify_ui_architecture.py` to catch duplicate imports, zombie UI files, patch artifacts and oversized MainActivity regressions.
- Added `.gitignore` guardrails for generated patch artifacts.

## Deliberately not changed in this sprint

- `HuaweiHealthManager`
- `SyncWorker`
- `GoogleHealthManager`
- Health permission policy
- Huawei Health Kit authorization flow

## Next sprint

Move `FinalUiText` to Android string resources and keep `L10n.kt` only for domain formatting / workout-title normalization.
