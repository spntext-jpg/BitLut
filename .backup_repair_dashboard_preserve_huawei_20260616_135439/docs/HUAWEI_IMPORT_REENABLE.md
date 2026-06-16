# Huawei import re-enable checklist

Current sprint mode keeps the product focused on a premium Google Health Connect dashboard.
Huawei import remains in the codebase and is intentionally hidden until Huawei Health Kit approval.

## Preserved code

- `HuaweiHealthManager.kt`
- `HuaweiExportParser.kt`
- `ImportScreen.kt`
- `ImportViewModel.kt`
- `SyncWorker.kt`
- Huawei AGConnect Gradle plugin and `com.huawei.hms:health` dependency
- Huawei app id manifest metadata
- Health Connect write pipeline in `GoogleHealthManager.writeSnapshot(...)`

## Runtime policy before approval

- Do not show Huawei import in primary UI.
- Do not schedule automatic Huawei sync workers.
- Ask only for `dashboardPermissions` from Google Health Connect.
- Keep the visible app as one premium read-only health dashboard.

## After Health Kit approval

1. Set `FeatureFlags.HUAWEI_IMPORT_ENABLED = true`.
2. Add Import entry point to the hidden sidebar/settings area.
3. Request `googleHealthManager.importPermissions` only when the user starts import.
4. Re-enable the manual import flow first.
5. Re-enable scheduled sync only after manual import is stable on a real Huawei/HMS device.
