/** Foreground diagnostic only. Integrate in the corporate RN app; do not run in Node/Codespaces.
 * Confirm the native permission delegate/manifest setup for its installed library first.
 * Consume each yielded page idempotently. No health data or tokens are logged here.
 */
import { initialize, requestPermission, readRecords } from 'react-native-health-connect';

export async function* readBitLutWorkoutPages(start: Date, end: Date) {
  if (!Number.isFinite(start.getTime()) || !Number.isFinite(end.getTime()) || end <= start) {
    throw new Error('Invalid time window');
  }
  if (!(await initialize())) throw new Error('Health Connect is unavailable');
  const grants = await requestPermission([{ accessType: 'read', recordType: 'ExerciseSession' }]);
  if (!grants.some(p => p.accessType === 'read' && p.recordType === 'ExerciseSession')) {
    throw new Error('Corporate reader needs its own exercise read permission');
  }
  let pageToken: string | undefined;
  const seen = new Set<string>();
  for (let page = 0; page < 20; page += 1) {
    const result = await readRecords('ExerciseSession', {
      timeRangeFilter: { operator: 'between', startTime: start.toISOString(), endTime: end.toISOString() },
      dataOriginFilter: ['com.openhealth.sync'],
      ascendingOrder: true, pageSize: 100, pageToken,
    });
    yield result.records;
    const next = result.pageToken?.trim();
    if (!next) return; // Both null and empty strings terminate pagination.
    if (seen.has(next)) throw new Error('Provider repeated a pagination token');
    seen.add(next);
    pageToken = next;
  }
  throw new Error('Diagnostic page budget exceeded: split the time window');
}
