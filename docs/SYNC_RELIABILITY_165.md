# BitLut 1.6.5 Sync Reliability Hardening

## Goal

Prevent duplicate writes to Google Health Connect and make sync safer under repeated manual syncs, worker retries and partial category failures.

## Implemented in P0

- GoogleHealthManager uses HealthPermissionPolicy.syncPermissions.
- Health Connect records written by BitLut get stable Metadata.clientRecordId.
- clientRecordId format: bitlut_<type>_<startTimeMs>_<endTimeMs>[_discriminator].
- Added scripts/verify_sync_reliability.py static guardrail.

## Next P1

- Huawei read chunking by day.
- Silent Huawei token refresh attempt for expired HMS auth.
- Optional HealthDataRepository if dashboard must work from Huawei directly before GHC export.

