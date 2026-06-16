# BitLut v1.5 navigation recovery

This patch restores the visible product shell after the dashboard-first hardening pass.

## Visible navigation

- Dashboard: Google Health data overview.
- Sync: Google Health Connect permissions and dashboard refresh.
- Huawei: discoverable but locked until Huawei Health Kit approval.
- Settings: release track and feature-flag status.

## Safety contract

Huawei import code remains compiled and preserved, but `FeatureFlags.HUAWEI_IMPORT_ENABLED` stays `false` in v1.5.
While disabled, the app must not start Huawei background sync, request Huawei permissions, or write imported data.

## Re-enable path

After Huawei Health Kit approval:

1. Set `FeatureFlags.HUAWEI_IMPORT_ENABLED = true`.
2. Run a dedicated import QA pass with real Huawei export files.
3. Verify Health Connect read/write permissions.
4. Re-check AppGallery privacy text and data safety declarations.
