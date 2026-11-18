package com.openhealth.sync.util

/** Persisted version|fingerprint; record identity is deliberately independent of value. */
internal object StableRecordVersion {
    fun resolve(stored: String?, fingerprint: String, now: Long): String {
        val previous = stored?.substringBefore('|')?.toLongOrNull() ?: 0L
        if (previous > 0 && stored?.substringAfter('|') == fingerprint) return requireNotNull(stored)
        return "${maxOf(now, previous + 1, 2L)}|$fingerprint"
    }
}
