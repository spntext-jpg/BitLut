# Huawei import re-enable checklist

Huawei import is intentionally preserved in the source tree and hidden at runtime.

Current AppGallery approval build:

- visible product: Google Health Connect dashboard
- visible data: daily steps, weekly steps, imported workouts
- hidden feature: Huawei Health import
- disabled runtime: WorkManager Huawei sync / automatic Huawei import
- feature flag: `FeatureFlags.HUAWEI_IMPORT_ENABLED = false`

After Huawei Health Kit approval:

1. Confirm AppGallery package name, SHA-256 fingerprint, Health Kit approval, and `agconnect-services.json`.
2. Run Huawei import QA on a Huawei/HMS device.
3. Flip `FeatureFlags.HUAWEI_IMPORT_ENABLED` to `true`.
4. Re-enable the import entry point in navigation/sidebar only after QA passes.
5. Request write permissions only in the import flow, not for dashboard-only browsing.
