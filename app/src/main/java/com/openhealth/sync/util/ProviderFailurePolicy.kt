package com.openhealth.sync.util

/** Abort this provider cycle rather than retrying each remaining record. */
internal object ProviderFailurePolicy {
    fun shouldDefer(error: Throwable): Boolean = generateSequence(error) { it.cause }
        .take(8).any {
            it is java.io.IOException || it is IllegalStateException ||
                it.javaClass.name.startsWith("android.os.") ||
                it.javaClass.name == "android.health.connect.HealthConnectException" ||
                listOf("rate limit", "rate_limit", "quota", "binder", "dead object", "service unavailable")
                    .any { marker -> it.message.orEmpty().contains(marker, ignoreCase = true) }
        }
}
