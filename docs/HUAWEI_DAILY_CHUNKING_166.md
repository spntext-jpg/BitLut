# BitLut 1.6.6 Huawei Daily Chunking

## Goal

Prevent Huawei Health Kit / HMS IPC payload issues when reading large continuous datasets for multi-day sync windows.

## Rules

- Public sync contracts remain unchanged.
- SyncWorker remains unaware of chunking.
- readSnapshot/readSteps/etc continue calling readPoints.
- readPoints now wraps readPointsRaw.
- Continuous data is read in 24-hour chunks.
- Activity/session/exercise/sport reads bypass chunking to avoid midnight split issues.
- Boundary duplicates are removed with distinctBy.
- SecurityException / 50005 is not swallowed; it must propagate to SyncWorker.

